import tempfile

from pywps import FORMATS, UOM
from pywps.app import Process
from pywps.inout import LiteralOutput, ComplexOutput
from .process_defaults import process_defaults, LiteralInputD, ComplexInputD, BoundingBoxInputD
from pywps.app.Common import Metadata
from pywps.response.execute import ExecuteResponse
from processes import process_helper
from gdalos.viewshed import viewshed_consts
from backend.formats import czml_format
from gdalos import GeoRectangle
from gdalos import gdalos_util
from gdalos.viewshed.viewshed_combine import viewshed_calc


class ViewShed(Process):
    def __init__(self):
        process_id = 'viewshed'

        defaults = process_defaults(process_id)
        mm = dict(min_occurs=1, max_occurs=23)  # 23 latin letters for gdal calc
        inputs = [
            LiteralInputD(defaults, 'of', 'output format (czml, gtiff)', data_type='string',
                          min_occurs=0, max_occurs=1, default='gtiff'),

            LiteralInputD(defaults, 'out_crs', 'output raster crs', data_type='string', default=None, min_occurs=0, max_occurs=1),

            ComplexInputD(defaults, 'r', 'input_raster', supported_formats=[FORMATS.GEOTIFF], min_occurs=1, max_occurs=1),
            LiteralInputD(defaults, 'bi', 'band_index', data_type='positiveInteger', default=1, min_occurs=0, max_occurs=1),
            LiteralInputD(defaults, 'co', 'creation options', data_type='string', min_occurs=0, max_occurs=1),

            LiteralInputD(defaults, 'md', 'maximum_distance (radius)', data_type='float', uoms=[UOM('metre')], **mm),

            # obeserver x,y in the given CRS
            LiteralInputD(defaults, 'in_crs', 'observer input crs', data_type='string', default=None, min_occurs=0, max_occurs=1),
            LiteralInputD(defaults, 'ox', 'observer_X', data_type='float', uoms=[UOM('metre')], **mm),
            LiteralInputD(defaults, 'oy', 'observer_Y', data_type='float', uoms=[UOM('metre')], **mm),

            # heights relative to terrain
            LiteralInputD(defaults, 'oz', 'observer altitude relative to terrain', data_type='float', uoms=[UOM('metre')], **mm),
            LiteralInputD(defaults, 'tz', 'target altitude relative to terrain', data_type='float', uoms=[UOM('metre')], **mm),

            # optional values
            LiteralInputD(defaults, 'vv', 'visible_value', data_type='float', default=viewshed_consts.st_seen, **mm),
            LiteralInputD(defaults, 'iv', 'invisible_value', data_type='float', default=viewshed_consts.st_hidden, **mm),
            LiteralInputD(defaults, 'ov', 'out_of_bounds_value', data_type='float', default=viewshed_consts.st_nodata, **mm),
            LiteralInputD(defaults, 'ndv', 'nodata_value', data_type='float', uoms=[UOM('metre')], default=viewshed_consts.st_nodtm, **mm),

            # advanced parameters
            LiteralInputD(defaults, 'cc', 'curve_coefficient', data_type='float', default=viewshed_consts.cc_atmospheric_refraction, **mm),
            LiteralInputD(defaults, 'mode', 'viewshed calc mode', data_type='integer', default=2, **mm),

            ComplexInputD(defaults, 'color_palette', 'color palette', supported_formats=[FORMATS.TEXT],
                          min_occurs=0, max_occurs=1, default=None),

            # output extent definition
            LiteralInputD(defaults, 'm', 'extent combine mode 2:combine/3:intersection', data_type='integer',
                          min_occurs=1, max_occurs=1, default=2),
            BoundingBoxInputD(defaults, 'extent', 'extent BoundingBox',
                              crss=['EPSG:4326', ], metadata=[Metadata('EPSG.io', 'http://epsg.io/'), ],
                              min_occurs=0, max_occurs=1, default=None),
            ComplexInputD(defaults, 'cutline', 'output vector cutline',
                          supported_formats=[FORMATS.GML],
                          # crss=['EPSG:4326', ], metadata=[Metadata('EPSG.io', 'http://epsg.io/'), ],
                          min_occurs=0, max_occurs=1, default=None),

            # combine calc modes
            LiteralInputD(defaults, 'o', 'operation 0:Single/1:Sum/2:Unique(todo)', data_type='integer',
                          min_occurs=0, max_occurs=1, default=None),

            ComplexInputD(defaults, 'fr', 'fake input rasters (for debugging)', supported_formats=[FORMATS.GEOTIFF],
                          min_occurs=0, max_occurs=23, default=None),

        ]
        outputs = [
            LiteralOutput('r', 'input raster name', data_type='string'),
            ComplexOutput('output', 'result raster', supported_formats=[FORMATS.GEOTIFF, czml_format]),
        ]

        super().__init__(
            self._handler,
            identifier=process_id,
            version='1.0',
            title='viewshed raster analysis',
            abstract='runs gdal.ViewshedGenerate',
            profile='',
            metadata=[Metadata('raster')],
            inputs=inputs,
            outputs=outputs,
            store_supported=True,
            status_supported=True
        )

    def _handler(self, request, response: ExecuteResponse):
        of: str = process_helper.get_request_data(request.inputs, 'of')
        ext = gdalos_util.get_ext_by_of(of)
        is_czml = ext == '.czml'

        extent = process_helper.get_request_data(request.inputs, 'extent')
        if extent is not None:
            # I'm not sure why the extent is in format miny, minx, maxy, maxx
            extent = [float(x) for x in extent]
            extent = GeoRectangle.from_min_max(extent[1], extent[3], extent[0], extent[2])
        else:
            extent = request.inputs['m'][0].data

        cutline = process_helper.get_request_data(request.inputs, 'cutline', True)
        operation = process_helper.get_request_data(request.inputs, 'o')
        color_palette = process_helper.get_request_data(request.inputs, 'color_palette', True)

        output_filename = tempfile.mktemp(suffix=ext)

        co = None
        files = []
        if 'fr' in request.inputs:
            for fr in request.inputs['fr']:
                fr_filename, ds = process_helper.open_ds_from_wps_input(fr)
                if operation:
                    files.append(ds)
                else:
                    output_filename = fr_filename
            input_ds = bi = arrays_dict = in_coords_crs_pj = out_crs = color_palette = None

        else:
            raster_filename, input_ds = process_helper.open_ds_from_wps_input(request.inputs['r'][0])
            response.outputs['r'].data = raster_filename
            bi = request.inputs['bi'][0].data

            in_coords_crs_pj = process_helper.get_request_data(request.inputs, 'in_crs')
            out_crs = process_helper.get_request_data(request.inputs, 'out_crs')

            if 'co' in request.inputs:
                co = []
                for coi in request.inputs['co']:
                    creation_option: str = coi.data
                    sep_index = creation_option.find('=')
                    if sep_index == -1:
                        raise Exception(f'creation option {creation_option} unsupported')
                    co.append(creation_option)

            params = 'md', 'ox', 'oy', 'oz', 'tz', \
                     'vv', 'iv', 'ov', 'ndv', \
                     'cc', 'mode'
            arrays_dict = {k: process_helper.get_input_data_array(request.inputs[k]) for k in params}

        viewshed_calc(input_ds=input_ds, bi=bi,
                  output_filename=output_filename, co=co, of=of,
                  arrays_dict=arrays_dict, extent=extent, cutline=cutline, operation=operation,
                  in_coords_crs_pj=in_coords_crs_pj, out_crs=out_crs,
                  color_palette=color_palette,
                  files=files)

        response.outputs['output'].output_format = czml_format if is_czml else FORMATS.GEOTIFF
        response.outputs['output'].file = output_filename

        return response


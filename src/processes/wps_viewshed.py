import tempfile
import os.path

import gdal
from pywps import FORMATS, UOM
from pywps.app import Process
from pywps.inout import LiteralOutput, ComplexOutput
from .process_defaults import process_defaults, LiteralInputD, ComplexInputD, BoundingBoxInputD
from pywps.app.Common import Metadata
from pywps.response.execute import ExecuteResponse
from processes import process_helper
from backend import viewshed_consts
from backend.formats import czml_format
from gdalos import GeoRectangle
from gdalos.calc import gdal_calc
from backend import gdal_to_czml


class ViewShed(Process):
    def __init__(self):
        process_id = 'viewshed'

        defaults = process_defaults(process_id)
        mm = dict(min_occurs=1, max_occurs=23)  # 23 latin letters for gdal calc
        inputs = [
            LiteralInputD(defaults, 'output_czml', 'make output as czml', data_type='boolean',
                          min_occurs=0, max_occurs=1, default=False),
            LiteralInputD(defaults, 'output_tif', 'make output as tif', data_type='boolean',
                          min_occurs=0, max_occurs=1, default=True),

            ComplexInputD(defaults, 'r', 'input_raster', supported_formats=[FORMATS.GEOTIFF], min_occurs=1, max_occurs=1),

            LiteralInputD(defaults, 'bi', 'band_index', data_type='positiveInteger', default=1, min_occurs=0, max_occurs=1),
            LiteralInputD(defaults, 'co', 'creation options', data_type='string', min_occurs=0, max_occurs=1),

            LiteralInputD(defaults, 'ox', 'observer_X', data_type='float', uoms=[UOM('metre')], **mm),
            LiteralInputD(defaults, 'oy', 'observer_Y', data_type='float', uoms=[UOM('metre')], **mm),
            LiteralInputD(defaults, 'oz', 'observer_Z', data_type='float', uoms=[UOM('metre')], **mm),
            LiteralInputD(defaults, 'tz', 'target_z', data_type='float', uoms=[UOM('metre')], **mm),

            LiteralInputD(defaults, 'vv', 'visible_value', data_type='float', default=viewshed_consts.st_seen, **mm),
            LiteralInputD(defaults, 'iv', 'invisible_value', data_type='float', default=viewshed_consts.st_hidden, **mm),
            LiteralInputD(defaults, 'ov', 'out_of_bounds_value', data_type='float', default=viewshed_consts.st_nodata, **mm),
            LiteralInputD(defaults, 'ndv', 'nodata_value', data_type='float', uoms=[UOM('metre')], default=viewshed_consts.st_nodtm, **mm),

            LiteralInputD(defaults, 'cc', 'curve_coefficient', data_type='float', default=viewshed_consts.cc_atmospheric_refraction, **mm),
            LiteralInputD(defaults, 'mode', 'calc mode', data_type='integer', default=2, **mm),
            LiteralInputD(defaults, 'md', 'maximum_distance', data_type='float', uoms=[UOM('metre')], **mm),

            ComplexInputD(defaults, 'color_palette', 'color palette', supported_formats=[FORMATS.TEXT],
                          min_occurs=0, max_occurs=1, default=None),
            LiteralInputD(defaults, 'o', 'operation', data_type='integer',
                          min_occurs=1, max_occurs=1, default=None),
            LiteralInputD(defaults, 'm', 'extent combine mode', data_type='integer',
                          min_occurs=1, max_occurs=1, default=2),

            ComplexInputD(defaults, 'fr', 'fake input rasters', supported_formats=[FORMATS.GEOTIFF],
                          min_occurs=0, max_occurs=23, default=None),

            BoundingBoxInputD(defaults, 'extent', 'extent BoundingBox',
                              crss=['EPSG:4326', ], metadata=[Metadata('EPSG.io', 'http://epsg.io/'), ],
                              min_occurs=0, max_occurs=1, default=None)

        ]
        outputs = [
            LiteralOutput('r', 'input raster name', data_type='string'),
            ComplexOutput('tif', 'result as GeoTIFF', supported_formats=[FORMATS.GEOTIFF]),
            ComplexOutput('czml', 'result as CZML', supported_formats=[czml_format])
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
        output_czml = request.inputs['output_czml'][0].data
        output_tif = request.inputs['output_tif'][0].data
        if output_czml or output_tif:
            extent = request.inputs['extent'][0].data if 'extent' in request.inputs else None
            if extent is not None:
                # I'm not sure why the extent is in format miny, minx, maxy, maxx
                extent = [float(x) for x in extent]
                extent = GeoRectangle.from_min_max(extent[1], extent[3], extent[0], extent[2])
            else:
                extent = request.inputs['m'][0].data

            operation = request.inputs['o'][0].data

            czml_output_filename = tempfile.mktemp(suffix=czml_format.extension) if output_czml else None
            tif_output_filename = tempfile.mktemp(suffix=FORMATS.GEOTIFF.extension) if output_tif else None

            files = []
            if 'fr' in request.inputs:
                for fr in request.inputs['fr']:
                    fr_filename, src_ds = process_helper.open_ds_from_wps_input(fr)
                    if operation:
                        files.append(src_ds)
                    else:
                        tif_output_filename = fr_filename
                        dst_ds = src_ds
            else:
                raster_filename, input_ds = process_helper.open_ds_from_wps_input(request.inputs['r'][0])
                response.outputs['r'].data = raster_filename

                input_band: gdal.Band = input_ds.GetRasterBand(request.inputs['bi'][0].data)

                if input_band is None:
                    raise Exception('band number out of range')

                co = None
                if 'co' in request.inputs:
                    co = []
                    for coi in request.inputs['co']:
                        creation_option: str = coi.data
                        sep_index = creation_option.find('=')
                        if sep_index == -1:
                            raise Exception(f'creation option {creation_option} unsupported')
                        co.append(creation_option)

                params = 'ox', 'oy', 'oz', 'tz', \
                         'vv', 'iv', 'ov', 'ndv', \
                         'cc', 'mode', 'md'
                new_keys = \
                    'observerX', 'observerY', 'observerHeight', 'targetHeight', \
                    'visibleVal', 'invisibleVal', 'outOfRangeVal', 'noDataVal', \
                    'dfCurvCoeff', 'mode', 'maxDistance'

                arrays_dict = {k: process_helper.get_input_data_array(request.inputs[k]) for k in params}
                arrays_dict = process_helper.make_dicts_list_from_lists_dict(arrays_dict, new_keys)

                if not operation:
                    arrays_dict = arrays_dict[0:0]

                gdal_out_format = 'GTiff' if output_tif and not operation else 'MEM'

                for vp in arrays_dict:
                    # d_path = tempfile.mkstemp(dir=os.path.dirname(raster_filename))[1]
                    d_path = tif_output_filename if gdal_out_format != 'MEM' else ''
                    src_ds = gdal.ViewshedGenerate(input_band, gdal_out_format, d_path, co, **vp)
                    if src_ds is None:
                        raise Exception('error occurred')
                    src_ds.GetRasterBand(1).SetNoDataValue(vp['noDataVal'])
                    if operation:
                        files.append(src_ds)
                    else:
                        dst_ds = src_ds

            if operation:
                alpha_pattern = '1*({}>3)'
                operand = '+'
                hide_nodata = True
                calc, kwargs = gdal_calc.make_calc(files, alpha_pattern, operand)
                color_table = process_helper.get_color_table(request.inputs, 'color_palette')
                gdal_out_format = 'GTiff' if output_tif else 'MEM'
                dst_ds = gdal_calc.Calc(
                    calc, outfile=tif_output_filename, extent=extent, format=gdal_out_format,
                    color_table=color_table, hideNodata=hide_nodata, return_ds=gdal_out_format == 'MEM', **kwargs)

            if czml_output_filename is not None and dst_ds is not None:
                gdal_to_czml.gdal_to_czml(dst_ds, name=czml_output_filename, out_filename=czml_output_filename)

            dst_ds = None  # close ds
            for i in range(len(files)):
                files[i] = None

            if output_tif:
                response.outputs['tif'].output_format = FORMATS.GEOTIFF
                response.outputs['tif'].file = tif_output_filename
            if output_czml:
                response.outputs['czml'].output_format = czml_format
                response.outputs['czml'].file = czml_output_filename

        return response

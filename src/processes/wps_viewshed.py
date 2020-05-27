import tempfile

import gdal, osr
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
from gdalos.calc import gdal_calc, gdal_to_czml
from gdalos import gdalos_trans, projdef


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
            extent = process_helper.get_request_data(request.inputs, 'extent')
            if extent is not None:
                # I'm not sure why the extent is in format miny, minx, maxy, maxx
                extent = [float(x) for x in extent]
                extent = GeoRectangle.from_min_max(extent[1], extent[3], extent[0], extent[2])
            else:
                extent = request.inputs['m'][0].data

            cutline = process_helper.get_request_data(request.inputs, 'cutline')
            operation = process_helper.get_request_data(request.inputs, 'o')

            czml_output_filename = tempfile.mktemp(suffix=czml_format.extension) if output_czml else None
            tif_output_filename = tempfile.mktemp(suffix=FORMATS.GEOTIFF.extension) if output_tif else None

            files = []
            if 'fr' in request.inputs:
                for fr in request.inputs['fr']:
                    fr_filename, ds = process_helper.open_ds_from_wps_input(fr)
                    if operation:
                        files.append(ds)
                    else:
                        tif_output_filename = fr_filename
                        ds1 = ds
            else:
                raster_filename, input_ds = process_helper.open_ds_from_wps_input(request.inputs['r'][0])
                response.outputs['r'].data = raster_filename

                input_band: gdal.Band = input_ds.GetRasterBand(request.inputs['bi'][0].data)

                if input_band is None:
                    raise Exception('band number out of range')

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
                    arrays_dict = arrays_dict[0:1]

                # in_raster_srs = projdef.get_srs_pj_from_ds(input_ds)
                in_raster_srs = osr.SpatialReference()
                in_raster_srs.ImportFromWkt(input_ds.GetProjection())
                if not in_raster_srs.IsProjected:
                    raise Exception(f'input raster has to be projected')

                in_coords_crs_pj = process_helper.get_request_data(request.inputs, 'in_crs')
                if in_coords_crs_pj is not None:
                    in_coords_crs_pj = projdef.get_proj_string(in_coords_crs_pj)
                    transform_coords_to_raster = projdef.get_transform(in_coords_crs_pj, in_raster_srs)
                else:
                    transform_coords_to_raster = None

                pjstr_src_srs = projdef.get_srs_pj_from_ds(input_ds)
                out_crs = process_helper.get_request_data(request.inputs, 'out_crs')
                pjstr_tgt_srs = projdef.get_proj_string(out_crs) if out_crs is not None else pjstr_src_srs
                post_process_needed = cutline or not projdef.proj_is_equivalent(pjstr_src_srs, pjstr_tgt_srs)

                # steps:
                # 1. viewshed
                # 2. calc
                # 3. post process
                # 4. czml
                steps = 1
                if operation:
                    steps += 1
                if output_czml:
                    steps += 1
                if post_process_needed:
                    steps += 1

                use_temp_tif = True  # todo: why dosn't it work without it?
                # gdal_out_format = 'GTiff' if use_temp_tif or (output_tif and not operation) else 'MEM'
                gdal_out_format = 'GTiff' if steps == 1 else 'MEM'

                co = None
                if 'co' in request.inputs:
                    co = []
                    for coi in request.inputs['co']:
                        creation_option: str = coi.data
                        sep_index = creation_option.find('=')
                        if sep_index == -1:
                            raise Exception(f'creation option {creation_option} unsupported')
                        co.append(creation_option)

                color_table = process_helper.get_color_table(request.inputs, 'color_palette')

                for vp in arrays_dict:
                    if transform_coords_to_raster:
                        vp['observerX'], vp['observerY'], _ = transform_coords_to_raster.TransformPoint(vp['observerX'], vp['observerY'])
                    d_path = tempfile.mktemp(suffix='.tif') if use_temp_tif else tif_output_filename if gdal_out_format != 'MEM' else ''
                    gdal_out_format = 'GTiff' if steps == 1 or use_temp_tif else 'MEM'
                    ds = gdal.ViewshedGenerate(input_band, gdal_out_format, d_path, co, **vp)
                    if ds is None:
                        raise Exception('error occurred')

                    src_band = ds.GetRasterBand(1)
                    src_band.SetNoDataValue(vp['noDataVal'])

                    if operation:
                        if use_temp_tif:
                            files.append(d_path)
                        else:
                            files.append(ds)
                    else:
                        if color_table:
                            src_band.SetRasterColorTable(color_table)
                            src_band.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
                    src_band = None

            input_ds = None
            input_band = None

            steps -= 1

            if operation:
                alpha_pattern = '1*({}>3)'
                operand = '+'
                hide_nodata = True
                calc, kwargs = gdal_calc.make_calc(files, alpha_pattern, operand)

                d_path = tempfile.mktemp(
                    suffix='.tif') if use_temp_tif else tif_output_filename if gdal_out_format != 'MEM' else ''
                gdal_out_format = 'GTiff' if steps == 1 or use_temp_tif else 'MEM'

                ds = gdal_calc.Calc(
                    calc, outfile=d_path, extent=extent, cutline=cutline, format=gdal_out_format,
                    color_table=color_table, hideNodata=hide_nodata, return_ds=True, **kwargs)
                if ds is None:
                    raise Exception('error occurred')
                for i in range(len(files)):
                    files[i] = None  # close calc input ds(s)
                steps -= 1

            if post_process_needed:
                # gdal_out_format = 'GTiff' if steps == 1 else 'MEM'
                d_path = tempfile.mktemp(
                    suffix='.tif') if use_temp_tif else tif_output_filename if gdal_out_format != 'MEM' else ''
                gdal_out_format = 'GTiff' if steps == 1 or use_temp_tif else 'MEM'

                ds = gdalos_trans(ds, out_filename=d_path, warp_CRS=pjstr_tgt_srs,
                                      cutline=cutline, of=gdal_out_format, return_ds=True, ovr_type=None)
                if ds is None:
                    raise Exception('error occurred')
                steps -= 1

            if czml_output_filename is not None and ds is not None:
                gdal_to_czml.gdal_to_czml(ds, name=czml_output_filename, out_filename=czml_output_filename)

            ds = None  # close ds

            if output_tif:
                response.outputs['tif'].output_format = FORMATS.GEOTIFF
                response.outputs['tif'].file = tif_output_filename
            if output_czml:
                response.outputs['czml'].output_format = czml_format
                response.outputs['czml'].file = czml_output_filename

        return response

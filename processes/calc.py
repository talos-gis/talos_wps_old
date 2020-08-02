import tempfile
from pywps import FORMATS
from pywps.app import Process
from pywps.app.Common import Metadata
from pywps.inout import ComplexOutput
from pywps.response.execute import ExecuteResponse

from .process_defaults import process_defaults, LiteralInputD, ComplexInputD, BoundingBoxInputD
from processes import process_helper

from gdalos.rectangle import GeoRectangle
from gdalos.calc import gdal_calc, gdal_to_czml, gdalos_combine
from backend.formats import czml_format
from gdalos import gdalos_util


class Calc(Process):
    def __init__(self):
        process_id = 'calc'
        defaults = process_defaults(process_id)
        inputs = [
            LiteralInputD(defaults, 'output_czml', 'make output as czml', data_type='boolean',
                         min_occurs=0, max_occurs=1, default=False),
            LiteralInputD(defaults, 'output_tif', 'make output as tif', data_type='boolean',
                         min_occurs=0, max_occurs=1, default=True),

            ComplexInputD(defaults, 'r', 'input rasters', supported_formats=[FORMATS.GEOTIFF],
                         min_occurs=1, max_occurs=23, default=None),
            LiteralInputD(defaults, 'a', 'alpha pattern', data_type='string',
                         min_occurs=1, max_occurs=1, default='1*({}>3)'),

            LiteralInputD(defaults, 'c', 'custom calc', data_type='string',
                          min_occurs=0, max_occurs=1, default=None),
            LiteralInputD(defaults, 'f', 'function', data_type='string',
                          min_occurs=0, max_occurs=1, default='sum'),
            LiteralInputD(defaults, 'o', 'operator', data_type='string',
                          min_occurs=0, max_occurs=1, default='+'),

            LiteralInputD(defaults, 'm', 'extent combine mode', data_type='integer',
                          min_occurs=1, max_occurs=1, default=2),
            LiteralInputD(defaults, 'h', 'hide Nodata', data_type='boolean',
                          min_occurs=0, max_occurs=1, default=True),
            ComplexInputD(defaults, 'color_palette', 'color palette', supported_formats=[FORMATS.TEXT],
                         min_occurs=0, max_occurs=1, default=None),
            # ComplexInputD(defaults, 'cutline', 'input vector cutline',
            #              supported_formats=[FORMATS.GML],
            #              # crss=['EPSG:4326', ], metadata=[Metadata('EPSG.io', 'http://epsg.io/'), ],
            #              min_occurs=0, max_occurs=1, default=None),
            # LiteralInputD(defaults, 'process_palette', 'put palette in czml description', data_type='integer',
            #              min_occurs=1, max_occurs=1, default=2),
            BoundingBoxInputD(defaults, 'extent', 'extent BoundingBox',
                             crss=['EPSG:4326', ], metadata=[Metadata('EPSG.io', 'http://epsg.io/'), ],
                             min_occurs=0, max_occurs=1, default=None)
        ]
        outputs = [
            ComplexOutput('output', 'result raster', supported_formats=[FORMATS.GEOTIFF, czml_format]),
        ]

        super().__init__(
            self._handler,
            identifier=process_id,
            version='1.0.0',
            title='gdal calc',
            abstract='gdal calc',
            inputs=inputs,
            outputs=outputs,
            metadata=[Metadata('raster')],
            # profile='',
            # store_supported=True,
            # status_supported=True
        )

    def _handler(self, request, response: ExecuteResponse):
        calc = process_helper.get_request_data(request.inputs, 'c')
        func = process_helper.get_request_data(request.inputs, 'f')
        operand = process_helper.get_request_data(request.inputs, 'o')

        if not (calc or func or operand):
            raise Exception('Please provide one of: calc, func, operand')

        of: str = process_helper.get_request_data(request.inputs, 'of')
        ext = gdalos_util.get_ext_by_of(of)
        is_czml = ext == '.czml'

        # process_palette = request.inputs['process_palette'][0].data if output_czml else 0
        # cutline = process_helper.get_request_data(request.inputs, 'cutline')
        extent = process_helper.get_request_data(request.inputs, 'extent')
        if extent is not None:
            # I'm not sure why the extent is in format miny, minx, maxy, maxx
            extent = [float(x) for x in extent]
            extent = GeoRectangle.from_min_max(extent[1], extent[3], extent[0], extent[2])
        else:
            extent = request.inputs['m'][0].data

        alpha_pattern = process_helper.get_request_data(request.inputs, 'a')
        hide_nodata = process_helper.get_request_data(request.inputs, 'h')

        output_filename = tempfile.mktemp(suffix=ext)
        gdal_out_format = 'MEM' if is_czml else 'GTiff'

        files = []
        for r in request.inputs['r']:
            _, src_ds = process_helper.open_ds_from_wps_input(r)
            files.append(src_ds)

        kwargs = dict()
        if calc is None:
            if func:
                calc, kwargs = gdalos_combine.make_calc_with_func(files, alpha_pattern, func, **kwargs)
            else:
                calc, kwargs = gdalos_combine.make_calc_with_operand(files, alpha_pattern, operand, **kwargs)
        color_table = process_helper.get_color_table(request.inputs, 'color_palette')
        dst_ds = gdal_calc.Calc(
            calc, outfile=output_filename, extent=extent, format=gdal_out_format,
            color_table=color_table, hideNodata=hide_nodata, return_ds=gdal_out_format == 'MEM', **kwargs)

        if output_filename is not None and dst_ds is not None:
            gdal_to_czml.gdal_to_czml(dst_ds, name=output_filename, out_filename=output_filename)

        dst_ds = None  # close ds
        for i in range(len(files)):
            files[i] = None

        response.outputs['output'].output_format = czml_format if is_czml else FORMATS.GEOTIFF
        response.outputs['output'].file = output_filename

        return response

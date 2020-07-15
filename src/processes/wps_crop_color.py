# todo: https://pywps.readthedocs.io/en/master/wps.html#wps
# * The input or output can also be result of any OGC OWS service.
# * how to select output format?
# wkt input <wps:ComplexData mimeType="application/wkt"><![CDATA[Polygon((21.98 38.04, 22.4 37.95, 22.12 37.53, 21.98 38.04))]]></wps:ComplexData>

# import owslib.wps
import tempfile
from pywps import FORMATS
from pywps.app import Process
from pywps.app.Common import Metadata
from pywps.inout import ComplexOutput, LiteralOutput
from pywps.response.execute import ExecuteResponse

from gdalos.calc import gdal_dem_color_cutline
from backend.formats import czml_format
from gdalos import gdalos_util
from gdalos.rectangle import GeoRectangle
from .process_defaults import process_defaults, LiteralInputD, ComplexInputD, BoundingBoxInputD
from processes import process_helper
from gdalos.gdalos_color import ColorPalette


class GdalDem(Process):
    def __init__(self):
        process_id = 'crop_color'
        defaults = process_defaults(process_id)
        inputs = [
            LiteralInputD(defaults, 'of', 'output format (czml, gtiff)', data_type='string',
                          min_occurs=0, max_occurs=1, default='gtiff'),
            LiteralInputD(defaults, 'output_czml', 'make output as czml', data_type='boolean',
                         min_occurs=0, max_occurs=1, default=None),
            LiteralInputD(defaults, 'output_tif', 'make output as tif', data_type='boolean',
                         min_occurs=0, max_occurs=1, default=None),

            ComplexInputD(defaults, 'r', 'input raster', supported_formats=[FORMATS.GEOTIFF],
                         min_occurs=1, max_occurs=1, default=None),
            ComplexInputD(defaults, 'color_palette', 'color palette', supported_formats=[FORMATS.TEXT],
                         min_occurs=0, max_occurs=1, default=None),
            ComplexInputD(defaults, 'cutline', 'input vector cutline',
                         supported_formats=[FORMATS.GML],
                         # crss=['EPSG:4326', ], metadata=[Metadata('EPSG.io', 'http://epsg.io/'), ],
                         min_occurs=0, max_occurs=1, default=None),
            LiteralInputD(defaults, 'process_palette', 'put palette in czml description', data_type='integer',
                         min_occurs=1, max_occurs=1, default=2),
            BoundingBoxInputD(defaults, 'extent', 'extent BoundingBox',
                             crss=['EPSG:4326', ], metadata=[Metadata('EPSG.io', 'http://epsg.io/'), ],
                             min_occurs=0, max_occurs=1, default=None)
        ]
        outputs = [
            LiteralOutput('r', 'input raster name', data_type='string'),
            ComplexOutput('output', 'result raster', supported_formats=[FORMATS.GEOTIFF, czml_format]),
            ComplexOutput('tif', 'result as GeoTIFF', supported_formats=[FORMATS.GEOTIFF]),  # backwards compatibility
            ComplexOutput('czml', 'result as CZML', supported_formats=[czml_format])  # backwards compatibility
        ]

        super().__init__(
            self._handler,
            identifier=process_id,
            version='1.0.0',
            title='crops to an extent and/or to a cutline polygon[s] and/or makes a color relief',
            abstract='returns a color relief of the input raster inside the given extent or cutline polygon[s]',
            inputs=inputs,
            outputs=outputs,
            metadata=[Metadata('raster')],
            # profile='',
            # store_supported=True,
            # status_supported=True
        )

    def _handler(self, request, response: ExecuteResponse):
        output_czml = process_helper.get_request_data(request.inputs, 'output_czml')
        output_tif = process_helper.get_request_data(request.inputs, 'output_tif')
        of: str = process_helper.get_request_data(request.inputs, 'of')
        if output_czml:
            of = 'czml'
        ext = gdalos_util.get_ext_by_of(of)
        is_czml = ext == '.czml'
        output_czml = is_czml
        output_tif = not is_czml

        if output_czml or output_tif:
            process_palette = request.inputs['process_palette'][0].data if output_czml else 0
            cutline = request.inputs['cutline'][0].file if 'cutline' in request.inputs else None
            # color_palette = request.inputs['color_palette'][0].file if 'color_palette' in request.inputs else None
            color_palette = ColorPalette.from_string_list(
                process_helper.get_request_data(request.inputs, 'color_palette', True))
            extent = request.inputs['extent'][0].data if 'extent' in request.inputs else None
            if extent is not None:
                # I'm not sure why the extent is in format miny, minx, maxy, maxx
                extent = [float(x) for x in extent]
                extent = GeoRectangle.from_min_max(extent[1], extent[3], extent[0], extent[2])

            czml_output_filename = tempfile.mktemp(suffix=czml_format.extension) if output_czml else None
            tif_output_filename = tempfile.mktemp(suffix=FORMATS.GEOTIFF.extension) if output_tif else None
            output_filename = tif_output_filename or czml_output_filename

            # gdal_out_format = 'czml' if output_format.extension == '.czml' else 'GTiff'
            # gdal_out_format = 'MEM' if is_czml else output_format
            gdal_out_format = 'GTiff' if output_tif else 'MEM'

            raster_filename, src_ds = process_helper.open_ds_from_wps_input(request.inputs['r'][0])

            ds = gdal_dem_color_cutline.czml_gdaldem_crop_and_color(
                ds=src_ds,
                czml_output_filename=czml_output_filename,
                out_filename=tif_output_filename,
                extent=extent, cutline=cutline,
                color_palette=color_palette,
                process_palette=process_palette,
                output_format=gdal_out_format)
            del ds
            del src_ds

            response.outputs['output'].output_format = czml_format if is_czml else FORMATS.GEOTIFF
            response.outputs['output'].file = output_filename

            if output_tif:
                response.outputs['tif'].output_format = FORMATS.GEOTIFF
                response.outputs['tif'].file = tif_output_filename
            if output_czml:
                response.outputs['czml'].output_format = czml_format
                response.outputs['czml'].file = czml_output_filename

        response.outputs['r'].data = raster_filename
        # response.outputs['output'].uom = UOM('unity')
        return response

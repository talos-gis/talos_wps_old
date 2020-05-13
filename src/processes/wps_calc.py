import tempfile
from pywps import FORMATS, Format
from pywps.app import Process
from pywps.app.Common import Metadata
from pywps.inout import ComplexOutput, LiteralOutput
from pywps.response.execute import ExecuteResponse

from backend import gdal_dem_color_cutline
from gdalos.rectangle import GeoRectangle
from .process_defaults import process_defaults, LiteralInputD, ComplexInputD, BoundingBoxInputD
from processes import process_helper
from pathlib import Path
from gdalos import gdalos_color
from gdalos.calc import gdal_calc
import os

czml_format = Format('application/czml+json', extension='.czml')
wkt_format = Format('application/wkt', extension='.wkt')


class Calc(Process):
    def __init__(self):
        process_id = 'calc'
        defaults = process_defaults(process_id)
        inputs = [
            ComplexInputD(defaults, 'r', 'input rasters', supported_formats=[FORMATS.GEOTIFF],
                         min_occurs=1, default=None),
            LiteralInputD(defaults, 'a', 'alpha pattern', data_type='string',
                         min_occurs=1, max_occurs=1, default='1*({}>3)'),
            LiteralInputD(defaults, 'o', 'operator', data_type='string',
                          min_occurs=1, max_occurs=1, default='+'),
            LiteralInputD(defaults, 'm', 'extent combine mode', data_type='integer',
                          min_occurs=1, max_occurs=1, default=2),
            LiteralInputD(defaults, 'h', 'hide Nodata', data_type='boolean',
                          min_occurs=0, max_occurs=1, default=True),
            LiteralInputD(defaults, 'c', 'custom calc', data_type='string',
                          min_occurs=0, max_occurs=1, default=None),

            LiteralInputD(defaults, 'output_czml', 'make output as czml', data_type='boolean',
                         min_occurs=0, max_occurs=1, default=False),
            LiteralInputD(defaults, 'output_tif', 'make output as tif', data_type='boolean',
                         min_occurs=0, max_occurs=1, default=True),
            ComplexInputD(defaults, 'color_palette', 'color palette', supported_formats=[FORMATS.TEXT],
                         min_occurs=0, max_occurs=1, default=None),
            # ComplexInputD(defaults, 'cutline', 'input vector cutline',
            #              supported_formats=[FORMATS.GML],
            #              # crss=['EPSG:4326', ], metadata=[Metadata('EPSG.io', 'http://epsg.io/'), ],
            #              min_occurs=0, max_occurs=1, default=None),
            LiteralInputD(defaults, 'process_palette', 'put palette in czml description', data_type='integer',
                         min_occurs=1, max_occurs=1, default=2),
            BoundingBoxInputD(defaults, 'extent', 'extent BoundingBox',
                             crss=['EPSG:4326', ], metadata=[Metadata('EPSG.io', 'http://epsg.io/'), ],
                             min_occurs=0, max_occurs=1, default=None)
        ]
        outputs = [
            ComplexOutput('tif', 'result as GeoTIFF', supported_formats=[FORMATS.GEOTIFF]),
            ComplexOutput('czml', 'result as CZML', supported_formats=[czml_format])
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
        output_czml = request.inputs['output_czml'][0].data
        output_tif = request.inputs['output_tif'][0].data
        if output_czml or output_tif:
            process_palette = request.inputs['process_palette'][0].data if output_czml else 0
            cutline = request.inputs['cutline'][0].file if 'cutline' in request.inputs else None
            color_palette = request.inputs['color_palette'][0].file if 'color_palette' in request.inputs else None
            extent = request.inputs['extent'][0].data if 'extent' in request.inputs else None
            if extent is not None:
                # I'm not sure why the extent is in format miny, minx, maxy, maxx
                extent = [float(x) for x in extent]
                extent = GeoRectangle.from_min_max(extent[1], extent[3], extent[0], extent[2])
            else:
                extent = request.inputs['m'][0].data
            operand = request.inputs['o'][0].data if 'o' in request.inputs else None
            alpha_pattern = request.inputs['a'][0].data if 'a' in request.inputs else None
            hideNodata = request.inputs['h'][0].data if 'h' in request.inputs else None
            calc = request.inputs['c'][0].data if 'c' in request.inputs else None

            czml_output_filename = tempfile.mktemp(suffix=czml_format.extension) if output_czml else None
            tif_output_filename = tempfile.mktemp(suffix=FORMATS.GEOTIFF.extension) if output_tif else None

            gdal_out_format = 'GTiff' if output_tif else 'MEM'

            files = []
            for r in request.inputs['r']:
                raster_filename, src_ds = process_helper.open_ds_from_wps_input(r)
                files.append(src_ds)

            color_filename, temp_color_filename = gdalos_color.save_palette(color_palette)
            pal = gdalos_color.ColorPalette()
            pal.read(color_filename)
            color_table = pal.get_color_table()
            if temp_color_filename:
                os.remove(temp_color_filename)

            kwargs = dict()
            if calc is None:
                calc, kwargs = gdal_calc.make_calc(files, alpha_pattern, operand, **kwargs)

            gdal_calc.Calc(calc, outfile=tif_output_filename, extent=extent,
                           color_table=color_table, hideNodata=hideNodata, **kwargs)

            if output_tif:
                response.outputs['tif'].output_format = FORMATS.GEOTIFF
                response.outputs['tif'].file = tif_output_filename
            if output_czml:
                response.outputs['czml'].output_format = czml_format
                response.outputs['czml'].file = czml_output_filename

        return response

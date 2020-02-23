# todo: https://pywps.readthedocs.io/en/master/wps.html#wps
# * The input or output can also be result of any OGC OWS service.
# * Data are on the server already (local/remote input tif)
# * optional extent input
# * multiple input/output formats
# wkt input <wps:ComplexData mimeType="application/wkt"><![CDATA[Polygon((21.98 38.04, 22.4 37.95, 22.12 37.53, 21.98 38.04))]]></wps:ComplexData>
# czml3 push
# pywps production flask?
# docker image

from pywps import FORMATS, Format
from pywps.app import Process
from pywps.inout import ComplexInput, LiteralInput, BoundingBoxInput, ComplexOutput
from pywps.response.execute import ExecuteResponse

from processes import gdal_dem_color_cutline

czml_format = Format('application/czml+json', extension='.czml')
wkt_format = Format('application/wkt', extension='.wkt')


class GdalDem(Process):
    def __init__(self):
        inputs = [
            # ComplexInput('raster', 'input raster', supported_formats=[FORMATS.GEOTIFF]),
            LiteralInput('raster', 'input raster', data_type='string'),
            ComplexInput('cutline', 'input vector cutline', supported_formats=[FORMATS.GML]),
            ComplexInput('color_palette', 'color palette', supported_formats=[FORMATS.TEXT]),
            # BoundingBoxInput('extent', 'extent BoundingBox', ['EPSG:4326', ],
            #                  metadata=[Metadata('EPSG.io', 'http://epsg.io/'), ]),
        ]
        outputs = [
            # ComplexOutput('output', 'output', supported_formats=[FORMATS.GEOTIFF])
            ComplexOutput('output', 'output', supported_formats=[czml_format])
        ]

        super().__init__(
            self._handler,
            identifier='color_relief_cutline',
            version='0.1',
            title='color relief of in polygon',
            abstract='returns a color relief of the input raster inside the given extent or cutline polygon[s]',
            inputs=inputs,
            outputs=outputs,
            # metadata=[Metadata('bla'), Metadata('bla')],
            # profile='',
            # store_supported=True,
            # status_supported=True
        )

    def _handler(self, request, response: ExecuteResponse):
        raster = request.inputs['raster'][0].data
        # raster = request.inputs['raster'][0].url
        # raster = '/home/idan/maps/srtm.tif'
        cutline = request.inputs['cutline'][0].file
        color_palette = request.inputs['color_palette'][0].file
        # ur = request.inputs['extent'][0].ur
        # ll = request.inputs['extent'][0].ll
        # extent = [*ll, *ur]

        output_format = czml_format
        output_path = gdal_dem_color_cutline.get_named_temporary_filenme(suffix=output_format.extension)

        gdal_out_format = 'czml' if output_format.extension == '.czml' else 'GTiff'

        gdal_dem_color_cutline.gdaldem_crop_and_color(filename=raster, out_filename=output_path,
                                                      cutline=cutline, color_palette=color_palette,
                                                      output_format=gdal_out_format)

        response.outputs['output'].output_format = output_format
        response.outputs['output'].file = output_path

        return response

import gdal
from pywps import FORMATS
from pywps.app import Process
from pywps.inout import ComplexInput, ComplexOutput
from .process_defaults import process_defaults, LiteralInputD, ComplexInputD, BoundingBoxInputD
from pywps.app.Common import Metadata
import numpy as np
from pywps.response.execute import ExecuteResponse


class Invert(Process):
    def __init__(self):
        process_id = 'invert'
        defaults = process_defaults(process_id)
        inputs = [
            ComplexInputD(defaults, 'A', 'input_raster', supported_formats=[FORMATS.GEOTIFF])
        ]
        outputs = [
            ComplexOutput('output', 'result raster', supported_formats=[FORMATS.GEOTIFF])
        ]

        super().__init__(
            self._handler,
            identifier=process_id,
            version='1.0.0',
            title='invert the values of the raster',
            abstract='invert',
            profile='',
            metadata=[Metadata('raster')],
            inputs=inputs,
            outputs=outputs,
            store_supported=True,
            status_supported=True
        )

    def _handler(self, request, response: ExecuteResponse):
        raster_filename = request.inputs['A'][0].file

        s_ds: gdal.Dataset = gdal.Open(raster_filename, gdal.GA_ReadOnly)
        s_band: gdal.Band = s_ds.GetRasterBand(1)
        (s_min, s_max, *_) = s_band.GetStatistics(False, True)
        # todo GetVirtualMemArray
        s_ndv = s_band.GetNoDataValue()
        s_array = s_band.ReadAsArray()
        s_array = np.ma.masked_equal(s_array, s_ndv)

        d_array = s_max + s_min - s_array

        d_path = raster_filename + '_inverse'
        d_ds: gdal.Dataset = gdal.GetDriverByName('GTIFF').Create(d_path, s_ds.RasterXSize, s_ds.RasterYSize, 1,
                                                                  s_band.DataType)
        d_ds.SetProjection(s_ds.GetProjection())
        d_ds.SetGeoTransform(s_ds.GetGeoTransform())

        d_band = d_ds.GetRasterBand(1)
        d_band.SetNoDataValue(s_ndv)
        d_band.WriteArray(d_array)
        d_band.FlushCache()

        del d_band
        del d_ds

        response.outputs['output'].output_format = FORMATS.GEOTIFF
        response.outputs['output'].file = d_path

        return response

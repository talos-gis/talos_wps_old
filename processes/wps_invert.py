import gdal
from pywps import FORMATS
from pywps.app import Process
from pywps.inout import ComplexInput, ComplexOutput
from pywps.app.Common import Metadata
import numpy as np
from pywps.response.execute import ExecuteResponse


class Invert(Process):
    def __init__(self):
        inputs = [
            ComplexInput('A', 'input_raster', supported_formats=[FORMATS.GEOTIFF])
        ]
        outputs = [
            ComplexOutput('result', 'result', supported_formats=[FORMATS.GEOTIFF])
        ]

        super().__init__(
            self._handler,
            identifier='invert',
            version='1.3.3.7',
            title='invert the values of the raster',
            abstract='invert',
            profile='',
            metadata=[Metadata('bla'), Metadata('bla')],
            inputs=inputs,
            outputs=outputs,
            store_supported=True,
            status_supported=True
        )

    def _handler(self, request, response: ExecuteResponse):
        s_path = request.inputs['A'][0].file

        s_ds: gdal.Dataset = gdal.OpenEx(s_path)
        s_band: gdal.Band = s_ds.GetRasterBand(1)
        (s_min, s_max, *_) = s_band.GetStatistics(False, True)
        # todo GetVirtualMemArray
        s_ndv = s_band.GetNoDataValue()
        s_array = s_band.ReadAsArray()
        s_array = np.ma.masked_equal(s_array, s_ndv)

        d_array = s_max + s_min - s_array

        d_path = s_path + '_inverse'
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

        response.outputs['result'].output_format = FORMATS.GEOTIFF
        response.outputs['result'].file = d_path

        return response

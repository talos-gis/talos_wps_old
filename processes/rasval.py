import gdal
from pywps import FORMATS, UOM
from pywps.app import Process
from pywps.inout import LiteralOutput
from .process_defaults import process_defaults, LiteralInputD, ComplexInputD
from pywps.app.Common import Metadata
from pywps.response.execute import ExecuteResponse
from gdalos.calc import get_pixel_from_raster
from processes import process_helper

import numpy as np

# from pywps.inout.literaltypes import LITERAL_DATA_TYPES


class RasterValue(Process):
    def __init__(self):
        process_id = 'ras_val'
        defaults = process_defaults(process_id)
        inputs = [
            ComplexInputD(defaults, 'r', 'input_raster', supported_formats=[FORMATS.GEOTIFF]),
            LiteralInputD(defaults, 'bi', 'band_index', data_type='positiveInteger', min_occurs=0, max_occurs=1, default=1),

            LiteralInputD(defaults, 'x', 'x or longitude or pixel', data_type='float', min_occurs=1, uoms=[UOM('metre')]),
            LiteralInputD(defaults, 'y', 'y or latitude or line', data_type='float', min_occurs=1, uoms=[UOM('metre')]),

            LiteralInputD(defaults, 'c', 'coordinate kind: ll/xy/pl', data_type='string', min_occurs=1, max_occurs=1, default='ll'),
            LiteralInputD(defaults, 'interpolate', 'interpolate ', data_type='boolean', min_occurs=1, max_occurs=1, default=True),
        ]
        outputs = [LiteralOutput('v', 'raster value at the requested coordinate as float', data_type='float'),
                   LiteralOutput('output', 'raster value at the requested coordinate (as string)', data_type='string')]

        super().__init__(
            self._handler,
            identifier=process_id,
            version='1.0.0',
            title='raster values',
            abstract='get raster values at given coordinates',
            profile='',
            metadata=[Metadata('raster')],
            inputs=inputs,
            outputs=outputs,
            store_supported=True,
            status_supported=True
        )

    def _handler(self, request, response: ExecuteResponse):
        raster_filename, ds = process_helper.open_ds_from_wps_input(request.inputs['r'][0])

        band: gdal.Band = ds.GetRasterBand(request.inputs['bi'][0].data)
        if band is None:
            raise Exception('band number out of range')

        c = request.inputs['c'][0].data.lower() if 'c' in request.inputs else None
        if c is None:
            srs = None
        else:
            if c == 'pl':
                srs = None
            elif c == 'xy':
                srs = False
            elif c == 'll':
                srs = True
            else:
                raise Exception('Unknown xy format {}'.format(c))

        x = process_helper.get_input_data_array(request.inputs['x'])
        y = process_helper.get_input_data_array(request.inputs['y'])

        if len(x) != len(y):
            raise Exception('length(x)={} is different from length(y)={}'.format(len(x), len(y)))

        if len(x) == 1:
            value = get_pixel_from_raster.get_pixel_from_raster(ds, x[0], y[0], srs)
            response.outputs['v'].output_format = FORMATS.TEXT
            response.outputs['v'].data = value
            response.outputs['output'].output_format = FORMATS.TEXT
            response.outputs['output'].data = str(value)
        elif len(x) > 1:
            points = np.dstack((x, y))[0]
            values = get_pixel_from_raster.get_pixel_from_raster_multi(ds, points, srs)
            if values:
                response.outputs['v'].output_format = FORMATS.TEXT
                response.outputs['v'].data = values
                response.outputs['output'].output_format = FORMATS.TEXT
                response.outputs['output'].data = str(values)
        del ds

        return response

import tempfile
import os.path

import gdal
from pywps import FORMATS
from pywps.app import Process
from pywps.inout import ComplexInput, ComplexOutput, LiteralInput
from pywps.app.Common import Metadata
from pywps.response.execute import ExecuteResponse


class ViewShed(Process):
    def __init__(self):
        inputs = [
            ComplexInput('r', 'input_raster', supported_formats=[FORMATS.GEOTIFF]),
            LiteralInput('bi', 'band_index', data_type='positiveInteger', min_occurs=0, default=1),
            LiteralInput('co', 'creation options', data_type='string', min_occurs=0, max_occurs=-1),
            LiteralInput('ndv', 'nodata_value', data_type='float', min_occurs=0, default=-1),
            LiteralInput('ox', 'observer_X', data_type='float'),
            LiteralInput('oy', 'observer_Y', data_type='float'),
            LiteralInput('oz', 'observer_Z', data_type='float'),
            LiteralInput('tz', 'target_z', data_type='float'),
            LiteralInput('md', 'maximum_distance', data_type='float'),
            LiteralInput('cc', 'curve_coefficient', data_type='float', min_occurs=0, default=0),
            LiteralInput('iv', 'invisible_value', data_type='float', min_occurs=0, default=0),
            LiteralInput('ov', 'out_of_bounds_value', data_type='float', min_occurs=0, default=0),
            LiteralInput('vv', 'visible_value', data_type='float', min_occurs=0, default=255),
        ]
        outputs = [
            ComplexOutput('result', 'result', supported_formats=[FORMATS.GEOTIFF])
        ]

        super().__init__(
            self._handler,
            identifier='viewshed',
            version='1.3.3.7',
            title='viewshed raster analysis',
            abstract='runs gdal.viewshed',
            profile='',
            metadata=[Metadata('bla'), Metadata('bla')],
            inputs=inputs,
            outputs=outputs,
            store_supported=True,
            status_supported=True
        )

    def _handler(self, request, response: ExecuteResponse):
        s_path = request.inputs['r'][0].file

        s_ds: gdal.Dataset = gdal.OpenEx(s_path)
        s_band: gdal.Band = s_ds.GetRasterBand(request.inputs['bi'][0].data)

        if s_band is None:
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

        d_path = tempfile.mkstemp(dir=os.path.dirname(s_path))[1]

        dest = gdal.ViewshedGenerate(s_band, 'GTIFF', d_path, co,
                                     request.inputs['ox'][0].data, request.inputs['oy'][0].data,
                                     request.inputs['oz'][0].data, request.inputs['tz'][0].data,

                                     request.inputs['vv'][0].data, request.inputs['iv'][0].data,
                                     request.inputs['ov'][0].data, request.inputs['ndv'][0].data,

                                     request.inputs['cc'][0].data,
                                     mode=2,
                                     maxDistance=request.inputs['md'][0].data)

        if dest is None:
            raise Exception('error occurred')

        del dest

        response.outputs['result'].output_format = FORMATS.GEOTIFF
        response.outputs['result'].file = d_path

        return response

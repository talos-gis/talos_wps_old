import osgeo.gdal
from pywps import Process, LiteralInput, LiteralOutput, UOM
from .process_defaults import process_defaults, LiteralInputD


class GetInfo(Process):
    def __init__(self):
        process_id = 'info'
        defaults = process_defaults(process_id)
        # inputs = [LiteralInputD(defaults, 'name', 'Input name', data_type='string', default=None)]
        outputs = [LiteralOutput('output', 'Output response', data_type='string')]

        super(GetInfo, self).__init__(
            self._handler,
            identifier=process_id,
            title='Service info',
            abstract='Returns service info',
            version='1.0.0',
            # inputs=inputs,
            outputs=outputs,
            store_supported=True,
            status_supported=True
        )

    def _handler(self, request, response):
        response.outputs['output'].data = 'Gdal version: {}'.format(osgeo.gdal.__version__)
        response.outputs['output'].uom = UOM('unity')
        return response

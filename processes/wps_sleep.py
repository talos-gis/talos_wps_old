import time
from pywps import Process, LiteralInput, LiteralOutput, UOM
from .process_defaults import process_defaults, LiteralInputD


class Sleep(Process):
    def __init__(self):
        process_id = 'sleep'
        defaults = process_defaults(process_id)
        inputs = [LiteralInputD(defaults, 'seconds', 'sleep seconds', data_type='float', default=3)]
        outputs = [LiteralOutput('time', 'Float Output response', data_type='float'),
                   LiteralOutput('output', 'String Output response', data_type='string')]

        super(Sleep, self).__init__(
            self._handler,
            identifier=process_id,
            title='Process Sleep',
            abstract='Returns how many seconds it really slept',
            version='0.0.1',
            inputs=inputs,
            outputs=outputs,
            store_supported=True,
            status_supported=True
        )

    def _handler(self, request, response):
        t = time.time()
        seconds = request.inputs['seconds'][0].data
        time.sleep(seconds)
        t = time.time() - t
        response.outputs['time'].data = t
        response.outputs['output'].data = 'I slept for {} seconds'.format(t)
        response.outputs['time'].uom = UOM('unity')
        response.outputs['output'].uom = UOM('unity')
        return response

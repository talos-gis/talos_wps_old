import time
from pywps import Process, LiteralInput, LiteralOutput, UOM
from .process_defaults import process_defaults, LiteralInputD


class Sleep2(Process):
    def __init__(self):
        process_id = 'sleep'
        defaults = process_defaults(process_id)
        inputs = [LiteralInputD(defaults, 'delay', 'sleep seconds', data_type='float', default=3)]
        outputs = [LiteralOutput('time', 'Float Output response', data_type='float'),
                   LiteralOutput('output', 'String Output response', data_type='string')]

        super(Sleep2, self).__init__(
            self._handler,
            identifier=process_id,
            title='Process Sleep',
            abstract='Returns how many seconds it really slept',
            version='1.0.0',
            inputs=inputs,
            outputs=outputs,
            store_supported=True,
            status_supported=True
        )

    def _handler(self, request, response):
        t = time.time()
        sleep_delay = request.inputs['delay'][0].data
        time.sleep(sleep_delay)
        t = time.time() - t
        response.outputs['time'].data = t
        response.outputs['time'].uom = UOM('unity')
        response.outputs['output'].data = 'I slept for {} sleep_delay'.format(t)
        response.outputs['output'].uom = UOM('unity')
        return response

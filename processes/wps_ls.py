import glob
from pywps import Process, LiteralInput, LiteralOutput, UOM


class ls(Process):
    def __init__(self):
        inputs = [
            LiteralInput('dir', 'argument', data_type='string', min_occurs=0, default='./static/data'),
            LiteralInput('pattern', 'argument', data_type='string', min_occurs=0, default='/*.tif'),
            LiteralInput('r', 'recursive', data_type='boolean', min_occurs=0, max_occurs=1, default=False),
            ]
        outputs = [LiteralOutput('output',
                                 'Output response', data_type='string')]

        super(ls, self).__init__(
            self._handler,
            identifier='ls',
            title='Process ls',
            abstract='Returns a the output of ls to the provided dir',
            version='1.0.0',
            inputs=inputs,
            outputs=outputs,
            store_supported=True,
            status_supported=True
        )

    def _handler(self, request, response):
        files = []
        r = request.inputs['r'][0].data
        for d in request.inputs['dir']:
            dir = d.data
            for p in request.inputs['pattern']:
                pattern = p.data
                pattern = dir + pattern
                files.extend([f for f in glob.glob(pattern, recursive=r)])
        files = list(files)
        response.outputs['output'].data = str(files)

        response.outputs['output'].uom = UOM('unity')
        return response

import glob
from pywps import Process, LiteralInput, LiteralOutput, UOM
from .process_defaults import process_defaults, LiteralInputD
from pathlib import Path


class ls(Process):
    def __init__(self):
        process_id = 'ls'
        defaults = process_defaults(process_id)
        inputs = [
            LiteralInputD(defaults, 'dir', 'argument', data_type='string', min_occurs=0, default='./sample/maps'),
            LiteralInputD(defaults, 'pattern', 'argument', data_type='string', min_occurs=0, default='*.tif'),
            LiteralInputD(defaults, 'r', 'recursive', data_type='boolean', min_occurs=0, max_occurs=1, default=False),
            ]
        outputs = [LiteralOutput('output',
                                 'Output response', data_type='string')]

        super(ls, self).__init__(
            self._handler,
            identifier=process_id,
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
            dir = Path(d.data)
            for p in request.inputs['pattern']:
                pattern = Path(p.data)
                pattern = dir / pattern
                files.extend([f for f in glob.glob(str(pattern), recursive=r)])
        files = list(files)
        response.outputs['output'].data = str(files)

        response.outputs['output'].uom = UOM('unity')
        return response

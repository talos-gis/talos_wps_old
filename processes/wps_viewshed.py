import tempfile
import os.path

import gdal
from pywps import FORMATS, UOM
from pywps.app import Process
from pywps.inout import LiteralInput, ComplexInput, LiteralOutput, ComplexOutput
from .process_defaults import process_defaults, LiteralInputD, ComplexInputD, BoundingBoxInputD
from pywps.app.Common import Metadata
from pywps.response.execute import ExecuteResponse
from processes import process_helper


class ViewShed(Process):
    def __init__(self):
        process_id = 'viewshed'
        defaults = process_defaults(process_id)
        inputs = [
            ComplexInputD(defaults, 'r', 'input_raster', supported_formats=[FORMATS.GEOTIFF]),
            LiteralInputD(defaults, 'bi', 'band_index', data_type='positiveInteger', min_occurs=0, default=1),
            LiteralInputD(defaults, 'co', 'creation options', data_type='string', min_occurs=0, max_occurs=-1),
            LiteralInputD(defaults, 'ndv', 'nodata_value', data_type='float', uoms=[UOM('metre')], min_occurs=0, default=-1),
            LiteralInputD(defaults, 'ox', 'observer_X', data_type='float', uoms=[UOM('metre')]),
            LiteralInputD(defaults, 'oy', 'observer_Y', data_type='float', uoms=[UOM('metre')]),
            LiteralInputD(defaults, 'oz', 'observer_Z', data_type='float', uoms=[UOM('metre')]),
            LiteralInputD(defaults, 'tz', 'target_z', data_type='float', uoms=[UOM('metre')]),
            LiteralInputD(defaults, 'md', 'maximum_distance', data_type='float', uoms=[UOM('metre')]),
            LiteralInputD(defaults, 'cc', 'curve_coefficient', data_type='float', min_occurs=0, default=0),
            LiteralInputD(defaults, 'iv', 'invisible_value', data_type='float', min_occurs=0, default=0),
            LiteralInputD(defaults, 'ov', 'out_of_bounds_value', data_type='float', min_occurs=0, default=0),
            LiteralInputD(defaults, 'vv', 'visible_value', data_type='float', min_occurs=0, default=255),
        ]
        outputs = [
            LiteralOutput('r', 'input raster name', data_type='string'),
            ComplexOutput('tif', 'result as GeoTIFF', supported_formats=[FORMATS.GEOTIFF])]

        super().__init__(
            self._handler,
            identifier=process_id,
            version='1.0',
            title='viewshed raster analysis',
            abstract='runs gdal.ViewshedGenerate',
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

        co = None
        if 'co' in request.inputs:
            co = []
            for coi in request.inputs['co']:
                creation_option: str = coi.data
                sep_index = creation_option.find('=')
                if sep_index == -1:
                    raise Exception(f'creation option {creation_option} unsupported')
                co.append(creation_option)

        d_path = tempfile.mkstemp(dir=os.path.dirname(raster_filename))[1]

        dest = gdal.ViewshedGenerate(band, 'GTIFF', d_path, co,
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

        response.outputs['r'].data = raster_filename
        response.outputs['tif'].output_format = FORMATS.GEOTIFF
        response.outputs['tif'].file = d_path

        return response

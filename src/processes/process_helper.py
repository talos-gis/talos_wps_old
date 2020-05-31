import os
from gdalos import gdalos_util
from gdalos import gdalos_color


def get_request_data(request_input, name, get_file: bool = False, index=0):
    # result = request_input[name][index].data if name in request_input else None
    if name not in request_input:
        return None
    result = request_input[name][index]
    result = result.file if get_file else result.data
    if result == 'None':
        result = None  # todo: is this a bug?
    return result


def get_input_data_array(request_input):
    return [x.data for x in request_input]


def open_ds_from_wps_input(request_input):
    # ds: gdal.Dataset
    raster_filename = request_input.file
    try:
        ds = gdalos_util.open_ds(raster_filename)
    except:
        ds = None
    if ds is None:
        raster_filename = request_input.data
        ds = gdalos_util.open_ds(raster_filename)
    if ds is None:
        raise Exception('cannot open file {}'.format(raster_filename))
    return raster_filename, ds



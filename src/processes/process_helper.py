import os
from gdalos import gdalos_util
from gdalos import gdalos_color


def get_input_data_array(request_input):
    return [x.data for x in request_input]


def open_ds_from_wps_input(request_input):
    raster_filename = request_input.file
    # ds: gdal.Dataset
    ds = gdalos_util.open_ds(raster_filename)
    if ds is None:
        raster_filename = request_input.data
        ds = gdalos_util.open_ds(raster_filename)
    if ds is None:
        raise Exception('cannot open file {}'.format(raster_filename))
    return raster_filename, ds


def fill_arrays(*args):
    max_len = max(len(x) for x in args)
    result = []
    for x in range(len(args)):
        lx = len(x)
        if lx < max_len:
            v = x[lx-1]
            for i in range(lx, max_len):
                x.append(v)
        result.append(x)
    return result


def fill_arrays_dict(d: dict):
    max_len = max(len(v) for v in d.values())
    result = dict()
    for k, v in d.items():
        len_v = len(v)
        if len_v < max_len:
            v = v[len_v-1]
            for i in range(len_v, max_len):
                v.append(v)
        result[k] = v
    return result


def make_dicts_list_from_lists_dict(d: dict, new_keys):
    max_len = max(len(v) for v in d.values())
    result = []
    new_d = dict()
    new_keys = new_keys or d.keys()
    for i in range(max_len):
        new_d = new_d.copy()
        for k, v in zip(new_keys, d.values()):
            len_v = len(v)
            if i < len_v:
                new_d[k] = v[i]
        result.append(new_d)
    return result


def get_color_table(request_inputs, name: str = 'color_palette'):
    color_palette = request_inputs[name][0].file if name in request_inputs else None
    color_filename, temp_color_filename = gdalos_color.save_palette(color_palette)
    pal = gdalos_color.ColorPalette()
    pal.read(color_filename)
    color_table = pal.get_color_table()
    if temp_color_filename:
        os.remove(temp_color_filename)
    return color_table
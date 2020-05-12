from gdalos import gdalos_util


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

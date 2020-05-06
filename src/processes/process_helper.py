from gdalos import gdal_helper


def get_input_data_array(request_input):
    return [x.data for x in request_input]


def open_ds_from_wps_input(request_input):
    raster_filename = request_input.file
    # ds: gdal.Dataset
    ds = gdal_helper.open_ds(raster_filename)
    if ds is None:
        raster_filename = request_input.data
        ds = gdal_helper.open_ds(raster_filename)
    if ds is None:
        raise Exception('cannot open file {}'.format(raster_filename))
    return raster_filename, ds

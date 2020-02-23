import os
import tempfile
from typing import Optional, Sequence, List, Union
from osgeo import gdal, ogr, osr
from gdalos.rectangle import GeoRectangle
from gdalos import gdal_helper
from processes import gdal_to_czml


def wkt_write_ogr(path, wkt_list, of='ESRI Shapefile', epsg=4326):
    driver = ogr.GetDriverByName(of)
    ds = driver.CreateDataSource(path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)

    layer = ds.CreateLayer('', srs, ogr.wkbUnknown)
    for wkt in wkt_list:
        feature = ogr.Feature(layer.GetLayerDefn())
        geom = ogr.CreateGeometryFromWkt(wkt)
        feature.SetGeometry(geom)  # Set the feature geometry
        layer.CreateFeature(feature)  # Create the feature in the layer
        feature.Destroy()  # Destroy the feature to free resources
    # Destroy the data source to free resources
    ds.Destroy()


# def get_named_temporary_filenme(suffix='', dir_name=''):
#     filename = next(tempfile._get_candidate_names())+suffix
#     if dir_name is None:
#         return filename
#     else:
#         if dir_name=='':
#             dir_name = tempfile._get_default_tempdir()
#         return os.path.join(dir_name, filename)


def gdal_crop(src_ds: gdal.Dataset, out_filename: str, output_format: str = 'MEM',
              extent: Optional[GeoRectangle] = None,
              cutline: Optional[Union[str, List[str]]] = None,
              common_options: dict = None):
    common_options = dict(common_options or dict())
    translate_options = {}
    warp_options = {}
    temp_filename = None

    if cutline is None:
        if extent is None:
            return src_ds
        # -projwin minx maxy maxx miny (ulx uly lrx lry)
        translate_options['projWin'] = extent.lurd
        # -te minx miny maxx maxy
    else:
        if extent is not None:
            warp_options['outputBounds'] = extent.ldru
        warp_options['dstNodata'] = -32768
        # warp_options['dstAlpha'] = True
        warp_options['cropToCutline'] = True

        if isinstance(cutline, str):
            cutline_filename = cutline
        elif isinstance(cutline, Sequence):
            temp_filename = tempfile.mktemp(suffix='.gpkg')
            cutline_filename = temp_filename
            wkt_write_ogr(cutline_filename, cutline, of='GPKG')
        warp_options['cutlineDSName'] = cutline_filename
    # else:
    #     raise Exception("extent is unknown {}".format(extent))

    common_options['format'] = output_format
    if warp_options:
        ds = gdal.Warp(str(out_filename), src_ds, **common_options, **warp_options)
    else:
        ds = gdal.Translate(str(out_filename), src_ds, **common_options, **translate_options)
    if temp_filename is not None:
        os.remove(temp_filename)
    return ds


def gdaldem_crop_and_color(filename: str, out_filename: str,
                           extent: Optional[GeoRectangle] = None,
                           cutline: Optional[Union[str, List[str]]] = None,
                           color_palette: Optional[Union[str, Sequence[str]]] = None,
                           output_format: str = 'GTiff', common_options: dict = None):
    is_czml = output_format.lower() == 'czml'
    do_color = color_palette is not None
    do_crop = (extent or cutline) is not None

    src_ds = gdal_helper.open_ds(filename)
    if src_ds is None:
        raise Exception('fail to open filename {}'.format(filename))

    if is_czml:
        dst_wkt = src_ds.GetProjectionRef()
        if dst_wkt.find('AUTHORITY["EPSG","4326"]') == -1:
            raise Exception('fail, unsupported projection')

    if do_crop:
        of = 'MEM' if do_color else output_format
        ds = gdal_crop(src_ds, out_filename, output_format=of, extent=extent, cutline=cutline,
                       common_options=common_options)
        if ds is None:
            raise Exception('fail to crop {}'.format(filename))
        elif ds is not src_ds:
            del src_ds
            src_ds = ds
    if do_color:
        of = 'MEM' if is_czml else output_format
        temp_filename = None
        if isinstance(color_palette, str):
            color_filename = color_palette
        elif isinstance(color_palette, Sequence):
            temp_filename = tempfile.mktemp(suffix='.txt')
            color_filename = temp_filename
            with open(temp_filename, 'w') as f:
                for item in color_palette:
                    f.write(item+'\n')
        else:
            raise Exception('Unknown color palette type {}'.format(color_palette))

        dem_options = {
            'addAlpha': True,
            'format': of,
            'processing': 'color-relief',
            'colorFilename': color_filename}
        ds = gdal.DEMProcessing(out_filename, src_ds, **dem_options)
        if temp_filename is not None:
            os.remove(temp_filename)
        if ds is None:
            raise Exception('fail to color {}'.format(filename))
        elif ds is not src_ds:
            del src_ds
            src_ds = ds

    if is_czml:
        output_czml = gdal_to_czml.gdal_to_czml(src_ds, name=out_filename)
        with open(out_filename, 'w') as f:
            print(output_czml, file=f)

    del src_ds


def get_wkt_list(filename):
    ds = ogr.Open(filename, 0)
    layer = ds.GetLayer()
    wkt_list = []
    for feature in layer:
        geom = feature.GetGeometryRef()
        wkt_list.append(geom.ExportToWkt())
    return wkt_list


def read_list(filename):
    return [line.rstrip('\n') for line in open(filename)]


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.realpath(__file__))
    root_data = os.path.join(script_dir, r'../static/data')
    shp_filename = os.path.join(root_data, r'poly.shp')
    color_palette_filename = os.path.join(root_data, r'color_file.txt')
    wkt_list = get_wkt_list(shp_filename)
    color_palette = read_list(color_palette_filename)
    raster_filename = os.path.join(root_data, r'srtm_x35_y32.tif')
    gdaldem_crop_and_color(
        filename=raster_filename,
        out_filename=tempfile.mktemp(suffix='.tif'),
        cutline=wkt_list,
        color_palette=color_palette,
        output_format='GTiff')

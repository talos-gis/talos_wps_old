import os
import tempfile
from typing import Optional, Sequence, List, Union
from osgeo import gdal, ogr, osr
from gdalos.rectangle import GeoRectangle
from backend import gdal_to_czml
import re


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


def gdal_crop(ds: gdal.Dataset, out_filename: str, output_format: str = 'MEM',
              extent: Optional[GeoRectangle] = None,
              cutline: Optional[Union[str, List[str]]] = None,
              common_options: dict = None):
    common_options = dict(common_options or dict())
    translate_options = {}
    warp_options = {}
    temp_filename = None

    if cutline is None:
        if extent is None:
            return ds
        # -projwin minx maxy maxx miny (ulx uly lrx lry)
        translate_options['projWin'] = extent.lurd
        # -te minx miny maxx maxy
    else:
        if extent is not None:
            warp_options['outputBounds'] = extent.ldru
        warp_options['cropToCutline'] = extent is None
        warp_options['dstNodata'] = -32768
        # warp_options['dstAlpha'] = True

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
        ds = gdal.Warp(str(out_filename), ds, **common_options, **warp_options)
    else:
        ds = gdal.Translate(str(out_filename), ds, **common_options, **translate_options)
    if temp_filename is not None:
        os.remove(temp_filename)
    return ds


def make_czml_description(stats, colors):
    if stats:
        if colors:
            return ' '.join(['{:.2f}:#{:06X}'.format(x, c) for x, c in zip(stats, colors)])
        else:
            return ' '.join(['{:.2f}'.format(x) for x in stats])
    else:
        return None


def czml_gdaldem_crop_and_color(ds: gdal.Dataset, czml_output_filename: str, **kwargs):
    ds, stats, colors = gdaldem_crop_and_color(ds=ds, **kwargs)
    if ds is None:
        raise Exception('fail to color')
    if czml_output_filename is not None:
        dst_wkt = ds.GetProjectionRef()
        if dst_wkt.find('AUTHORITY["EPSG","4326"]') == -1:
            raise Exception('fail, unsupported projection')
        description = make_czml_description(stats, colors)
        output_czml_doc = gdal_to_czml.gdal_to_czml(ds, name=czml_output_filename, description=description)
        with open(czml_output_filename, 'w') as f:
            print(output_czml_doc, file=f)
    return ds


def pal_color_to_rgb(color):
    # r g b a -> argb
    # todo: support color names or just find the gdal implementation of this function...
    color = re.findall(r'\d+', color)
    try:
        if len(color) == 1:
            return int(color[0])
        elif len(color) == 3:
            return (int(color[0]) * 255 + int(color[1])) * 255 + int(color[2])
        elif len(color) == 4:
            return ((int(color[3]) * 255 + int(color[0])) * 255 + int(color[1])) * 255 + int(color[2])
        else:
            return 0
    except:
        return 0


def color_palette_stats(color_filename, min_val, max_val, process_palette):
    stats = []
    colors = []
    if process_palette:
        process_colors = process_palette is ...
        try:
            with open(color_filename) as fp:
                for line in fp:
                    split_line = line.strip().split(' ', maxsplit=1)
                    num_str = split_line[0].strip()
                    if process_colors:
                        color = pal_color_to_rgb(split_line[1])
                    is_percent = num_str.endswith('%')
                    if is_percent:
                        num_str = num_str.rstrip('%')
                    try:
                        num = float(num_str)
                        if is_percent:
                            num = (max_val-min_val)*num*0.01+min_val
                        stats.append(num)
                        if process_colors:
                            colors.append(color)
                    except ValueError:
                        pass
        except IOError:
            stats = None
    return stats, colors


def gdaldem_crop_and_color(ds: gdal.Dataset,
                           out_filename: str, output_format: str = 'GTiff',
                           extent: Optional[GeoRectangle] = None,
                           cutline: Optional[Union[str, List[str]]] = None,
                           color_palette: Optional[Union[str, Sequence[str]]] = None,
                           process_palette=...,
                           common_options: dict = None):
    do_color = color_palette is not None
    do_crop = (extent or cutline) is not None

    if out_filename is None:
        out_filename = ''
        if output_format != 'MEM':
            raise Exception('output filename is None')

    if do_crop:
        output_format_crop = 'MEM' if do_color else output_format
        ds = gdal_crop(ds, out_filename,
                       output_format=output_format_crop, extent=extent, cutline=cutline,
                       common_options=common_options)
        if ds is None:
            raise Exception('fail to crop')

    bnd = ds.GetRasterBand(1)
    bnd.ComputeStatistics(0)
    min_val = bnd.GetMinimum()
    max_val = bnd.GetMaximum()

    if do_color:
        temp_color_filename = None
        if isinstance(color_palette, str):
            color_filename = color_palette
        elif isinstance(color_palette, Sequence):
            temp_color_filename = tempfile.mktemp(suffix='.txt')
            color_filename = temp_color_filename
            with open(temp_color_filename, 'w') as f:
                for item in color_palette:
                    f.write(item+'\n')
        else:
            raise Exception('Unknown color palette type {}'.format(color_palette))
        stats, colors = color_palette_stats(color_filename, min_val, max_val, process_palette)
        dem_options = {
            'addAlpha': True,
            'format': output_format,
            'processing': 'color-relief',
            'colorFilename': color_filename}
        ds = gdal.DEMProcessing(out_filename, ds, **dem_options)
        if temp_color_filename is not None:
            os.remove(temp_color_filename)
        if ds is None:
            raise Exception('fail to color')
    else:
        stats = [min_val, max_val]
    return ds, stats, colors


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
    root_data = os.path.join(script_dir, r'./data/sample')
    shp_filename = os.path.join(root_data, r'shp/poly.shp')
    color_palette_filename = os.path.join(root_data, r'color_files/color_file.txt')
    wkt_list = get_wkt_list(shp_filename)
    color_palette = read_list(color_palette_filename)
    raster_filename = os.path.join(root_data, r'maps/srtm1_x35_y32.tif')
    gdaldem_crop_and_color(
        filename=raster_filename,
        out_filename=tempfile.mktemp(suffix='.tif'),
        cutline=wkt_list,
        color_palette=color_palette,
        output_format='GTiff')

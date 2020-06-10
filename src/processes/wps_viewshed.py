import tempfile

from pywps import FORMATS, UOM
from pywps.app import Process
from pywps.inout import LiteralOutput, ComplexOutput
from .process_defaults import process_defaults, LiteralInputD, ComplexInputD, BoundingBoxInputD
from pywps.app.Common import Metadata
from pywps.response.execute import ExecuteResponse
from processes import process_helper
from gdalos.viewshed.viewshed_params import viewshed_defaults, atmospheric_refraction_coeff
from backend.formats import czml_format
from gdalos import GeoRectangle
from gdalos import gdalos_util
from gdalos.viewshed.viewshed_calc import viewshed_calc, CalcOperation
from gdalos.viewshed.viewshed_params import ViewshedParams
from pywps.inout.literaltypes import LITERAL_DATA_TYPES


class ViewShed(Process):
    def __init__(self):
        process_id = 'viewshed'

        defaults = process_defaults(process_id)
        mm = dict(min_occurs=1, max_occurs=1000)
        mm0 = dict(min_occurs=0, max_occurs=1000)
        mmm = dict(data_type='float', uoms=[UOM('metre')], **mm)
        mmm0 = dict(data_type='float', uoms=[UOM('metre')], **mm0)
        dmm = dict(data_type='float', uoms=[UOM('degree')], **mm)
        # 254 is the max possible values for unique function. for sum it's not really limited
        inputs = [
            LiteralInputD(defaults, 'out_crs', 'output raster crs', data_type='string', default=None, min_occurs=0, max_occurs=1),
            LiteralInputD(defaults, 'of', 'output format (czml, gtiff)', data_type='string',
                          min_occurs=0, max_occurs=1, default='gtiff'),

            ComplexInputD(defaults, 'r', 'input raster', supported_formats=[FORMATS.GEOTIFF], min_occurs=1, max_occurs=1),

            LiteralInputD(defaults, 'bi', 'band index', data_type='positiveInteger', default=1, min_occurs=0, max_occurs=1),
            LiteralInputD(defaults, 'co', 'creation options', data_type='string', min_occurs=0, max_occurs=1),

            LiteralInputD(defaults, 'min_r', 'Minimum visibility range/radius/distance', default=0, **mmm0),  # todo
            LiteralInputD(defaults, 'max_r', 'Maximum visibility range/radius/distance', **mmm),  # was: md

            # obeserver x,y in the given CRSr
            LiteralInputD(defaults, 'in_crs', 'observer input crs', data_type='string', default=None, min_occurs=0, max_occurs=1),
            LiteralInputD(defaults, 'ox', 'observer X/longitude', **mmm),
            LiteralInputD(defaults, 'oy', 'observer Y/latitude', **mmm),

            # observer and target height/altitude/elevation
            LiteralInputD(defaults, 'oz', 'observer height/altitude/elevation', **mmm),
            LiteralInputD(defaults, 'tz', 'target height/altitude/elevation', **mmm),

            # https://en.wikipedia.org/wiki/Height_above_ground_level AMSL/AGL
            LiteralInputD(defaults, 'oza', 'observer height mode AGL(True) / AMSL(False)', default=True, data_type='boolean', **mm),  # todo
            LiteralInputD(defaults, 'tza', 'target height mode AGL(True) / AMSL(False)', default=True, data_type='boolean', **mm),  # todo

            # angles
            LiteralInputD(defaults, 'azimuth', 'horizontal azimuth direction', default=0, **dmm),  # todo
            LiteralInputD(defaults, 'h_aperture', 'horizontal aperture', default=360, **dmm),  # todo
            LiteralInputD(defaults, 'elevation', 'vertical elevation direction', default=0, **dmm),  # todo
            LiteralInputD(defaults, 'v_aperture', 'vertical aperture', default=180, **dmm),  # todo

            # optional values
            LiteralInputD(defaults, 'vv', 'visible_value', default=viewshed_defaults['vv'], **mmm),
            LiteralInputD(defaults, 'iv', 'invisible_value', default=viewshed_defaults['iv'], **mmm),
            LiteralInputD(defaults, 'ov', 'out_of_bounds_value', default=viewshed_defaults['ov'], **mmm),
            LiteralInputD(defaults, 'ndv', 'nodata_value', default=viewshed_defaults['ndv'], **mmm),

            # http://resources.esri.com/help/9.3/arcgisdesktop/com/gp_toolref/spatial_analyst_tools/how_viewshed_works.htm
            # https://desktop.arcgis.com/en/arcmap/10.3/tools/spatial-analyst-toolbox/using-viewshed-and-observer-points-for-visibility.htm
            # For applications involving visibility with radio waves,
            # the refraction correction to be applied depends on the wavelength of the signal.
            # The location of telecommunication sites is not merely a simple matter of determining the intervisibility
            # but, rather, involves a number of parameters associated with the modeling of radio wave propagation
            # including reflection, refraction specific to the frequency, attenuation (signal weakening),
            # interference, atmospheric effects, and so on.
            # Nonetheless, Observer Points and Viewshed are appropriate tools to use during the preliminary
            # investigation stages of assessing possible telecommunication sites and coverage.

            # http://web.soccerlab.polymtl.ca/grass/monsterViewer.php?functionName=main&fileName=/data/project-manager/grass/grassSVN/grass-addons/raster/r.viewshed/main.cc&iframe=true&width=100%&height=100%#cloneCode
            # atmospheric refraction coeff. 1/7 for visual, 0.325 for radio waves,
            # in future we might calculate this based on the physics, for now we just fudge by the 1/7th approximation.

            # https://invest.readthedocs.io/en/3.4.1/final_ecosystem_services/scenic_quality.html
            # refraction (float) – The earth curvature correction option corrects for the curvature of the
            # earth and refraction of visible light in air. Changes in air density curve the light downward causing
            # an observer to see further and the earth to appear less curved. While the magnitude of this effect varies
            # with atmospheric conditions, a standard rule of thumb is that refraction of visible light reduces the
            # apparent curvature of the earth by one-seventh. By default, this model corrects for the curvature of the
            # earth and sets the refractivity coefficient to 0.13.

            # https://gdal.org/programs/gdal_viewshed.html
            # https://grass.osgeo.org/grass78/manuals/r.viewshed.html
            # grass refraction_coeff  = 1/7 ~= 0.14286
            # gdal: curve_coefficient(cc) = 1-refraction_coeff = 0.85714 ~= 6/7
            # gdal: height_corrected = dem_height - cc * target_distance^2/sphere_diameter = dem_height
            # talos: earth_curve_factor = 1/cc = 1/(1-refraction_coeff); refraction_coeff = 1-1/earth_curve_factor
            # talos: refraction_coeff = 1/7 -> earth_curve_factor = 7/6

            # refraction_coeff values
            # 0 -> normal sphere without correction
            # 1/7 ~= 0.14286 -> normal correction for visible light
            # 0.25~0.325 -> radio waves
            # 1 -> flat earth

            # advanced parameters
            LiteralInputD(defaults, 'alg', 'Viewshed algorithm to use',
                          default=None, data_type='string', **mm0),  # todo
            LiteralInputD(defaults, 'refraction_coeff', 'atmospheric refraction correction coefficient',
                          default=atmospheric_refraction_coeff, data_type='float', **mm),  # was: 1-cc
            LiteralInputD(defaults, 'mode', 'viewshed calc mode', default=2, data_type='integer', **mm),

            ComplexInputD(defaults, 'color_palette', 'color palette', supported_formats=[FORMATS.TEXT],
                          min_occurs=0, max_occurs=1, default=None),

            # output extent definition
            LiteralInputD(defaults, 'extent_c', 'extent combine mode 2:union/3:intersection', data_type='integer',
                          min_occurs=1, max_occurs=1, default=2),  # was: m
            BoundingBoxInputD(defaults, 'extent', 'extent BoundingBox',
                              crss=['EPSG:4326', ], metadata=[Metadata('EPSG.io', 'http://epsg.io/'), ],
                              min_occurs=0, max_occurs=1, default=None),
            ComplexInputD(defaults, 'cutline', 'output vector cutline',
                          supported_formats=[FORMATS.GML],
                          # crss=['EPSG:4326', ], metadata=[Metadata('EPSG.io', 'http://epsg.io/'), ],
                          min_occurs=0, max_occurs=1, default=None),

            # combine calc modes
            LiteralInputD(defaults, 'o', 'operation viewshed/max/count/count_z/unique', data_type='string',
                          min_occurs=0, max_occurs=1, default=None),

            ComplexInputD(defaults, 'fr', 'fake input rasters (for debugging)', supported_formats=[FORMATS.GEOTIFF],
                          min_occurs=0, max_occurs=23, default=None),

        ]
        outputs = [
            LiteralOutput('r', 'input raster name', data_type='string'),
            ComplexOutput('output', 'result raster', supported_formats=[FORMATS.GEOTIFF, czml_format]),
        ]

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
        of: str = process_helper.get_request_data(request.inputs, 'of')
        ext = gdalos_util.get_ext_by_of(of)
        is_czml = ext == '.czml'

        extent = process_helper.get_request_data(request.inputs, 'extent')
        if extent is not None:
            # I'm not sure why the extent is in format miny, minx, maxy, maxx
            extent = [float(x) for x in extent]
            extent = GeoRectangle.from_min_max(extent[1], extent[3], extent[0], extent[2])
        else:
            extent = request.inputs['extent_c'][0].data

        cutline = process_helper.get_request_data(request.inputs, 'cutline', True)
        operation = process_helper.get_request_data(request.inputs, 'o')
        if not operation:
            operation = None
        else:
            try:
                i = int(operation)
                if i == 0:
                    operation = CalcOperation.viewshed
                elif i == 1:
                    operation = CalcOperation.count
                elif i == 2:
                    operation = CalcOperation.unique
                operation = CalcOperation(i)
            except ValueError:
                try:
                    operation = CalcOperation[operation]
                except ValueError:
                    raise Exception ('unknown operation requested {}'.format(operation))

        color_palette = process_helper.get_request_data(request.inputs, 'color_palette', True)

        output_filename = tempfile.mktemp(suffix=ext)

        co = None
        files = []
        if 'fr' in request.inputs:
            for fr in request.inputs['fr']:
                fr_filename, ds = process_helper.open_ds_from_wps_input(fr)
                if operation:
                    files.append(ds)
                else:
                    output_filename = fr_filename
            input_ds = bi = arrays_dict = in_coords_crs_pj = out_crs = color_palette = None

        else:
            raster_filename, input_ds = process_helper.open_ds_from_wps_input(request.inputs['r'][0])
            response.outputs['r'].data = raster_filename
            bi = request.inputs['bi'][0].data

            in_coords_crs_pj = process_helper.get_request_data(request.inputs, 'in_crs')
            out_crs = process_helper.get_request_data(request.inputs, 'out_crs')

            if 'co' in request.inputs:
                co = []
                for coi in request.inputs['co']:
                    creation_option: str = coi.data
                    sep_index = creation_option.find('=')
                    if sep_index == -1:
                        raise Exception(f'creation option {creation_option} unsupported')
                    co.append(creation_option)

            params = ViewshedParams.__slots__
            arrays_dict = {k: process_helper.get_input_data_array(request.inputs[k]) for k in params}

        viewshed_calc(input_ds=input_ds, bi=bi,
                      output_filename=output_filename, co=co, of=of,
                      vp_array=arrays_dict, extent=extent, cutline=cutline, operation=operation,
                      in_coords_crs_pj=in_coords_crs_pj, out_crs=out_crs,
                      color_palette=color_palette,
                      files=files)

        response.outputs['output'].output_format = czml_format if is_czml else FORMATS.GEOTIFF
        response.outputs['output'].file = output_filename

        return response


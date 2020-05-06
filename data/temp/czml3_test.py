# from czml3.examples import simple
# output=simple

import gdal
from wps.processes import gdal_to_czml

raster_filename = r'd:\dev\czml\1.tif'
ds = gdal.Open(raster_filename, gdal.GA_ReadOnly)
output = gdal_to_czml.gdal_to_czml(ds, name="")
del ds

print(output)

output_filename = "czml3.czml"
with open(output_filename, 'w') as f:
    print(output, file=f)

server=http://localhost:5000/wps

## GET
# say hello
curl "$server?service=WPS&request=execute&version=1.0.0&Identifier=say_hello&storeExecuteResponse=true&DataInputs=name=Idan&RawDataOutput=output"
curl "$server?service=WPS&request=execute&version=1.0.0&Identifier=ls&storeExecuteResponse=true&DataInputs=dir=./static/maps&DataInputs=pattern=*.tif&RawDataOutput=output"

# viewshed with sampled data
curl "$server?service=WPS&request=execute&version=1.0.0&Identifier=viewshed&storeExecuteResponse=true&DataInputs=r=@xlink:href=file:./sample/maps/srtm1_x35_y32.tif;ox=35.21317;oy=32.03437;oz=100;tz=0;md=1"

# viewshed with mapped volume data
curl "$server?service=WPS&request=execute&version=1.0.0&Identifier=viewshed&storeExecuteResponse=true&DataInputs=r=@xlink:href=file:./static/maps/srtm1_x33-62_y23-39.tif;ox=35.21317;oy=32.03437;oz=100;tz=0;md=1"
curl "$server?service=WPS&request=execute&version=1.0.0&Identifier=viewshed&storeExecuteResponse=true&DataInputs=r=@xlink:href=file:./static/maps/srtm1_x35_y32.tif;ox=35.21317;oy=32.03437;oz=100;tz=0;md=1" # -o ./outputs/viewshed.tif && cat ./outputs/viewshed.tif


## POST
curl -H "Content-type: xml" -X POST -d@./sample/requests/crop_color_sample_czml_post.xml $server # -o ./outputs/crop_color_sample_czml_post.czml && cat ./outputs/crop_color_sample_czml_post.czml
curl -H "Content-type: xml" -X POST -d@./sample/requests/crop_color_sample_post.xml $server -o outputs/crop_color_sample.tif
curl -H "Content-type: xml" -X POST -d@./sample/requests/crop_color_post.xml http://localhost/wps -o outputs/crop_color.tif

curl -H "Content-type: xml" -X POST -d@./sample/requests/viewshed_post.xml $server


## clear request cache
rm ./logs/pywps-logs.sqlite3
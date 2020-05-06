shopt -s expand_aliases

sudo docker container stop $(sudo docker container ls -aq) && sudo docker container rm $(sudo docker container ls -aq)

sudo docker build -t talos_wps:latest -t talos_wps:latest .

sudo docker run \
  -it \
  -p 5000:5000 \
  --name talos_wps_test \
  --env WORKDIR=/app \
  --mount type=bind,source=/home/idan/maps,target=/app/data/static/maps,readonly \
  --mount type=bind,source=/home/idan/dev/talos_wps/data/static/config,target=/app/data/static/config,readonly \
  talos_wps:latest

server=http://localhost:5000/wps

curl "$server?service=WPS&request=execute&version=1.0.0&Identifier=say_hello&storeExecuteResponse=true&DataInputs=name=Idan&RawDataOutput=output"
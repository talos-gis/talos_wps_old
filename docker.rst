sudo docker build -t talosgis/talos_wps:release-1.0.2 -t talosgis/talos_wps:latest .

sudo docker run \
  -d \
  -it \
  -p 5000:5000 \
  --name talos_wps_test \
  --env WORKDIR=/app \
  --mount type=bind,source=/home/idan/maps,target=/app/static/data,readonly \
  talosgis/talos_wps:latest
    
sudo docker exec -it talos_wps_test bash

sudo docker ps -all

sudo docker system prune

To stop all running containers use the docker container stop command followed by a list of all containers IDs.
$ sudo docker container stop $(sudo docker container ls -aq)

Once all containers are stopped, you can remove them using the docker container rm command followed by the containers ID list.
$ sudo docker container rm $(sudo docker container ls -aq)

sudo docker container stop $(sudo docker container ls -aq) && sudo docker container rm $(sudo docker container ls -aq)


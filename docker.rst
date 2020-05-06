sudo docker container stop $(sudo docker container ls -aq) && sudo docker container rm $(sudo docker container ls -aq)

sudo docker build -t talos_wps:latest -t talos_wps:latest .

sudo docker run \
  -d \
  -it \
  -p 5000:5000 \
  --name talos_wps_test \
  --env WORKDIR=/app \
  --mount type=bind,source=/home/idan/maps,target=/app/data/static/maps,readonly \
  --mount type=bind,source=/home/idan/dev/talos_wps/data/static/config,target=/app/data/static/config,readonly \
  talos_wps:latest


sudo docker start talos_wps_test
sudo docker restart talos_wps_test

sudo docker exec -it talos_wps_test bash

sudo docker ps -all

sudo docker system prune

To stop all running containers use the docker container stop command followed by a list of all containers IDs.
$ sudo docker container stop $(sudo docker container ls -aq)

Once all containers are stopped, you can remove them using the docker container rm command followed by the containers ID list.
$ sudo docker container rm $(sudo docker container ls -aq)

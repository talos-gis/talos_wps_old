docker build -t talos_wps .

docker run \
  -d \
  -it \
  -p 80:5000 \
  --name talos_wps_test \
  --env WORKDIR=/app \
  --mount type=bind,source=/home/idan/maps,target=/app/static/data,readonly \
  talos_wps
    
docker exec -it talos_wps_test bash

docker ps -all

To stop all running containers use the docker container stop command followed by a list of all containers IDs.
$ docker container stop $(docker container ls -aq)

Once all containers are stopped, you can remove them using the docker container rm command followed by the containers ID list.
$ docker container rm $(docker container ls -aq)

docker container stop $(docker container ls -aq) && docker container rm $(docker container ls -aq) 

docker system prune

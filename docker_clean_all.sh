#!/bin/bash

# This script removes all docker containers and images

docker ps | awk '{print $1}' | xargs -I{} docker stop {}
docker ps -a | awk '{print $1}' | xargs -I{} docker rm {}
docker images | awk '{print $3}' | xargs -I{} docker rmi {}

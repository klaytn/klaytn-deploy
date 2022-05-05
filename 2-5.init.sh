#!/bin/bash
set -e

./deploy cn init &
./deploy pn init &
./deploy en init &
./deploy cnbn init &
./deploy bn init &
./deploy scn init &
./deploy spn init &
./deploy sen init &
wait

./deploy grafana init &
./deploy locust master init &
./deploy locust slave init &
./deploy locustSC master init &
./deploy locustSC slave init &
./deploy graylog init &
wait

rm -rf ./token-manager/data/*

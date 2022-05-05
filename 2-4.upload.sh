#!/bin/bash
set -e

./deploy cn upload &
./deploy pn upload &
./deploy en upload &
./deploy cnbn upload &
./deploy bn upload &
./deploy scn upload &
./deploy spn upload &
./deploy sen upload &
./deploy grafana upload &
./deploy locust master upload &
./deploy locust slave upload &
./deploy locustSC master upload &
./deploy locustSC slave upload &

wait

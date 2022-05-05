#!/bin/bash
set -e

./deploy klaytn prepare &
./deploy grafana prepare &
./deploy locust master prepare &
./deploy locust slave prepare &
./deploy locustSC master prepare &
./deploy locustSC slave prepare &

wait

#!/bin/bash
set -e

./deploy cn create
./deploy pn create
./deploy en create
./deploy cnbn create
./deploy bn create
./deploy scn create
./deploy spn create
./deploy sen create
./deploy grafana create
./deploy locust master create
./deploy locust slave create
./deploy locustSC master create
./deploy locustSC slave create
./deploy graylog create

#!/bin/bash
set -e

./deploy cn startInstances
./deploy pn startInstances
./deploy en startInstances
./deploy cnbn startInstances
./deploy bn startInstances
./deploy scn startInstances
./deploy spn startInstances
./deploy sen startInstances
./deploy grafana startInstances
./deploy locust master startInstances
./deploy locust slave startInstances
./deploy locustSC master startInstances
./deploy locustSC slave startInstances
./deploy graylog startInstances

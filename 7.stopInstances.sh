#!/bin/bash
set -e

./deploy cn stopInstances
./deploy pn stopInstances
./deploy en stopInstances
./deploy cnbn stopInstances
./deploy bn stopInstances
./deploy scn stopInstances
./deploy spn stopInstances
./deploy sen stopInstances
./deploy grafana stopInstances
./deploy locust master stopInstances
./deploy locust slave stopInstances
./deploy locustSC master stopInstances
./deploy locustSC slave stopInstances
./deploy graylog stopInstances

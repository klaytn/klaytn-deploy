#!/bin/bash
set -e

./deploy cn terminateInstances &
./deploy pn terminateInstances &
./deploy en terminateInstances &
./deploy cnbn terminateInstances &
./deploy bn terminateInstances &
./deploy scn terminateInstances &
./deploy spn terminateInstances &
./deploy sen terminateInstances &
./deploy grafana terminateInstances &
./deploy locust master terminateInstances &
./deploy locust slave terminateInstances &
./deploy locustSC master terminateInstances &
./deploy locustSC slave terminateInstances &
./deploy graylog terminateInstances &

wait

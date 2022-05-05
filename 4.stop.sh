#!/bin/bash
set -e

if [ "$FORCE" == "1" ]; then
  ./deploy cn stop -f
  ./deploy pn stop -f
  ./deploy en stop -f
  ./deploy cnbn stop -f
  ./deploy bn stop -f
  ./deploy scn stop -f
  ./deploy spn stop -f
  ./deploy sen stop -f
else
  ./deploy cn stop
  ./deploy pn stop
  ./deploy en stop
  ./deploy cnbn stop
  ./deploy bn stop
  ./deploy scn stop
  ./deploy spn stop
  ./deploy sen stop
fi

./deploy grafana stop
./deploy locust master stop
./deploy locust slave stop
./deploy locustSC master stop
./deploy locustSC slave stop

#!/bin/bash
set -e

./deploy locust master start
./deploy locustSC master start
./deploy cnbn start
./deploy bn start
./deploy cn start
./deploy pn start
./deploy en start
./deploy scn start
./deploy spn start
./deploy sen start
./deploy grafana start
sleep 3
./deploy locust slave start
./deploy locustSC slave start
./deploy graylog start

./3-1.printBanner.sh
useTokenManager=`jq '.source.tokenManager.useTokenManager' ./conf.json`
if [ "$useTokenManager" = true ]; then
  ./3-2.exec_token_manager.sh
fi

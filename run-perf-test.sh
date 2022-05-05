#!/bin/bash
set -e

./run-perf-test-prepare.sh

./3-1.printBanner.sh

printf "######################################################\n"
printf "#######   Test preparation has been ended.   #########\n"
printf "######################################################\n"

printf "######################################################\n"
printf "####  Wait for a while for nodes to be stabilized ####\n"
printf "######################################################\n"

for (( k=90; k>0; k-- ))
do
    printf "Please wait %d seconds for test nodes to be stabilized.." "$k"
    sleep 1
    printf "\r%b" "\033[2K"
done

NUM_CNS=$(./deploy cn num)
NUM_PNS=$(./deploy pn num)
NUM_ENS=$(./deploy en num)

./run-perf-test-check-connection.sh $NUM_CNS $NUM_PNS $NUM_ENS
if [ $? -ne 0 ]; then
    echo "Failed during checking peer connections of Klaytn nodes"
    exit 1
fi


./deploy locust master start &
sleep 15
./deploy locust slave start
if [ $? -ne 0 ]; then
    echo "Failed to start locust slave, please retry starting the slaves or terminate the test."
    exit 1
fi

./run-perf-test-finalize.sh $NUM_CNS $NUM_PNS $NUM_ENS

#!/bin/bash
#1.create.sh
set -e

./deploy en create
./deploy grafana create
./deploy locust master create
./deploy locust slave create
./deploy graylog create

#!/bin/bash
#2-1.build.sh
./deploy klaytn build
./deploy locust build
make -C klaytn all

./deploy klaytn extract &
./deploy locust extract &

#2-2.genesis.sh = skip
#2-3.prepare.sh
echo "start 2-3.prepare.sh"

./deploy klaytn preparecco &
./deploy grafana prepare &
./deploy locust master prepare &
./deploy locust slave prepare &

wait

echo "start 2-4.upload.sh"
#2-4.upload.sh
#copy static.json & genesis.json to en upload directory

./deploy en upload &
./deploy grafana upload &
./deploy locust master upload &
./deploy locust slave upload &

wait

#2-5.init.sh
./deploy en init
./deploy grafana init
./deploy locust master init
./deploy locust slave init
./deploy graylog init

#3.start

./deploy en start
./deploy grafana start
./deploy graylog start

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

./deploy locust master start &
sleep 15
./deploy locust slave start
if [ $? -ne 0 ]; then
    echo "Failed to start locust slave, please retry starting the slaves or terminate the test."
    exit 1
fi


NUM_ENS=$(./deploy en num)
./run-perf-test-finalize.sh 0 0 $NUM_ENS


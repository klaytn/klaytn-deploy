#!/bin/bash

NUM_CNS=$1
NUM_PNS=$2
NUM_ENS=$3

function check_peer_count {
    NODE_TYPE=$1
    NUM_NODES=$2
    MIN_CONNS=$3

    for (( i=0; i<$NUM_NODES; i++ ))
    do
        CONNS=$(($(./deploy $NODE_TYPE jsexec --id $i "net.peerCount")))
        if [ $CONNS -lt $MIN_CONNS ]; then
            echo "$NODE_TYPE$i has only $CONNS connections, but it should have $MIN_CONNS at least!"
            if [ $WAIT_COUNT -lt $MAX_WAIT_COUNT ]; then
                WAIT_COUNT=$((WAIT_COUNT+1))
                printf "Wait $WAIT_SECONDS seconds, this is $WAIT_COUNT time. Connection check starts from $NODE_TYPE"0" again.\n\n"
                sleep $WAIT_SECONDS
                i=-1
                continue
            else
                echo "Already waited $WAIT_COUNT times but it still fails to be stabilized. Terminate performance test"
                exit 1
            fi
        else
            echo "$NODE_TYPE$i has $CONNS connections"
        fi
    done
}

printf "\n"
printf "########################################################\n"
printf "####  Start checking connections of Klaytn nodes..  ####\n"
printf "########################################################\n"

PNS_PER_CN=$(($NUM_CNS/$NUM_PNS))

MIN_CN_CONNS=$(($NUM_CNS-1+$PNS_PER_CN))
MIN_PN_CONNS=2 # this should be refined!
MIN_EN_CONNS=1 # this should be refined!

echo "NumCNs: $NUM_CNS, NumPNs: $NUM_PNS, NumENs: $NUM_ENS, PNs per CN: $PNS_PER_CN"
echo "Min CN Conns: $MIN_CN_CONNS, Min PN Conns: $MIN_PN_CONNS, Min EN Conns: $MIN_EN_CONNS"

WAIT_COUNT=0
MAX_WAIT_COUNT=3
WAIT_SECONDS=10

check_peer_count "cn" $NUM_CNS $MIN_CN_CONNS
check_peer_count "pn" $NUM_PNS $MIN_PN_CONNS
check_peer_count "en" $NUM_ENS $MIN_EN_CONNS


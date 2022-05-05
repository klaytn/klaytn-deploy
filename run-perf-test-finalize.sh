#!/bin/bash
set -e

NUM_CNS=$1
NUM_PNS=$2
NUM_ENS=$3

function check_finalized {
    NODE_TYPE=$1
    NUM_NODES=$2

    for (( i=0; i<$NUM_NODES; i++ ))
    do
        HEAD_BLOCK_NUM=$(($(./deploy $NODE_TYPE jsexec --id $i "klay.blockNumber")))
        HEAD_BLOCK_TXS=$(($(./deploy $NODE_TYPE jsexec --id $i "klay.getBlock($HEAD_BLOCK_NUM)[\"transactions\"].length")))
        PENDING_SIZE=$(($(./deploy $NODE_TYPE jsexec --id $i "Object.keys(txpool.content.pending).length")))
        QUEUED_SIZE=$(($(./deploy $NODE_TYPE jsexec --id $i "Object.keys(txpool.content.queued).length")))
        printf "$NODE_TYPE$i HeadBlockNum: $HEAD_BLOCK_NUM, TxsInHeadBlock: $HEAD_BLOCK_TXS, PendingTxs: $PENDING_SIZE, QueuedTxs: $QUEUED_SIZE \n"
        if [ "$HEAD_BLOCK_TXS" -gt 0 ]; then
            echo "$NODE_TYPE$i's TxsInHeadBlock is non-zero but $HEAD_BLOCK_TXS, test is not finalized."
        elif [ "$PENDING_SIZE" -gt 0 ]; then
            echo "$NODE_TYPE$i's PendingTxs is non-zero but $PENDING_SIZE, test is not finalized."
        elif [ "$PENDING_SIZE" -gt 0 ]; then
            echo "$NODE_TYPE$i's QueuedTxs is non-zero but $QUEUED_SIZE, test is not finalized."
        fi
    done
}

RUNTIME=$(./deploy klaytn runtime)

for (( k=$RUNTIME+60; k>0; k-- ))
do
    printf "Performance test is in-progress, please wait %d seconds (runtime + additional 60s) to be done." "$k"
    sleep 1
    printf "\r%b" "\033[2K"
done

printf "######################################################\n"
printf "#### Starting checking the status of Klaytn nodes ####\n"
printf "######################################################\n"

check_finalized "cn" $NUM_CNS
check_finalized "pn" $NUM_PNS
check_finalized "en" $NUM_ENS

printf "#####################################################\n"
printf "## Starting downloading the logs from Klaytn nodes ##\n"
printf "#####################################################\n"

if [ "$NUM_CNS" -gt 0]; then
    ./deploy cn download klaytn/logs/kcnd.out
if [ "$NUM_PNS" -gt 0]; then
    ./deploy pn download klaytn/logs/kpnd.out
if [ "$NUM_ENS" -gt 0]; then
    ./deploy en download klaytn/logs/kend.out

# TODO - Also need to download Grafana and Prometheus data

CURRENT_TIME=$(date "+%Y-%m%d-%H%M")
RESULT_FILE_DIR=$CURRENT_TIME"-perf-test-logs"
RESULT_FILE_NAME=$RESULT_FILE_DIR".tar.gz"

mkdir $RESULT_FILE_DIR
cp -r upload $RESULT_FILE_DIR"/."
cp conf.json $RESULT_FILE_DIR"/."
tar -zcf $RESULT_FILE_NAME $RESULT_FILE_DIR

printf "##########################################################################\n"
printf "## conf.json and logs are saved at $RESULT_FILE_NAME ##\n"
printf "##########################################################################\n"

UPLOAD_FLAG=$(./deploy grafana upload-perf-test-result)
if [ "$UPLOAD_FLAG" -eq 1 ]; then
    UPLOAD_PATH=$(./deploy grafana upload-perf-test-result-path)
    echo "Uploading the result data is enabled, start uploading the result data. uploadPath=$UPLOAD_PATH$RESULT_FILE_NAME"
    aws s3 cp $RESULT_FILE_NAME $UPLOAD_PATH$RESULT_FILE_NAME
else
    echo "Uploading the result data is disabled, you can find your result file at $RESULT_FILE_NAME"
fi

./deploy grafana show-perf-test-result

TERMINATE_FLAG=$(./deploy klaytn terminate-instances-after-perf-test)
if [ "$TERMINATE_FLAG" -eq 1 ]; then
    printf "###########################################################################\n"
    printf "## Automatic instance termination is enabled, terminate the instances... ##\n"
    printf "###########################################################################\n"
    ./5.terminateInstances.sh
else
    printf "###########################################################################\n"
    printf "## Performance test has ended, but automatic termination is not enabled. ##\n"
    printf "## Please call./5.terminateInstances.sh to terminate instances.          ##\n"
    printf "###########################################################################\n"
fi

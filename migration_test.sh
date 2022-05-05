#!/bin/bash

timeout=120
nodeType="en"
nodeNumber=1

function waitNewBlock() {
    blockNum=`./deploy $nodeType jsexec --id $nodeNumber 'klay.blockNumber'`
    echo "Start to wait greater block than "$blockNum" "

    startTime=`date +%s`
    i=1
    while :
    do
      sleep 1
      sp="/-\|"
      printf "please wait for making block... ${sp:i++%${#sp}:1} \r"
      curBlkNum=`./deploy $nodeType jsexec --id $nodeNumber 'klay.blockNumber'`
      if [ $curBlkNum -gt $blockNum ];
      then
        echo "Found greater block "$curBlkNum" "
        break
      fi
      currentTime=`date +%s`
      runtime=$((currentTime-startTime))
      if [ $runtime -gt $timeout ];
      then
        echo "Timeout!!! block hasn't been made by "$timeout" sec"
        return 0    # exit 1

      fi
    done
    printf "Thanks for your waiting. \n"
    return 1
}


testCnt=0
while :
do
    ((testCnt++))
    echo "TEST CNT # "$testCnt" "
    ./deploy en jsexec "admin.startStateMigration(false)" --id 1
    sleep 500

    waitNewBlock
    res=$?
    if [ $res -eq 0 ];
    then
        echo "Migration timeout!!! block hasn't been made by "$timeout" sec"
        exit 1
    fi

    ./deploy en stop --id 1
    sleep 10
    ./deploy en start --id 1

    sleep 500

    waitNewBlock
    res=$?
    if [ $res -eq 0 ];
    then
        echo "timeout after start!!! block hasn't been made by "$timeout" sec"
        exit 1
    fi
done
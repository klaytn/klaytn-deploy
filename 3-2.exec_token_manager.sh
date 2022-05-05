#/bin/bash

startTime=`date +%s`
timeout=`jq '.source.tokenManager.timeout' ./conf.json`
nodeType=`jq '.source.tokenManager.node.type' ./conf.json`
nodeType=`tr '[:upper:]' '[:lower:]'<<<${nodeType:1:2}`
nodeNumber=`jq '.source.tokenManager.node.number' ./conf.json`

./token-manager/script/checkConfigure.sh

if [ $? -eq 1 ]; then
  echo "please edit your configure for token manager"
  exit 1
fi
 
i=1
sp="/-\|"
while :
do
  printf "please wait for making block... ${sp:i++%${#sp}:1} \r"
  blockNum=`./deploy $nodeType jsexec --id $nodeNumber 'klay.blockNumber'`
  if [ $blockNum -gt 10 ];
  then
    break
  fi
  currentTime=`date +%s`
  runtime=$((currentTime-startTime))
  if [ $runtime -gt $timeout ];
  then
    echo "timeout!!! block hasn't been made by "$timeout" sec"
    echo "cancel token manager script"
    exit 1
  fi
done
printf "Thanks for your waiting. start token manager   \n"

./token-manager/script/exec_token_manager.sh
jq . ./token-manager/data/allAddress.json

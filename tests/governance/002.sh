#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

. $DIR/common.sh

pushd $DIR/../.. &> /dev/null

# Non governing node assuming that the governing node is node 0
id=1

# Setup phase
num=$(./deploy cn jsexec --id $id "klay.getCouncilSize()")
maxidx=`expr $num - 1`
v1=$(jq '.Address' upload/CN${maxidx}/keys/validator)
epoch=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "istanbul.epoch" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
blk=$(./deploy cn jsexec --id $id "klay.blockNumber")
epochIdx=$((blk / epoch))
govmode=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "governance.governancemode" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
# Check if the governancemode is 'ballot'. If it is, change it into 'single'
if [ ${govmode} == "\"ballot\"" ] || [ ${govmode} == "\"none\"" ] ; then
  echo "Current governance mode is '${govmode}', trying to change it to 'single'"
  ./deploy cn jsexec "governance.vote(\"governance.governancemode\",\"single\")"

  wait=`expr ${epoch} \* 2 + 10`
  echo "Waiting ${wait} seconds"
  sleep ${wait}
  echo
  # Check if the governancemode has changed
  govmode=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "governance.governancemode" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
  if [ ${govmode} == "\"single\"" ]; then
    echo "Governancemode has changed successfully"
    echo
  else
    echo "Failed to change the governancemode!!"
    exit 1
  fi
fi

echo "Trying to remove validator ${v1}"
echo "Current epoch = ${epoch}"
echo "Current block number ${blk}"
echo "epoch index ${epochIdx}"

echo "Wait until new epoch is started..."
wait_new_epoch
echo "current block ${blk} epoch idx ${epochIdx}"

# Remove!!
result=$(./deploy cn jsexec --id $id "governance.vote(\"governance.removevalidator\",${v1})")

if [[ $result =~ "Error: You don't have the right to vote" ]]; then
  exit 0
fi

echo "FAILED"
exit 1


#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

. $DIR/common.sh

pushd $DIR/../.. &> /dev/null

echo "Current status"
./deploy cn jsexec "klay.getCommittee()"
./deploy cn jsexec "klay.getCommitteeSize()"

# Setup phase
# Assume that the governing node is node 0
id=0
num=$(./deploy cn jsexec --id $id "klay.getCouncilSize()")
if [ $num -lt 4 ]; then
	echo "This test requires more than 4 nodes"
	exit 1
fi
maxidx=`expr $num - 1`
v1=$(jq '.Address' upload/CN${maxidx}/keys/validator)
epoch=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "istanbul.epoch" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
blk=$(./deploy cn jsexec --id $id "klay.blockNumber")
epochIdx=$((blk / epoch))
govmode=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "governance.governancemode" | awk -F":" '{print $2}' | awk -F"," '{print $1}')

# Check if the governancemode is 'ballot'. If it is, change it into 'single'
if [ ${govmode} == "\"ballot\"" ]; then
  echo "Current governance mode is 'ballot', trying to change it to 'single'"
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
cmd="governance.vote(\"governance.removevalidator\",${v1})"
echo ${cmd}
./deploy cn jsexec --id $id ${cmd}

size=$num
while [ $size -eq $num ]; do
  size=$(./deploy cn jsexec --id $id "klay.getCommitteeSize()")

  curblk=$(./deploy cn jsexec --id $id "klay.blockNumber")
  curEpochIdx=$((curblk / epoch))
  if [ $size -ne $num ] && [ $curEpochIdx -gt $((epochIdx+1)) ]; then
    echo "not updated until epoch is passed. ${curEpochIdx}"
    ./deploy cn jsexec "klay.getCommittee()"
    ./deploy cn jsexec "klay.getCommitteeSize()"
    exit 1
  fi

done

echo "Removed."
./deploy cn jsexec "klay.getCommittee()"
./deploy cn jsexec "klay.getCommitteeSize()"

# validation
committee=`./deploy cn jsexec --id $id "klay.getCommittee()"`
for ((i=0;i<$num;i++));do
  c=`./deploy cn jsexec --id $i "klay.getCommittee()"`
  if [ "$committee" != "$c" ]; then
    echo "Committee list is not the same across nodes!!!"
    ./deploy cn jsexec "klay.getCommittee()"
    ./deploy cn jsexec "klay.getCommitteeSize()"
    exit 1
  fi
done

# Rollback.
wait_new_epoch
echo "Trying to add ${v1} back."
./deploy cn jsexec --id $id "governance.vote(\"governance.addvalidator\",${v1})"

while [ $size -ne $num ]; do
  size=$(./deploy cn jsexec --id $id "klay.getCommitteeSize()")
done

echo "Added back."
./deploy cn jsexec "klay.getCommittee()"
./deploy cn jsexec "klay.getCommitteeSize()"

popd &> /dev/null

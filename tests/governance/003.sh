#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

. $DIR/common.sh

pushd $DIR/../.. &> /dev/null

echo "Current status"
./deploy cn jsexec "klay.getCommittee()"
./deploy cn jsexec "klay.getCommitteeSize()"

# Setup phase
id=0
num=$(./deploy cn jsexec --id $id "klay.getCouncilSize()")
newValidator="0x1111111111111111111111111111111111111111"
if [ $num -lt 3 ]; then
  echo "This test requires more than 3 nodes"
  exit 1
fi
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

# Add!!
./deploy cn jsexec --id $id "governance.vote(\"governance.addvalidator\",\"${newValidator}\")"

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

echo "Added."
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
echo "Trying to remove ${newValidator} back."
./deploy cn jsexec --id $id "governance.vote(\"governance.removevalidator\",\"${newValidator}\")"

while [ $size -ne $num ]; do
  size=$(./deploy cn jsexec --id $id "klay.getCommitteeSize()")
done

echo "Removed back."
./deploy cn jsexec "klay.getCommittee()"
./deploy cn jsexec "klay.getCommitteeSize()"

popd &> /dev/null

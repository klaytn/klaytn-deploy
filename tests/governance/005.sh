#!/bin/bash
# Voting test for ballot governance mode
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

. $DIR/common.sh

pushd $DIR/../.. &> /dev/null

# Setup phase
id=0
num=$(./deploy cn jsexec --id $id "klay.getCouncilSize()")
epoch=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "istanbul.epoch" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
govmode=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "governance.governancemode" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
blk=$(./deploy cn jsexec --id $id "klay.blockNumber")
epochIdx=$((blk / epoch))

# Check if the governancemode is 'single' or 'none', if so change it to 'ballot'
if [ ${govmode} != "\"ballot\"" ]; then
  echo "Current governance mode is not 'ballot', trying to change it"
  ./deploy cn jsexec --id 0 "governance.vote(\"governance.governancemode\",\"ballot\")"
  
  wait=`expr ${epoch} \* 2 + 10`
  echo "Waiting ${wait} seconds"
  sleep ${wait}
  echo
  # Check if the governancemode has changed
  govmode=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "governance.governancemode" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
  if [ ${govmode} == "\"ballot\"" ]; then
    echo "Governancemode has changed successfully"
    echo
  else
    echo "Failed to change the governancemode!!"
    exit 1
  fi
fi

# Get new mintingamount value
newmintingamount=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "reward.mintingamount" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
if [ $newmintingamount == "\"9600000000000000000\"" ]; then 
  newmintingamount="1000000000000000000"
else 
  newmintingamount="9600000000000000000"
fi

# Get new ratio
newratio=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "reward.ratio" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
if [ $newratio == "\"34/54/12\"" ]; then 
  newratio="100/0/0"
else 
  newratio="34/54/12"
fi

# Get new minimumstake
newminimumstake=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "reward.minimumstake" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
if [ $newminimumstake == "\"5000000\"" ]; then 
  newminimumstake="2500000"
else 
  newminimumstake="5000000"
fi

# Get new unitprice
newunitprice=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "governance.unitprice" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
if [ $newunitprice == 25000000000 ]; then 
  newunitprice=10000000000
else 
  newunitprice=25000000000
fi

# Get new committeesize
newcommitteesize=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "istanbul.committeesize" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
if [ $newcommitteesize == 13 ]; then 
  newcommitteesize=31
else 
  newcommitteesize=13
fi

# Get new epoch
newepoch=$epoch
if [ $newepoch == 30 ]; then 
  newepoch=25
else 
  newepoch=30
fi

# Get deferredtxfee
newdeferredtxfee=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "reward.deferredtxfee" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
if [ $newdeferredtxfee == false ]; then 
  newdeferredtxfee=true
else 
  newdeferredtxfee=false
fi

# Get new useginicoeff
newuseginicoeff=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "reward.useginicoeff" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
if [ $newuseginicoeff == false ]; then 
  newuseginicoeff=true
else 
  newuseginicoeff=false
fi

echo "Trying to vote in ballot mode"
echo "Current epoch = ${epoch}"
echo "Current block number ${blk}"
echo "epoch index ${epochIdx}"

echo "Wait until new epoch is started..."
wait_new_epoch
echo "current block ${blk} epoch idx ${epochIdx}"

keys=( reward.ratio reward.minimumstake  )
values=( $newratio $newminimumstake )

total=${#keys[*]}
echo "Total = ${total}"
# vote for string values!! - all have to fail
for (( i=0; i<$total; i++ ))
do
  for (( j=0; j<(( `expr ${num} / 2` )); j++ ))
  do
    cmd="governance.vote(\"${keys[$i]}\",\"${values[$i]}\")"
    echo ${j} ":" ${cmd}
    ./deploy cn jsexec --id ${j} ${cmd}
  done
  ./deploy cn jsexec --id 0 "governance.showTally"
done

ukeys=( governance.unitprice istanbul.committeesize )
uvalues=( $newunitprice $newcommitteesize )

utotal=${#ukeys[*]}
echo "Total = ${utotal}"
# vote for uint/bool values!! - all have to succeeed
for (( i=0; i<$utotal; i++ ))
do
  cmd="governance.vote(\"${ukeys[$i]}\",${uvalues[$i]})"
  echo ${j} ":" ${cmd}
  ./deploy cn jsexec ${cmd}
  ./deploy cn jsexec --id 0 "governance.showTally"
done


waiting=`expr ${epoch} \* 2 + 10`
echo "Waiting ${waiting} seconds"
sleep ${waiting}

# validation for string values
for (( i=0; i<$total; i++ ))
do
  c=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "${keys[$i]}" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
  if [ \"${values[$i]}\" == $c ]; then
    echo "Test failed!!! Want: ${values[$i]}, Have: ${c} have to be different"
    exit 1
  fi
done

# validation for uint/bool values
for (( i=0; i<$utotal; i++ ))
do
  c=$(./deploy cn jsexec --id $id "governance.getParams()" | grep "${ukeys[$i]}" | awk -F":" '{print $2}' | awk -F"," '{print $1}' | sed -e 's/^ *//g' -e 's/ *$//g')
  if [ ${uvalues[${i}]} != ${c} ]; then
    echo "Test failed!!! Want: ${uvalues[$i]}, Have: ${c}"
    exit 1
  fi
done

echo "Test successfully completed!!"
popd &> /dev/null

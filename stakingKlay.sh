#/bin/sh

echo "send klay to Staking contract"
echo "====================================================="
testAddress=`jq '.Address' ./token-manager/data/testAccountInfo.json`
stakingAddress=`jq '.stakingAddress['$1']' token-manager/data/allAddress.json`
./deploy en jsexec --id 0 'personal.sendTransaction({from:'$testAddress',to:'$stakingAddress', value: web3.toPeb('$2', "KLAY")}, "123")'
echo "====================================================="

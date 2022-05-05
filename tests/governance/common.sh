#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

wait_new_epoch() {
	epoch=$(./deploy cn jsexec --id 0 "governance.itemsAt()" | grep "istanbul.epoch" | awk -F":" '{print $2}' | awk -F"," '{print $1}')
	blk=$(./deploy cn jsexec --id 0 "klay.blockNumber")
	epochIdx=$((blk / epoch))
	curEpochIdx=$epochIdx
	while [ $curEpochIdx -eq $epochIdx ]; do
	  curblk=$(./deploy cn jsexec --id 0 "klay.blockNumber")
	  curEpochIdx=$((curblk / epoch))
	done

	blk=$curblk
	epochIdx=$curEpochIdx
}

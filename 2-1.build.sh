#!/bin/bash
set -e

# Build docker container for use in remote VMs
./deploy klaytn build
./deploy locust build
./deploy locustSC build

# Locally build for use in host (e.g. homi)
echo "Building for host"
make -C klaytn all

# Extract binaries for remote VMs from docker container
./deploy klaytn extract &
./deploy locust extract &
./deploy locustSC extract &

useTokenManager=`jq '.source.tokenManager.useTokenManager' ./conf.json`
if [ "$useTokenManager" = true ]; then
  ./clone_token_manager.sh &
fi

useRewardTester=`jq '.source.rewardTester.useRewardTester' ./conf.json`
if [ "useRewardTester" = true ]; then
  ./clone_reward_tester.sh &
fi

wait

#/bin/sh

if [ ! -d "tests/klaytn-reward-tester" ]; then
  cd tests
  git clone git@github.com:klaytn/klaytn-reward-tester.git
  cd klaytn-reward-tester
  ./init_tester
fi 

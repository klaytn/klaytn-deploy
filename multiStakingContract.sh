#/bin/sh

if [ "$#" -ne 1 ]; then
  echo "give an cco number for deploying contract."
  echo "ex) ./multiStakingContract 0"
  exit 1
fi

cd token-manager/script
./additionalStakingContract.sh $1

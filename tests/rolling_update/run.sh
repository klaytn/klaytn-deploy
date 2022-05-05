#!/bin/sh

# HOW TO USE:
# step 1) deploy old version klaytn.
# step 2) update git branch of conf.json to the target version.
# step 3) run.sh <old version> <new version>
#         e.g. ./tests/rolling_update/run.sh v1.0.0 v1.1.0

if [[ -z $1 ]]; then
    echo "Usage: ./rolling-update.sh <old version> <new version>"
    exit 1
fi

if [[ -z $2 ]]; then
    echo "Usage: ./rolling-update.sh <old version> <new version>"
    exit 1
fi

OLD_VERSION=$1
NEW_VERSION=$2

NUM_CNS=$(jq ".deploy.CN.aws.numNodes" conf.json)
NUM_PNS=$(jq ".deploy.PN.aws.numNodes" conf.json)
NUM_ENS=$(jq ".deploy.EN.aws.numNodes" conf.json)

FAILED=

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
. $DIR/common.sh
pushd $DIR/../.. &> /dev/null

# Step 0: check ens are alive
for ((i = 0 ; i < $NUM_ENS ; i++)); do
    CHECK_EN=$(./deploy en jsexec --id $i "CHECK_RUNNING" | grep "CHECK_RUNNING")
    if [[ -z $CHECK_EN ]]; then
        echo "Check if EN$i is running"
        exit 1
    fi
done

# Step 1: build
./2-1.build.sh

# Step 2: Update half ENs
echo "updating ENs.."
NUM_HALF_ENS=$((NUM_ENS/2))
for ((i = 0 ; i < $NUM_HALF_ENS ; i++)); do
    updateBinary "en" $i
done

# Step 3: Update all PNs
echo "updating PNs.."
for ((i = 0 ; i < $NUM_PNS ; i++)); do
    updateBinary "pn" $i
done

# Step 4: Update all CNs
echo "updating CNs.."
for ((i = 0 ; i < $NUM_CNS ; i++)); do
    updateBinary "cn" $i
done

if [[ -z $FAILED ]]; then
    echo "PASS: rolling update test, $1 --> $2"
else
    echo "FAIL: rolling update test, $1 --> $2"
fi

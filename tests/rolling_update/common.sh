#!/bin/sh

function checkAlive() {
    TYPE=$1
    i=$2

    while true; do
        ./deploy $TYPE start --id $i &> /dev/null
        sleep 1
        CHECK_NODE=$(./deploy $TYPE jsexec --id $i "CHECK_RUNNING" | grep "CHECK_RUNNING")
        if [[ $CHECK_NODE ]]; then
            break;
        fi
        echo "        waiting $TYPE$i to alive.."
    done
}

function checkBlockGeneration() {
    TYPE=$1
    i=$2

    BN1=$(./deploy $TYPE jsexec --id $i "klay.blockNumber")
    sleep 1

    while true; do
        BN2=$(./deploy $TYPE jsexec --id $i "klay.blockNumber")
        if [[ $((BN2+0)) -gt $((BN1+0)) ]]; then
            break
        fi
        echo "        waiting block generation of $TYPE$i.."
        sleep 1
    done
}

function updateBinary() {
    TYPE=$1
    i=$2

    NODE_VERSION=$(./deploy $TYPE jsexec --id $i "web3.version.node" | grep "Klaytn")
    NODE_OLD_VERSION=$(./deploy $TYPE jsexec --id $i "web3.version.node" | grep `echo $OLD_VERSION | cut -f 1 -d -`)
    echo "    $TYPE$i old version: $NODE_VERSION"
    if [[ -z $NODE_OLD_VERSION ]]; then
        echo "    error: old version mismatch"
        FAILED=1
    fi

    if [[ $TYPE == "cn" ]]  && [[ $i != 0 ]]; then
        NODE_ADDR=$(./deploy $TYPE jsexec --id $i "governance.nodeAddress")
        while true; do
            # if epoch is small and council is large, vote can be failed. try again.
            ./deploy $TYPE jsexec --id 0 "governance.vote(\"governance.removevalidator\",${NODE_ADDR})"
            COUNCIL=$(./deploy $TYPE jsexec --id $i "klay.getCouncil()" | grep $NODE_ADDR)
            if [[ -z $COUNCIL ]]; then
                break;
            fi
            echo "    checking vote result.."
            sleep 1
        done
    fi

    ./deploy $TYPE stop --id $i &> /dev/null
    ./deploy $TYPE upload --id $i &> /dev/null

    checkAlive $TYPE $i

    if [[ $TYPE == "cn" ]] && [[ $i != 0 ]]; then
        while true; do
            # if epoch is small and council is large, vote can be failed. try again.
            ./deploy $TYPE jsexec --id 0 "governance.vote(\"governance.addvalidator\",${NODE_ADDR})"
            COUNCIL=$(./deploy $TYPE jsexec --id $i "klay.getCouncil()" | grep $NODE_ADDR)
            if [[ -z $COUNCIL ]]; then
                break;
            fi
            echo "    checking vote result.."
            sleep 1
        done
    fi

    NODE_VERSION=$(./deploy $TYPE jsexec --id $i "web3.version.node" | grep "Klaytn")
    NODE_NEW_VERSION=$(./deploy $TYPE jsexec --id $i "web3.version.node" | grep `echo $NEW_VERSION | cut -f 1 -d -`)
    echo "    $TYPE$i new version: $NODE_VERSION"
    if [[ -z $NODE_NEW_VERSION ]]; then
        echo "    error: new version mismatch"
        FAILED=1
    fi

    checkBlockGeneration $TYPE $i
}


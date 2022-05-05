#!/bin/bash
set -e

./2-1.build.sh
./2-2.genesis.sh
./2-3.prepare.sh
./2-4.upload.sh
./2-5.init.sh

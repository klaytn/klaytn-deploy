#!/bin/bash
set -e

# Check a case when klaytn binaries are downloaded from remote
if [ -d klaytn ]; then
  ./deploy klaytn genesis
fi
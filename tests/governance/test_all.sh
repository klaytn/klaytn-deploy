#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
. $DIR/common.sh

TEST_LIST=`ls $DIR/???.sh`
FAILED_TESTS=()

for i in ${TEST_LIST[*]}; do
	echo -e "${GREEN}[TEST START] $i${NC}"
	$i
	if [ $? -ne 0 ]; then
		echo -e "${RED}!!!TEST FAILED!!! $i${NC}"
		FAILED_TESTS+=($i)
	fi
	echo -e "${GREEN}[TEST END] $i${NC}"
done

if [ ${#FAILED_TESTS[@]} -ne 0 ]; then
	echo -e "${RED}Failed tests: ${NC}"
	printf "\t- ${RED}%s${NC}\n" "${FAILED_TESTS[@]}"
fi

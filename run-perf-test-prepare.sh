#!/bin/bash

./1.create.sh
if [ $? -ne 0 ]; then
    echo "Creating instances failed at 9-1.preparePerformanceTest.sh, please terminate any remaining instances.."
    exit 1
fi

./2.prepare.sh
if [ $? -ne 0 ]; then
    echo "Preparation failed at 9-1.preparePerformanceTest.sh, script will run ./docker_clean_all.sh and retry preparation automatically.."
    ./docker_clean_all.sh
    ./2.prepare.sh
    if [ $? -ne 0 ]; then
      echo "Preparation failed again at 9-1.preparePerformanceTest.sh, terminate performance test and deployed instances.."
      ./5.terminateInstances.sh
      exit 1
    fi
fi

./deploy cnbn start && ./deploy bn start &&./deploy cn start && ./deploy pn start && ./deploy en start && ./deploy scn start && ./deploy grafana start &&./deploy locustSC master start && ./deploy locustSC slave start && ./deploy graylog start

if [ $? -ne 0 ]; then
    echo "Failed while starting deployed instances at 9-1.preparePerformanceTest.sh, please retry starting the instances or terminate them."
    exit 1
fi

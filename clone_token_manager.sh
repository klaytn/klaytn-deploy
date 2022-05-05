#/bin/sh

if [ ! -d "token-manager" ]; then
  git clone -b dev-platform-test-tool git@github.com:Krustuniverse-Klaytn-Group/token-manager.git
  mkdir token-manager/data
  cd token-manager/platform
  npm i
  result=`npm list -g baobab-sap | grep empty | wc -l`
  if [ $result -gt 0 ]; then
    npm i -g baobab-sap
  fi
  baobab-sap compile
else
  cd token-manager
  git pull origin platform
fi 

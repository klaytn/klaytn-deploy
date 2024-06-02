[![No Maintenance Intended](http://unmaintained.tech/badge.svg)](http://unmaintained.tech/)

# NO LONGER MAINTAINED

Since the launch of Kaia Blockchain this repository has been parked in favour of the new open-source projects in [Kaia's Github]. Contributors have now moved there continuing with massive open-source contributions to our blockchain ecosystem. A big thank you to everyone who has contributed to this repository. For more information about Klaytn's chain merge with Finschia blockchain please refer to the launching of Kaia blockchain - [kaia.io](http://kaia.io/).

---

# Klaytn-Deploy
A Tool for klaytn node deployment.
* The klaytn node is deployed on AWS EC2 machine.
* This tool provides scripts to build Klaytn private network composed of deployed nodes. Network is monitored using [Grafana](https://grafana.com/).
* In addition, this tool provides [Locust](https://locust.io/) load testing.

## Prerequisite
Since it was written for Linux and MacOS environments, other environments may be different.

Install following programs
* python3, pip3, python3-venv
* docker: [Install Docker Engine](https://docs.docker.com/engine/install) For MacOS, recommended to use docker-desktop. After installation, start docker.
* aws-cli v2: [Install AWS CLI V2](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)

Configure python virtual environment and install dependencies.
```
$ python3 -m venv venv
$ source venv/bin/activate
(venv)$ pip3 install -r requirements.txt
```

Run `aws configure`
For more information, read [Understanding and getting your AWS credentials](https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html).
```
$ aws configure
AWS Access Key ID [None]: [Access key ID provided]
AWS Secret Access Key [None]: [Secret key ID provided]
Default region name [None]: ap-northeast-2
Default output format [None]: json
```

Prepare an aws key-pair
For more information, read [Amazon EC2 key pairs and Linux instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html)
* You can simply make one at aws management console: EC2 > Key pairs > Create key pair
* If you want to deploy instance in multiple regions, you should prepare the same aws key-pair in every region.
* Locate the key-pair at ~/.ssh folder: `mv sample.key.pem ~/.ssh`
* change mod of your file: `chmod 400 ~/.ssh/sample.key.pem`

Disable unknown host check via ssh
```
$ echo 'Host *' >> ~/.ssh/config
$ echo '    StrictHostKeyChecking no' >> ~/.ssh/config
```

## Quick Start
We will deploy a Klaytn network consisting of a total of three nodes: cn1, pn1, and en1.
In addition, locust master/slave node for load test and grafana node for monitoring are also distributed.

copy conf.template.json file to conf.json file
```
cp conf.template.json conf.json
```

Before, you should prepare next aws information
* subnet id: If your organization does not provide the aws subnet, you should make one or use default subnet.
For more information, read [What is Amazon VPC?](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html).
If you want to make your own VPC, Subnet, you may also refer to the VPC,subnet creation part which is located at the below of this document.
* zone: the region where your klaytn nodes will be deployed.
* security group: can be created by clicking `VPC -> Security Group -> Create security group`
  * VPC: configure the VPC
  * Inbound rules
      * essential rule: Type - All traffic, Source type - custom, Source - its security group's id.
      * optional rule: If vpc peer connection exists, you should prepare inbound rules per peer connection. Source - CIDR
  * Outbound rules
      * essential rule: Type - All traffic, Destination type - custom, Source - 0.0.0.0/0
  * Add your local pc's ip at security group's inbound rule for ssh access.

You **should modify** `userInfo` parts.
```
    "userInfo": {
        "keyPath": "$HOME/.ssh/sample.key.pem", ---(1) pem file location
        "NETWORK_ID": 8888,   ---------------------(2) klaytn private network id you want to deploy
        "aws":{
            "tags": {
                "User": "klaytn-test", -------------(3) aws user tag you want to use
                "Project": "klaytn", ---------------(4) aws project tag you want to use
                "Team": "klaytn" -------------------(5) aws project tag you want to use
            },
            "keyName": "sample.key", --------------(6) pem file name
            "subnet": "subnet-0a0a0a0a0a0a0a0a0", -(7) write your aws subnet-id
            "zone": "ap-northeast-2a" -------------(8) aws zone you want to use as a dafault
        }
    }
```

You **should modify** `securityGroup` in every node type. Below is "CN" node type example.
```
    "CN": {
        "aws":{
            "numNodes":1,
            "instanceType":"m5.large",                 --- (1) you can modify instance type. t2.micro is for free tier.
            "imageId": "ami-033a6a056910d1137",        --- (2) we use amazon-linux2 aws public ami
            "securityGroup": ["sg-0a0a0a0a0a0a0a0a0"], --- (3) you should modify security group id
            "storage":{"DeviceName":"/dev/xvda","VolumeSize":8},
            "userName":"ec2-user"
        },
```

Finally, modify `testcases` in locust slave node type like below.
```
    "locustSlave": {
        "testcases":["transferSignedTx"]
    }
```

Run the following scripts in sequence to deploy the klaytn nodes. 

**Make sure that Docker must always be running before running the script.**
```
# Create a klaytn network
$ ./1.create.sh

# Build binaries to be deployed on AWS ec2. It uses docker.
$ ./2-1.build.sh

# Create a test account, genesis.json, nodekey, etc. according to conf.json
$ ./2-2.genesis.sh

# Prepare the files needed for upload. The files are saved at `upload` directory.
$ ./2-3.prepare.sh

# Upload the files in `upload` directory to each EC2 instance.
$ ./2-4.upload.sh

# Get ready to start nodes in each EC2 instances.
# 1) Remove files in `data` and `logs`. 
# 2) Place `nodekey` and `static-nodes.json`. 
# 3) Install dependent libraries if not installed. It will take some time.
# 4) Run node init command with using genesis.json
$ ./2-5.init.sh
```
If `./2-5.init.sh` is completed, you can use the instance to create your own aws amis. 
To make an ami, stop the instances by running `./6.stopInstances.sh`.
Then, go to the aws management console, and create an ami.
* klaytn ami: for cn,pn,en,cnbn,bn,scn,spn,sen
* grafana ami: for grafana
* locust-master ami: for locust master
* locust-slave ami: for locust slave

After the ami creation is done, you can start your instances by running `./7.startInstances.sh`

Run `./3.start.sh` to start the deployed network.
```
# start the whole network
$ ./3.start.sh 
To connect Prometheus: http://14.152.12.11:9090
To connect Grafana: http://12.674.221.88:3000 (admin/admin)
To connect locustMaster: http:/84.293.123.92:8089
```

Click LocustMaster url. You can start the test when 1 users(worker) is up.
For more information, read [locust's web interface](https://docs.locust.io/en/stable/quickstart.html#locust-s-web-interface)
* Put 100 in number of users
* Put 100 in Spawn rate
* click "Start swarming" to start the test.

Click Grafana url. You can monitor the deployed network.
For more information, read [What is Grafana OSS](https://grafana.com/docs/grafana/latest/introduction/oss-details/)

If you want to stop the network, enter `./4.stop.sh`

If you want to terminate instances, enter `./5.terminateInstances.sh`

You can make your own amis.

## How to contribute?
* issue: Please make an issue if there's bug, improvement, docs suggestion, etc.
* contribute: Please make a PR. If the PR is related with an issue, link the issue.

## Details
### 1. Creating your own VPC, Subnet

* Creating VPC
  * VPC can be created simply by clicking `VPC dashboard -> Launch VPC Wizard` button.
  * IPv4 CIDR block: If you want to use multiple region, you should configure the CIDR block. The CIDR blocks must not be duplicated.
    example. seoul: 10.117.0.0/22, singapore: 10.117.8.0/22, tokyo: 10.117.4.0/22
  * Default options would be enough.
* Creating Peering connection (If you use only single region, skip this)
  * you should create a VPC, Subnet, and security group for every region.
  * If you want to deploy in multiple regions. you should set up several peering connection.
  * Peer connection can be created by clicking `VPC -> Peering connections -> Create peering connection`
  * In every region, create peering connection with other regions. For example, if there's seoul/singapore/tokyo region, you should create two peering connections in each region.
  * Requester: your VPC
  * Region: Another region (then, enter the VPC of the selected region)

### 2. conf.json detailed explanation
conf.json key description

| Key | Description |
|-------------|----------|
| `source/klaytn` | Configuration for [klaytn](https://github.com/klaytn/klaytn) |
| `source/locust` | Configuration for [locust](https://github.com/klaytn/klaytn-load-tester) |
| `source/locustSC` | Configuration for locust at service chain |
| `deploy/*/aws/instanceType` | Reference [HW Specification](https://docs.klaytn.com/node/endpoint-node/system-requirements#h-w-specification) |
| `deploy/*/aws/storage` | Measurement of `VolumeSize` is GB. Klaytn network will use up about 50GB for a day. |
| `deploy/*/aws/_subnets` | Check [Subnet ID](https://ap-northeast-2.console.aws.amazon.com/ec2/v2/home?region=ap-northeast-2#Instances:sort=desc:subnetId) for subnet ID of running instances |
| `deploy/*/aws/_securityGroups` | Check [Security Group](https://ap-northeast-2.console.aws.amazon.com/ec2/v2/home?region=ap-northeast-2#SecurityGroups:sort=groupId) |
| `deploy/locustSlave/testcases` | Check [testcases](https://github.com/klaytn/klaytn-load-tester/tree/master/klayslave) |

klaytn node uses the klaytn binary which version is specified at conf.json file.
If you want to use "sample" branch of your forked klaytn repository, put like below.
The klaytn binary will be cross-compiled when executing ./2-1.build.sh.
Similarly, locust and reward-tester can set repo and branch.
```
  "source":{
    "klaytn":{
      "git":{
        "ref":"git@github.com:sample-git-account/klaytn.git", --(1) repo
        "branch":"sample"                                     --(2) branch
      },
```

You can configure `numNodes` of each node type
```
  "CN": {
    "aws":{
      "numNodes":4, ------------------------(1) "CN numNodes 4" means, four CN node will be deployed.
    },
  },
```

You can configure locust slave more specific.
```
  "locustSlave": {
    "enabled":true, 
    ...
    "RPS": 20000, --------------------------(1) RPS means the number of request per second. it will send 20000 requests per second.
    "testcases":[
      // define the test what you want -----(2) we offer various kinds of testcase. however, some tcs are out-dated.
       ],
    "numAccForSignedTx": 1000, -------------(3) total number of test account
    "activeAccPercent": 100, ---------------(4) the percentage of the test account to be activated
    "slavesPerNode":1, ---------------------(5) the number of locust slave per slaveNode
    "_overrideKeys":[]
  },
```

### 3. Shell Script detailed explanation
All python files related to shell scripts are located in plib.
* `1.create.sh`: Create a klaytn network
* `2. prepare.sh`: prepare.sh is a script that executes the following five shell scripts sequencially at once.
* `2-1.build.sh`: Build binaries to be deployed on AWS ec2. It uses docker.
* `2-2.genesis.sh`: Create a test account, genesis.json, nodekey, etc. according to conf.json
* `2-3.prepare.sh`: Prepare the files needed for upload. The files are saved at `upload` directory.
* `2-4.upload.sh`: Upload the files in `upload` directory to each EC2 instance.
* `2-5.init.sh`: Get ready to start nodes in each EC2 instances.
  * Remove files in `data` and `logs`.
  * Place `nodekey` and `static-nodes.json`. 
  * Install dependent libraries if not installed. It will take some time.
  * Run node init command with using genesis.json
* `3.start.sh`, `4.stop.sh`: start/stop the whole network
  * Runs binary files to stop or start for each EC2 instance . (ex. `kend start`, `kcnd stop`, `kpnd stop`)
  * Note: This commands start and stop the process, not the EC2 instance. Even though the nodes are stopped it will be keep charged for storage.
* `5.terminateInstances.sh`: Stops the instances and remove them forever. Use this when you are done running the network.
* `6.startInstances.sh`: Starts the stopped instances. `3. start.sh` should be called to run the networks again.
* `7.stopInstances.sh`: Stops the whole instances for temporary. Only fees for the storage will be charged. (Stopping the instances can save money.) You can start again using `startInstances.sh`.

Next scripts are useful scripts
* Profile a klaytn binary
```
$ ./profile.sh
$ NODE_TYPE=pn NODE_ID=1 HTTP_PORT=6002 DURATION=60 ./profile.sh
```
* Tracing a klaytn binary
```
$ ./trace.sh
$ NODE_TYPE=pn NODE_ID=1 HTTP_PORT=6002 DURATION=60 ./trace.sh
```
* To remove all unused docker images and containers
```
$ ./docker_clean_all.sh
```
* To start klaytn-reward-tester
```
$ // For using klaytn-reward-tester, target node should open rpc namespace of governance, istanbul, klay, personal 
$ vi tests/klaytn-reward-tester/test.conf.json // set ip of target_node which support rpc api
$ ./3-3.start_reward_tester.sh
```
### 4. To run Ethereum tx test with locust

In "conf.json" file, you need to set the `source["locustSlave"]["enabledEthTest"]` with `true` and give test cases like below.
```
"locustSlave": {
  "enabled":true,
  "enabledEthTest": true,
  ...
  "testcases": ["ethereumTxLegacyTC"],
```

And also you need to open `eth` rpc like below.

```
"EN": {
  ...
  "overrideOptions":{
    ...
    "RPC_API":"klay,personal,eth",
```

Now you are ready to test ethereum tx types with locust.

### 5. `./deploy` usage
| example | description |
|-------------|----------|
| `$./deploy cn ssh 0` | To attatch a node |
| `$./deploy cn attach 0` | Attach to the klaytn js console |
| `$./deploy cn download klaytn/bin/kcnd` | Download a file |
| `$./deploy cn log 0` | Cat a log |
| `$./deploy cn taillog 0` | Tail a log |
| `$./deploy show conf` | To show current configuration |
| `$./deploy klaytn topology` | To get network topology |
| `$./deploy cn exec ls klaytn` | To execute a command on a node |
| `$./deploy cn jsexec klay.blockNumber` | Execute a command on klay js console |

### 6. Token-manager
Token-manager cannot be used yet.

Installing libraries for Token-Manager for MacOS. If you want to install nvm, please refer to [nvm github](https://github.com/nvm-sh/nvm).
```
$ brew install jq
$ brew install nvm
$ nvm install v10
$ nvm use v10
```

To execute token-manager script
```
$ ./3-2.exec_token_manager.sh
```

### 7. Configuration

klaytn-deploy provides the following 5 types of config file examples to be used in various cases.

* General Case: A general configuration file for launching a blockchain network. Create a new blockchain with CNs, PNs and ENs.
```
$ cp conf.template.json conf.json
```

* DynamoDB Case: Example network file where en uses DynamoDB instead of levelDB
```
$ cp conf.dynamo.json conf.json
```
* ENs Synchronized to Baobab or Cypress: 
Deploy one or more ENs with specified [Baobab](https://packages.klaytn.net/baobab/chaindata/) or [Cypress](https://packages.klaytn.net/cypress/chaindata/) chaindata(lumberjack).
(Takes time to download a compressed file and unpack it.)
```
$ cp conf.enonly.lumberjack.json conf.json
```

* Using AMIs created With Lumberjack: Example configuration file used when launching EN that syncs from 0 to Cypress or Baobab.
Or deploy one or more ENs using AMIs created with lumberjack. You need the AMI ID to deploy.
(The AMIs have current cypress chaindata. They are created everyday and expired in a week.)
```
$ cp conf.enonly.sync.json conf.json
```

## TroubleShooting
* signal: killed
  * symptom: `> /usr/local/go/pkg/tool/linux_amd64/link: signal: killed`
  * solution
    * In the docker preferences, click the Advanced button.
    * Increase the memory size (e.g. 2GB -> 4GB)
* signal: no space left on device
  * symptom: failed to copy files: failed to copy directory: Error processing tar file(exit status 1): mkdir /klaytn/vendor/github.com/docker/docker/hack: no space left on device
  * solution: run ./docker-image-prune.sh

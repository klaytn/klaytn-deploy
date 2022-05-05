#!/usr/bin/env python3

import os
import json
import urllib.request
import sys
from urllib.error import HTTPError
import ssl
import glob
from KlaytnCommon import LoadConfig, ExecuteShell, CanDownloadRelease
from PrepareFiles import PrepareFiles
from pytimeparse.timeparse import timeparse

class KlaytnCmd:
	def __init__(self, parsers):
		parser = parsers.add_parser("klaytn")
		subparsers = parser.add_subparsers(dest="klaytnsubparser")

		p = subparsers.add_parser("build", help="Build klaytn.")
		p.set_defaults(func=self.build)

		p = subparsers.add_parser("extract", help="Extract klaytn binaries from docker image.")
		p.set_defaults(func=self.extract)

		p = subparsers.add_parser("prepare", help="Prepare files to be uploaded to Klaytn nodes into the directory `upload`.")
		p.set_defaults(func=self.prepare)

		p = subparsers.add_parser("preparecco", help="Prepare files to be uploaded to Klaytn nodes into the directory `upload` for CCO onboarding test.")
		p.set_defaults(func=self.preparecco)

		p = subparsers.add_parser("genesis", help="Create a genesis block with static-nodes.json using homi.")
		p.set_defaults(func=self.genesis)

		p = subparsers.add_parser("topology", help="Print network topology of current configuration.")
		p.set_defaults(func=self.topology)

		p = subparsers.add_parser("runtime", help="Running time of automated performance test.")
		p.set_defaults(func=self.runtime)

		p = subparsers.add_parser("scconf", help="Generate deploy_conf.json for service chain deployment/execution")
		p.set_defaults(func=self.scconf)

		p = subparsers.add_parser("terminate-instances-after-perf-test", help="Whether to terminate instances after the performance test.")
		p.set_defaults(func=self.terminateInstancesAfterTest)

	def build(self, args):
		jsonConf = LoadConfig(args.conf)

		ref = jsonConf["source"]["klaytn"]["git"]["ref"]
		branch = jsonConf["source"]["klaytn"]["git"]["branch"]
		if isinstance(branch, list):
			branch = branch[0]

		klaytnDir = "klaytn"
		# if klaytn exists remove it.
		if os.path.exists(klaytnDir):
			ExecuteShell("rm -rf %s" % klaytnDir)

		# git clone klaytn repository
		if os.path.exists(klaytnDir) == False:
			ExecuteShell("git clone %s" % ref)

		build_args = []
		# if data race detection is on, set the environment variable "KLAYTN_RACE_DETECT" = 1
		if jsonConf["source"]["klaytn"]["dataRaceDetection"] == True:
			build_args.append("KLAYTN_RACE_DETECT=1")

		if CanDownloadRelease(ref, branch):
			print("The binary can be downloaded. Skipping the build.")
		else:
			print('The binary cannot be found. Trying building...')

			dockerImageTag = "%s-%s" %(jsonConf["source"]["klaytn"]["dockerImageTag"], jsonConf["userInfo"]["aws"]["userTag"])
			dockerImageTag = dockerImageTag.lower()
			dockerBaseImage = jsonConf["source"]["klaytn"]["dockerBaseImage"]
			build_args.append("DOCKER_BASE_IMAGE=%s" % dockerBaseImage)

			flatten_build_args = ""
			if len(build_args) > 0:
				flatten_build_args = "--build-arg " + " --build-arg ".join(build_args)
			print("using base docker image: ", dockerBaseImage)
			print("docker build %s --no-cache -t %s ." % (flatten_build_args, dockerImageTag))
			ExecuteShell("cd %s && git checkout master && git fetch -f %s %s && git checkout %s && git checkout -B build && docker build %s --no-cache -t %s ." %
					(klaytnDir, ref, branch, branch, flatten_build_args, dockerImageTag))

	def extract(self, args):
		jsonConf = LoadConfig(args.conf)
		binaryPath = jsonConf["source"]["klaytn"]["binaryPath"]
		ref = jsonConf["source"]["klaytn"]["git"]["ref"]
		branch = jsonConf["source"]["klaytn"]["git"]["branch"]

		# if binary exists remove it.
		if os.path.exists(binaryPath):
			ExecuteShell("rm -rf %s" % binaryPath)

		# check if the binary can be downloaded.
		if CanDownloadRelease(ref, branch):
			print("The binary can be downloaded. Download binaries from remote server")
			ExecuteShell("mkdir %s && mkdir %s/bin && mkdir %s/conf" % (binaryPath, binaryPath, binaryPath))
			nodeTypes=["kcn", "kpn", "ken", "kscn", "kspn", "ksen", "kbn", "kgen", "homi"]
			for nodeType in nodeTypes:
				download_url = "http://packages.klaytn.net/klaytn/{0}/{1}-{0}-0-linux-amd64.tar.gz".format(branch.replace("-", "~"), nodeType)
				print("Download", download_url)
				if nodeType != "kgen" and nodeType != "homi":
					ExecuteShell("wget -q -O bin.tar.gz %s && tar -xzf bin.tar.gz && cp %s-linux-amd64/bin/%sd %s/bin" % (download_url, nodeType, nodeType, binaryPath))
					ExecuteShell("cp -r %s-linux-amd64/conf/* %s/conf" % (nodeType, binaryPath))
					if nodeType == "kcn" or nodeType == "kpn" or nodeType == "ken":
						ExecuteShell("cp %s/conf/%sd.conf %s/conf/%sd_baobab.conf" % (binaryPath, nodeType, binaryPath, nodeType))
						if sys.platform == "darwin":
							ExecuteShell("sed -i '' \"s/NETWORK=.*/NETWORK=\"baobab\"/g\" %s/conf/%sd_baobab.conf" % (binaryPath, nodeType))
						else:
							ExecuteShell("sed -i \"s/NETWORK=.*/NETWORK=\"baobab\"/g\" %s/conf/%sd_baobab.conf" % (binaryPath, nodeType))
				ExecuteShell("rm -rf bin.tar.gz && rm -rf %s-linux-amd64" % nodeType)
		else:
			print("The binary cannot be downloaded. Extracting from docker image..")
			dockerImageTag = "%s-%s" %(jsonConf["source"]["klaytn"]["dockerImageTag"], jsonConf["userInfo"]["aws"]["userTag"])
			dockerImageTag = dockerImageTag.lower()
			dockerPkgPath = jsonConf["source"]["klaytn"]["dockerPkgPath"]
			ExecuteShell("mkdir -p $(pwd)/%s" % binaryPath)
			ExecuteShell("docker run --rm -u $(id -u):$(id -g) -v $(pwd)/%s:/tmp1 %s bash -c 'cp -r %s/* /tmp1'" %
				(binaryPath, dockerImageTag, dockerPkgPath))

	def genesis(self, args):
		jsonConf = LoadConfig(args.conf)
		numCNs = jsonConf["deploy"]["CN"]["aws"]["numNodes"]
		numPNs = jsonConf["deploy"]["PN"]["aws"]["numNodes"]
		numENs = jsonConf["deploy"]["EN"]["aws"]["numNodes"]
		numBNs = jsonConf["deploy"]["BN"]["aws"]["numNodes"]
		numCNBNs = jsonConf["deploy"]["CNBN"]["aws"]["numNodes"]
		numSCNs = jsonConf["deploy"]["SCN"]["aws"]["numNodes"]
		numSPNs = jsonConf["deploy"]["SPN"]["aws"]["numNodes"]
		numSENs = jsonConf["deploy"]["SEN"]["aws"]["numNodes"]
		numBridge = jsonConf["deploy"]["ServiceChain"]["bridges"]["num"]

		# numTestAccounts = test key(5) + locust(5) + bridge nodes
		numTestAccounts = 5 + 5 + numBridge

		baobabOptions = "--governance --gov-mode \"single\" --gov-unit-price 25000000000 --reward-mint-amount 96000000 --reward-ratio \"34/54/12\" --reward-deferred-tx --ist-epoch 30 --ist-proposer-policy 2 --deriveShaImpl 2 --ist-subgroup 13 --staking-interval 60 --proposer-interval 30"
		if "homiOption" in jsonConf["source"]["klaytn"]:
			baobabOptions = jsonConf["source"]["klaytn"]["homiOption"]

		if numCNs > 0:
			if "numValidators" in jsonConf["deploy"]["CN"]["aws"]:
				numValidators = jsonConf["deploy"]["CN"]["aws"]["numValidators"]
				if numValidators > numCNs:
					raise Exception("numValidators(%d) cannot be greater than numCNs(%d)!" % (numValidators, numCNs))
				ExecuteShell("rm -rf homi-output-cn")
				ExecuteShell("klaytn/build/bin/homi setup -o homi-output-cn %s --cn-num %d --validators-num %d --test-num %d remote" % (baobabOptions, numCNs, numValidators, numTestAccounts))
			else:
				ExecuteShell("rm -rf homi-output-cn")
				ExecuteShell("klaytn/build/bin/homi setup -o homi-output-cn %s --cn-num %d --test-num %d remote" % (baobabOptions, numCNs, numTestAccounts))

		if numPNs > 0:
			ExecuteShell("klaytn/build/bin/homi setup -o homi-output-pn %s --cn-num %d remote" % (baobabOptions, numPNs))
		if numENs > 0:
			ExecuteShell("klaytn/build/bin/homi setup -o homi-output-en %s --cn-num %d remote" % (baobabOptions, numENs))
		if numSCNs > 0:
			ExecuteShell("rm -rf homi-output-scn")
			ExecuteShell("klaytn/build/bin/homi setup -o homi-output-scn --cn-num %d --test-num %d --servicechain-test remote" % (numSCNs, numTestAccounts))
		if numSPNs > 0:
			ExecuteShell("rm -rf homi-output-spn")
			ExecuteShell("klaytn/build/bin/homi setup -o homi-output-spn --cn-num %d --servicechain-test remote" % (numSPNs))
		if numSENs > 0:
			ExecuteShell("rm -rf homi-output-sen")
			ExecuteShell("klaytn/build/bin/homi setup -o homi-output-sen --cn-num %d --servicechain-test remote" % (numSENs))


	def prepare(self, args):
		PrepareFiles(args.conf).Prepare()

	def preparecco(self, args):
		PrepareFiles(args.conf).PrepareCCOTest()

	def topology(self, args):
		PrepareFiles(args.conf).PrintTopology()

	def runtime(self, args):
		jsonConf = LoadConfig(args.conf)
		print (timeparse(jsonConf["deploy"]["locustMaster"]["performanceTest"]["runTime"]))

	def scconf(self, args):
		jsonConf = LoadConfig(args.conf)
		mainBridge = jsonConf["deploy"]["ServiceChain"]["bridges"]["mainBridge"]
		subBridge = jsonConf["deploy"]["ServiceChain"]["bridges"]["subBridge"]
		num = int(jsonConf["deploy"]["ServiceChain"]["bridges"]["num"])
		numParentNodes = int(jsonConf["deploy"][mainBridge]["aws"]["numNodes"])
		numChildNodes = int(jsonConf["deploy"][subBridge]["aws"]["numNodes"])

		if num > numParentNodes:
			raise Exception("number of bridges(%d) cannot be larger than the number of parent nodes(%d)" % (num, numParentNodes))
		if num > numChildNodes:
			raise Exception("number of bridges(%d) cannot be larger than the number of child nodes(%d)" % (num, numChildNodes))

		with open("upload/CN0/keys/nodekey", 'r') as f:
			parentKey = f.read().strip()
		with open("upload/SCN0/keys/nodekey", 'r') as f:
			childKey = f.read().strip()

		ExecuteShell("mkdir -p service-chain")
		for i in range(0,num):
			parentPath = "upload/%s%d" % (mainBridge, i)
			childPath = "upload/%s%d" % (subBridge, i)

			with open("%s/publicip" % (parentPath), 'r') as f:
				parentIp = f.read().strip()
			with open("%s/publicip" % (childPath), 'r') as f:
				childIp = f.read().strip()

			sp = glob.glob("%s/parent_bridge_account/0x*" % (childPath))[0].split('/')
			parentOperator = sp[len(sp)-1]

			sp = glob.glob("%s/child_bridge_account/0x*" % (childPath))[0].split('/')
			childOperator = sp[len(sp)-1]


			deploy_conf = {
				'parent': {
					'ip':parentIp,
					'url':"http://%s:8551"%(parentIp),
					'key':parentKey,
					'operator':parentOperator,
				},
				'child': {
					'ip':childIp,
					'url':"http://%s:8551"%(childIp),
					'key':childKey,
					'operator':childOperator
				}
			}

			fname = "service-chain/bridge_info_%d.json" %(i)
			with open(fname, 'w') as f:
				print("writing to file %s"%(fname))
				f.write(json.dumps(deploy_conf, indent=2))

	def terminateInstancesAfterTest(self, args):
		jsonConf = LoadConfig(args.conf)
		if jsonConf["deploy"]["locustMaster"]["performanceTest"]["terminateInstancesAfterTest"]:
			print (1)
		else:
			print (0)


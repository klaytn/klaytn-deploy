#!/usr/bin/env python3
from BaobabTopologyGenerator import BaobabTopologyGenerator
from CypressTopologyGenerator import CypressTopologyGenerator
from ServiceChainTopologyGenerator import ServiceChainTopologyGenerator
from KlaytnCommon import ExecuteShell, LoadConfig, GetPrivateIp, GenKNIMap, GetInitAdditional, GetOverridOptions

import pprint
import sys
import json
import os
import re
import validators

class PrepareFiles:
	def __init__(self, jsonConfFilename):
		self.jsonConf = LoadConfig(jsonConfFilename)

		numCNs = self.jsonConf["deploy"]["CN"]["aws"]["numNodes"]
		numPNs = self.jsonConf["deploy"]["PN"]["aws"]["numNodes"]
		numENs = self.jsonConf["deploy"]["EN"]["aws"]["numNodes"]
		numCNBNs = self.jsonConf["deploy"]["CNBN"]["aws"]["numNodes"]
		numBNs = self.jsonConf["deploy"]["BN"]["aws"]["numNodes"]
		numSCNs = self.jsonConf["deploy"]["SCN"]["aws"]["numNodes"]
		numSPNs = self.jsonConf["deploy"]["SPN"]["aws"]["numNodes"]
		numSENs = self.jsonConf["deploy"]["SEN"]["aws"]["numNodes"]

		if self.jsonConf["topology"] == "baobab" and numCNs > 0:
			PNsPerCN = int(numPNs / numCNs)
			PNsPerEN = numPNs
			if numENs != 0:
				PNsPerEN = int(numPNs / numENs)
				if PNsPerEN < 2:
					PNsPerEN = 2

			t = BaobabTopologyGenerator(numCNs, numPNs, numENs, PNsPerCN, PNsPerEN)
			self.jsonConf["topology"] = t.GetTopology()
			#print ("topology is set to baobab: ")
			#pprint.PrettyPrinter().pprint(self.jsonConf["topology"])

		elif self.jsonConf["topology"] == "cypress" and numCNs > 0:
			PNsPerCN = numPNs / numCNs
			PNsPerEN = 2

			t = CypressTopologyGenerator(numCNs, numPNs, numENs, PNsPerCN, PNsPerEN)
			self.jsonConf["topology"] = t.GetTopology()

		if numSCNs > 0:
			t = ServiceChainTopologyGenerator(numSCNs, numSPNs, numSENs, 2)
			self.jsonConf["topology"].update(t.GetTopology())

		mainBridgeNode = self.jsonConf["deploy"]["ServiceChain"]["bridges"]["mainBridge"]
		subBridgeNode = self.jsonConf["deploy"]["ServiceChain"]["bridges"]["subBridge"]

		if self.jsonConf["deploy"][mainBridgeNode]["aws"]["numNodes"] < self.jsonConf["deploy"][subBridgeNode]["aws"]["numNodes"]:
			raise Exception("number of %s should be greater equal than number of %s" % (mainBridgeNode, subBridgeNode))

		self.numCNs = numCNs
		self.numPNs = numPNs
		self.numENs = numENs
		self.numBNs = numBNs
		self.numCNBNs = numCNBNs
		self.numSCNs = numSCNs
		self.numSPNs = numSPNs
		self.numSENs = numSENs
		self.kni = re.compile('(^kni://.*@)(0\.0\.0\.0)(:.*\?discport=)(.*$)')
		self.mainBridgeNode = mainBridgeNode
		self.subBridgeNode = subBridgeNode

		self.chaindata = None
		if "chaindata" in self.jsonConf["source"]["klaytn"]:
			self.chaindata = self.jsonConf["source"]["klaytn"]["chaindata"]

		self.overwriteGenesis = None
		if "overwriteGenesis" in self.jsonConf["source"]["klaytn"]:
			self.overwriteGenesis = self.jsonConf["source"]["klaytn"]["overwriteGenesis"]

	def PrintTopology(self):
		print (json.dumps(self.jsonConf["topology"], indent=4, separators=(',', ': ')))

	def PrepareCCOTest(self):
		print ("start PrepareCCOTest")
		for i in range(0, self.numENs):
			self.prepareUploadForCCOTest("EN", i)

	def Prepare(self):

		if self.numCNs == 0 :
			for i in range(0, self.numENs):
				self.prepareUpload("EN", i, 0)
			return
		# make error if homi-output-cn is not present
		if os.path.exists("homi-output-cn") == False:
			raise Exception("Please execute `./deploy klaytn genesis` first!")

		for i in range(0, self.numCNBNs):
			self.prepareUploadForBootnodes("CNBN", i)

		for i in range(0, self.numBNs):
			self.prepareUploadForBootnodes("BN", i)

		KNIMap = GenKNIMap(self.jsonConf)

		for i in range(0, self.numCNs):
			self.prepareUpload("CN", i, KNIMap)

		for i in range(0, self.numPNs):
			self.prepareUpload("PN", i, KNIMap)

		for i in range(0, self.numENs):
			self.prepareUpload("EN", i, KNIMap)

		for i in range(0, self.numSCNs):
			self.prepareUpload("SCN", i, KNIMap)

		for i in range(0, self.numSPNs):
			self.prepareUpload("SPN", i, KNIMap)

		for i in range(0, self.numSENs):
			self.prepareUpload("SEN", i, KNIMap)

	def replaceOptionsToConf(self, confDir, nodeType, options):
		content = ""
		if nodeType == "CNBN":
			nodeType = "BN"
		confFilename = "%s/k%sd.conf"% (confDir, nodeType.lower())
		with open(confFilename) as f:
			for l in f:
				m = re.search("^(\s*.*\s*)=(.*)", l)
				if m is not None:
					o = m.group(1)
					if o in options:
						l = "%s=%s\n" % (o, options[o])
				content += l
		with open(confFilename, "w") as f:
			f.write(content)

	def overrideOptions(self, confDir, nodeType, nodeIdx, rewardBase, bootnodes):
		#with open("%s/genesis.json"%confDir) as f:
			#genesis = json.load(f)
		#chainId = genesis["config"]["chainId"]

		# override network id specified in userinfo.
		networkId = 10000
		if "NETWORK_ID" in self.jsonConf["userInfo"]:
			networkId = self.jsonConf["userInfo"]["NETWORK_ID"]

		options = GetOverridOptions(self.jsonConf, nodeType, nodeIdx).copy()
		options["REWARDBASE"] = rewardBase

		if "NETWORK_ID" not in options:
			options["NETWORK_ID"] = networkId

		initAdditional = GetInitAdditional(self.jsonConf, nodeType, nodeIdx)

		additional = ""
		if "ADDITIONAL" in options:
			additional = options["ADDITIONAL"]

		additional = additional + " " + initAdditional

		if "NO_DISCOVER" not in options:
			if len(bootnodes) > 0 :
				additional = "%s --bootnodes %s" % (additional, ",".join(bootnodes))
				options["NO_DISCOVER"] = ""
			elif not (self.jsonConf["deploy"]["CN"]["aws"]["numNodes"] == 0 and self.jsonConf["deploy"]["PN"]["aws"]["numNodes"] == 0 and self.jsonConf["deploy"]["EN"]["aws"]["numNodes"] != 0) :
				options["NO_DISCOVER"] = "1"

		options["ADDITIONAL"] = "\"%s\"" % additional

		if "lumberjack" == self.chaindata or self.overwriteGenesis == True:
			options["DATA_DIR"] = "/var/kend/data"

		if self.jsonConf["deploy"]["ServiceChain"]["enabled"] == True:
			if nodeType == self.mainBridgeNode and nodeIdx < self.jsonConf["deploy"]["ServiceChain"]["bridges"]["num"]:
				options["SC_MAIN_BRIDGE"] = 1
				options["RPC_ENABLE"] = 1
				if "RPC_API" not in options:
					options["RPC_API"] = "klay,mainbridge"
				elif "mainbridge" not in options["RPC_API"]:
					options["RPC_API"] += ",mainbridge"
				options["SC_MAIN_BRIDGE_INDEXING"] = self.jsonConf["deploy"]["ServiceChain"]["anchoring"]["SC_MAIN_BRIDGE_INDEXING"]
			elif nodeType == self.subBridgeNode and nodeIdx < self.jsonConf["deploy"]["ServiceChain"]["bridges"]["num"]:
				options["SC_SUB_BRIDGE"] = 1
				options["RPC_ENABLE"] = 1
				if "RPC_API" not in options:
					options["RPC_API"] = "klay,subbridge"
				elif "subbridge" not in options["RPC_API"]:
					options["RPC_API"] += ",subbridge"
				options["SC_ANCHORING"] = self.jsonConf["deploy"]["ServiceChain"]["anchoring"]["SC_ANCHORING"]
				options["SC_ANCHORING_PERIOD"] = self.jsonConf["deploy"]["ServiceChain"]["anchoring"]["SC_ANCHORING_PERIOD"]

			if nodeType in ["SCN", "SPN", "SEN"]:
				with open("./homi-output-cn/scripts/genesis.json") as f:
					genesis = json.load(f)
					options["SC_PARENT_CHAIN_ID"] = genesis["config"]["chainId"]

		self.replaceOptionsToConf(confDir, nodeType, options)

	def getRewardBase(self, validatorFilename):
		with open(validatorFilename) as f:
			validator = json.load(f)
		return validator["Address"]

	def prepareUpload(self, nodeType, nodeIdx, KNIMap):
		nodeName = "%s%d" % (nodeType, nodeIdx)
		targetDir = "upload/%s" % nodeName
		ExecuteShell("mkdir -p %s/data/klay" % targetDir)
		ExecuteShell("mkdir -p %s/keys" % targetDir)
		ExecuteShell("mkdir -p %s/bin" % targetDir)
		ExecuteShell("mkdir -p %s/conf" % targetDir)

		if os.path.exists("homi-output-%s" % (nodeType.lower())) :
			ExecuteShell("cp homi-output-%s/keys/nodekey%d %s/keys/nodekey" % (nodeType.lower(), nodeIdx+1, targetDir))
			ExecuteShell("cp homi-output-%s/keys/validator%d %s/keys/validator" % (nodeType.lower(), nodeIdx+1, targetDir))

		# Do not copy bin. It will be copied from binaryPath directly.
		# ExecuteShell("cp %s/bin/k%s* %s/bin" % (self.jsonConf["source"]["klaytn"]["binaryPath"], nodeType.lower(), targetDir))
		ExecuteShell("cp %s/bin/k%sd %s/bin" % (self.jsonConf["source"]["klaytn"]["binaryPath"], nodeType.lower(), targetDir))

		if self.numCNs == 0 and self.numPNs == 0:
			ExecuteShell("cp %s/conf/k%sd.conf %s/conf" % (self.jsonConf["source"]["klaytn"]["binaryPath"], nodeType.lower(), targetDir))
			self.overrideOptions("%s/conf" % targetDir, nodeType, nodeIdx, "", "")
			return

		# For service chain test
		if nodeType in ["SCN", "SPN", "SEN"]:
			ExecuteShell("rm -rf %s/parent_bridge_account" % targetDir)
			ExecuteShell("rm -rf %s/child_bridge_account" % targetDir)

			ExecuteShell("cp homi-output-scn/scripts/genesis.json %s/conf" % targetDir)

			if nodeType == self.subBridgeNode and nodeIdx < self.jsonConf["deploy"]["ServiceChain"]["bridges"]["num"]:
				keyIdx = nodeIdx + 11  # keyIdx for bridge operator is started from 11. keyIdx under 10 is used by test and locust
				ExecuteShell("mkdir -p %s/parent_bridge_account" % targetDir)
				ExecuteShell("mkdir -p %s/child_bridge_account" % targetDir)
				ExecuteShell("cp -r homi-output-cn/keys_test/keystore%d/* %s/parent_bridge_account/" % (keyIdx, targetDir))
				ExecuteShell("cp -r homi-output-scn/keys_test/keystore%d/* %s/child_bridge_account/" % (keyIdx, targetDir))
		else:
			# if self.jsonConf["source"]["klaytn"]["overrideGenesisJson"] exists, use that.
			if "overrideGenesisJson" in self.jsonConf["source"]["klaytn"]:
				path = self.jsonConf["source"]["klaytn"]["overrideGenesisJson"]
				if validators.url(path):
					ExecuteShell("curl %s -o %s/conf/genesis.json" % (path, targetDir))
				else:
					ExecuteShell("cp %s %s/conf" % (path, targetDir))

			else:
				ExecuteShell("cp homi-output-cn/scripts/genesis.json %s/conf" % targetDir)

		ExecuteShell("cp %s/conf/k%sd.conf %s/conf" % (self.jsonConf["source"]["klaytn"]["binaryPath"], nodeType.lower(), targetDir))

		rewardBase = self.getRewardBase("%s/keys/validator" % (targetDir))

		bootnodes = []
		if nodeType == "CN":
			if self.jsonConf["deploy"]["CNBN"]["enabled"] == False:
				# Generate static-nodes.json only if CNBN is not enabled.
				static = self.genStaticNodes(nodeName, KNIMap)
				with open("%s/conf/static-nodes.json" % targetDir, "w") as f:
					json.dump(static, f)
			else:
				# Prepare bootnodes.lst file
				for i in range(0, self.numCNBNs):
					filename = "upload/CNBN%d/keys/node_info.json" % (i)
					with open(filename) as f:
						v = json.load(f)
					bootnodes.append(v["NodeInfo"])
				with open("%s/conf/bootnodes.lst"%targetDir, "w") as f:
					f.write(",".join(bootnodes))

		elif nodeType == "PN":
			# PN needs static-nodes.json always.
			static = self.genStaticNodes(nodeName, KNIMap)
			with open("%s/conf/static-nodes.json" % targetDir, "w") as f:
				json.dump(static, f)

			if self.jsonConf["deploy"]["BN"]["enabled"] == True:
				# Prepare bootnodes.lst file
				for i in range(0, self.numCNBNs):
					filename = "upload/BN%d/keys/node_info.json" % (i)
					with open(filename) as f:
						v = json.load(f)
					bootnodes.append(v["NodeInfo"])
				with open("%s/conf/bootnodes.lst"%targetDir, "w") as f:
					f.write(",".join(bootnodes))

		elif nodeType == "EN":
			if self.jsonConf["deploy"]["BN"]["enabled"] == False:
				# Generate static-nodes.json only if BN is not enabled.
				static = self.genStaticNodes(nodeName, KNIMap)
				with open("%s/conf/static-nodes.json" % targetDir, "w") as f:
					json.dump(static, f)
			else:
				# Prepare bootnodes.lst file
				for i in range(0, self.numCNBNs):
					filename = "upload/BN%d/keys/node_info.json" % (i)
					with open(filename) as f:
						v = json.load(f)
					bootnodes.append(v["NodeInfo"])
				with open("%s/conf/bootnodes.lst"%targetDir, "w") as f:
					f.write(",".join(bootnodes))

		elif nodeType == "SCN":
			nodeName = "%s%d" % ("SCN", nodeIdx)
			targetDir = "upload/%s" % nodeName

			static = self.genStaticNodes(nodeName, KNIMap)
			with open("%s/conf/static-nodes.json" % targetDir, "w") as f:
				json.dump(static, f)

		elif nodeType == "SPN":
			nodeName = "%s%d" % ("SPN", nodeIdx)
			targetDir = "upload/%s" % nodeName

			static = self.genStaticNodes(nodeName, KNIMap)
			with open("%s/conf/static-nodes.json" % targetDir, "w") as f:
				json.dump(static, f)

		elif nodeType == "SEN":
			nodeName = "%s%d" % ("SEN", nodeIdx)
			targetDir = "upload/%s" % nodeName

			static = self.genStaticNodes(nodeName, KNIMap)
			with open("%s/conf/static-nodes.json" % targetDir, "w") as f:
				json.dump(static, f)

		else:
			static = self.genStaticNodes(nodeName, KNIMap)
			with open("%s/conf/static-nodes.json" % targetDir, "w") as f:
				json.dump(static, f)

		if nodeType == self.subBridgeNode and nodeIdx < self.jsonConf["deploy"]["ServiceChain"]["bridges"]["num"]:
			mainBridgeNode = "%s%d" % (self.mainBridgeNode, nodeIdx)
			mainBridgeKNI = KNIMap[mainBridgeNode]
			mainBridgeKNI = mainBridgeKNI.replace(":32323", ":50505")
			with open("%s/conf/main-bridges.json" % targetDir, "w") as f:
				json.dump([mainBridgeKNI], f)

		# Override options based on the conf.json.
		# This also updates bootnodes.
		self.overrideOptions("%s/conf" % targetDir, nodeType, nodeIdx, rewardBase, bootnodes)


	def prepareUploadForCCOTest(self, nodeType, nodeIdx):
		nodeName = "%s%d" % (nodeType, nodeIdx)
		targetDir = "upload/%s" % nodeName
		ExecuteShell("mkdir -p %s/data/klay" % targetDir)
		ExecuteShell("mkdir -p %s/keys" % targetDir)
		ExecuteShell("mkdir -p %s/bin" % targetDir)
		ExecuteShell("mkdir -p %s/conf" % targetDir)

		# Do not copy bin. It will be copied from binaryPath directly.
		# ExecuteShell("cp %s/bin/k%s* %s/bin" % (self.jsonConf["source"]["klaytn"]["binaryPath"], nodeType.lower(), targetDir))
		ExecuteShell("cp %s/bin/k%sd %s/bin" % (self.jsonConf["source"]["klaytn"]["binaryPath"], nodeType.lower(), targetDir))

		# Use self.jsonConf["source"]["klaytn"]["overrideGenesisJson"]
		path = self.jsonConf["source"]["klaytn"]["overrideGenesisJson"]
		if validators.url(path):
			ExecuteShell("curl %s -o %s/conf/genesis.json" % (path, targetDir))
		else:
			ExecuteShell("cp %s %s/conf/genesis.json" % (path, targetDir))

		ExecuteShell("cp %s/conf/k%sd.conf %s/conf" % (self.jsonConf["source"]["klaytn"]["binaryPath"], nodeType.lower(), targetDir))

		#rewardBase = self.getRewardBase("%s/keys/validator" % (targetDir))
		rewardBase=""
		bootnodes = []
		if nodeType != "EN":
			raise Exception("Only EN can be used for CCO stress test!!")
		# check existence of pn-nodes file.
		pnNodesFileName = "cco-onboarding-stress-test-pn-nodes.json"
		if os.path.exists(pnNodesFileName) == False:
			print ("It seems that you don't have %s yet." % (pnNodesFileName))
			sys.exit(1)
		ExecuteShell("cp cco-onboarding-stress-test-pn-nodes.json %s/conf/static-nodes.json" % targetDir)

		# Override options based on the conf.json.
		# This also updates bootnodes.
		self.overrideOptions("%s/conf" % targetDir, nodeType, nodeIdx, rewardBase, bootnodes)

	def prepareUploadForBootnodes(self, nodeType, nodeIdx):
		nodeName = "%s%d" % (nodeType, nodeIdx)
		targetDir = "upload/%s" % nodeName
		ExecuteShell("mkdir -p %s/bin" % targetDir)
		ExecuteShell("mkdir -p %s/conf" % targetDir)
		klaytnBinPath = self.jsonConf["source"]["klaytn"]["binaryPath"]

		ExecuteShell("cp %s/bin/kbnd %s/bin" % (klaytnBinPath, targetDir))
		ExecuteShell("cp %s/conf/kbnd.conf %s/conf" % (klaytnBinPath, targetDir))
		ExecuteShell("cd %s; ../../klaytn/build/bin/kgen --file" % (targetDir))
		filename = "%s/keys/node_info.json" % (targetDir)
		discoveryPort = self.jsonConf["deploy"][nodeType]["discoveryPort"]
		with open(filename) as f:
			v = json.load(f)
		m = self.kni.match(v["NodeInfo"])
		ip = GetPrivateIp("upload/%s%d/privateip"%(nodeType, nodeIdx))
		v["NodeInfo"] = "%s%s%s%s" % (m.group(1), ip, m.group(3), discoveryPort)
		with open(filename, "w") as f:
			json.dump(v, f, indent=4, separators=(',', ': '))
		self.overrideOptions("%s/conf" % targetDir, nodeType, nodeIdx, "", [])

	def prepareUploadBN(self, nodeIdx, KNIMap):
		nodeType = "BN"
		nodeName = "%s%d" % (nodeType, nodeIdx)
		targetDir = "upload/%s" % nodeName
		ExecuteShell("mkdir -p %s/data/klay" % targetDir)
		ExecuteShell("mkdir -p %s/keys" % targetDir)
		ExecuteShell("mkdir -p %s/bin" % targetDir)
		ExecuteShell("mkdir -p %s/conf" % targetDir)

		ExecuteShell("cp homi-output-cn/scripts/genesis.json %s/conf" % targetDir)
		ExecuteShell("cp homi-output-%s/keys/nodekey%d %s/keys/nodekey" % (nodeType.lower(), nodeIdx+1, targetDir))
		ExecuteShell("cp homi-output-%s/keys/validator%d %s/keys/validator" % (nodeType.lower(), nodeIdx+1, targetDir))
		ExecuteShell("cp %s/bin/k%s* %s/bin" % (self.jsonConf["source"]["klaytn"]["binaryPath"], nodeType.lower(), targetDir))

	def genStaticNodes(self, name, KNIMap):
		staticNodes = []
		for n in self.jsonConf["topology"][name]:
			staticNodes.append(KNIMap[n])

		return staticNodes

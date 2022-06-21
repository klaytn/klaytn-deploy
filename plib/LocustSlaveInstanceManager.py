#!/usr/bin/env python3

import sys, os
from AWSInstanceManager import AWSInstanceManager
from KlaytnCommon import ExecuteShell, Colorize, GetOverridOptions

class LocustSlaveInstanceManager(AWSInstanceManager):
	def __init__(self, jsonConf, userInfo):
		nodeType = "locustSlave"
		awsConf = jsonConf["deploy"][nodeType]["aws"]
		AWSInstanceManager.__init__(self, awsConf, nodeType, userInfo)

		self.nodeType = nodeType
		self.jsonConf = jsonConf

		numCNs = self.jsonConf["deploy"]["CN"]["aws"]["numNodes"]

		self.catLogCmdFormat = "cd ~/%s && cat slave-%s.%d.log"
		self.tailLogCmdFormat = "cd ~/%s && tail -f slave-%s.%d.log"

		if self.jsonConf["deploy"]["locustMaster"]["enabled"] == False:
			print ("Since locustMaster is disabled, skipping locust slave...")
			print ("locustSlave cannot be enabled if locustMaster is disabled.")

		if self.jsonConf["deploy"][nodeType]["enabled"] == False:
			print ("Since locustSlave is disabled, skipping locust slave...")
			sys.exit(0)

	def getMasterIp(self):
		with open("upload/locustMaster0/privateip") as f:
			masterIp = f.readline().strip()
		return masterIp

	def Prepare(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		srcDir = self.nodeType
		for i in range(0, len(hosts)):
			self.PrepareById(i)

	def PrepareById(self, nodeIdx):
		self.checkIndex(nodeIdx)
		targetDir = "upload/%s%d" % (self.nodeType, nodeIdx)
		ExecuteShell("mkdir -p %s" % targetDir)

		locustBinaryPath = self.jsonConf["source"]["locust"]["binaryPath"]
		ExecuteShell("cp -r %s/* %s" % (locustBinaryPath, targetDir))

	def Upload(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")
		self.uploadFiles(range(0, len(hosts)), hosts)

	def UploadById(self, index):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		self.uploadFiles([index], hosts)

	def uploadFiles(self, indices, hosts):
		print ("upload to %s" % (self.nodeType))
		remoteDir = "~/%s" % self.nodeType
		self.execute(hosts, "mkdir -p %s" % remoteDir)

		srclist = []
		destlist = []
		for i in range(len(hosts)):
			localDir = "upload/%s%d" % (self.nodeType, i)
			srclist.append("%s/*" % (localDir))
			destlist.append(remoteDir)
		self.uploadList(hosts, srclist, destlist)

	def Init(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")
		# Do nothing.

	def InitById(self, index):
		hosts = self.GetPublicIPAddressesById(index)
		if len(hosts) == 0:
			print ("No hosts available.")
		# Do nothing.

	def Start(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")
		self.startHosts(hosts, 0)

	def StartById(self, index):
		hosts = self.GetPublicIPAddressesById(index)
		if len(hosts) == 0:
			print ("No hosts available.")
		self.startHosts(hosts, index)

	def startHosts(self, hosts, startNodeId):
		numNodes = int(self.jsonConf["deploy"][self.nodeType]["aws"]["numNodes"])
		numSlaves = int(self.jsonConf["deploy"][self.nodeType]["slavesPerNode"])
		eachRps = int(self.jsonConf["deploy"][self.nodeType]["RPS"] / numNodes / numSlaves)
		eachNumAccForSignedTx = int(self.jsonConf["deploy"][self.nodeType]["numAccForSignedTx"] / numNodes / numSlaves)
		activeAccPercent = int(self.jsonConf["deploy"][self.nodeType]["activeAccPercent"])
		chargeKLAY = ""

		endpoints = []
		testServiceChain = False
		for nodeType in self.jsonConf["deploy"][self.nodeType]["endpoints"]:
			if "http://" in nodeType:
				# in this case, the value is an URL, not nodetype.
				endpoints.append(("customIP", nodeType.lstrip("http://")))
			else:
				numNodes = self.jsonConf["deploy"][nodeType]["aws"]["numNodes"]
				port = GetOverridOptions(self.jsonConf, nodeType, 0)["RPC_PORT"]
				for i in range(0, numNodes):
					with open("upload/%s%d/privateip" % (nodeType, i)) as f:
						ip = f.readline().strip()
					endpoints.append((nodeType, "%s:%d" % (ip, port)))
			if nodeType in ["SCN", "SPN", "SEN"]:
				testServiceChain = True

		if "overrideKeys" in self.jsonConf["deploy"][self.nodeType]:
			parentPrivateKeys = self.jsonConf["deploy"][self.nodeType]["overrideKeys"]
		else:
			parentPrivateKeys = self.getTestKeysForLocust("cn")

		if "overrideCharge" in self.jsonConf["deploy"][self.nodeType]:
			chargeKLAY = "-charge " + str(self.jsonConf["deploy"][self.nodeType]["overrideCharge"])

		if testServiceChain:
			childPrivateKeys = self.getTestKeysForLocust("scn")

		masterIp = self.getMasterIp()

		tc = ",".join(self.jsonConf["deploy"][self.nodeType]["testcases"])
		lenHosts = len(hosts)
		for i in range(startNodeId, lenHosts):
			for j in range(0, numSlaves):
				idx = i * numSlaves + j
				if endpoints[idx % len(endpoints)][0] in ["SCN", "SPN", "SEN"]:
					key = childPrivateKeys[idx % len(childPrivateKeys)]
				else:
					key = parentPrivateKeys[idx % len(parentPrivateKeys)]
				endpoint = endpoints[idx % len(endpoints)][1]
				self.execute([hosts[i-startNodeId]], "nohup bash -c \'./%s/bin/klayslave --max-rps %s --vusigned=%s --activepercent=%s --master-host %s --master-port 5557 -key %s -tc=\"%s\" %s -endpoint http://%s > %s/slave-%s.%d.log 2>&1 &\'" % (self.nodeType, eachRps, eachNumAccForSignedTx, activeAccPercent, masterIp, key, tc, chargeKLAY, endpoint, self.nodeType, key, j))

	def Stop(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")
		self.stopHosts(hosts)

	def StopById(self, index):
		hosts = self.GetPublicIPAddressesById(index)
		if len(hosts) == 0:
			print ("No hosts available.")
		self.stopHosts(hosts)

	def Exe(self, cmd):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")
		cmd = " ".join(cmd)
		#prefix_str="\033[0;3%dm[%s%02d]\033[0m" % ((index%6+1), self.nodeType, index)
		self.execute(hosts, cmd)

	def ExeById(self, index, cmd):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		cmd = " ".join(cmd)
		#prefix_str="\033[0;3%dm[%s%02d]\033[0m" % ((index%6+1), self.nodeType, index)
		self.execute(hosts, cmd)

	def stopHosts(self, hosts):
		self.execute(hosts, "killall -2 klayslave")
		self.execute(hosts, "pkill klayslave")

	def CatLogById(self, nodeIdx, slaveIdx):
		self.checkIndex(nodeIdx)
		self.checkSlaveIndex(slaveIdx)
		numSlaves = self.jsonConf["deploy"][self.nodeType]["slavesPerNode"]
		privateKeys = self.getTestKeysForLocust("cn")
		hosts = self.GetPublicIPAddressesById(nodeIdx)
		idx = nodeIdx * numSlaves + slaveIdx
		key = privateKeys[idx % len(privateKeys)]
		self.execute(hosts, self.catLogCmdFormat % (self.nodeType, key, slaveIdx) )

	def TailLogById(self, nodeIdx, slaveIdx):
		self.checkIndex(nodeIdx)
		self.checkSlaveIndex(slaveIdx)
		numSlaves = self.jsonConf["deploy"][self.nodeType]["slavesPerNode"]
		hosts = self.GetPublicIPAddressesById(nodeIdx)
		idx = nodeIdx * numSlaves + slaveIdx
		privateKeys = self.getTestKeysForLocust("cn")
		key = privateKeys[idx % len(privateKeys)]
		self.execute(hosts, self.tailLogCmdFormat % (self.nodeType, key, slaveIdx) )

	def checkSlaveIndex(self, index):
		numSlaves = self.jsonConf["deploy"][self.nodeType]["slavesPerNode"]
		if index < 0 or index >= numSlaves:
			raise Exception("slaveIdx should be in [%d, %d]" % (0, numSlaves-1))

	def getCNPrivateKeys(self):
		numCNs = self.jsonConf["deploy"]["CN"]["aws"]["numNodes"]

		privateKeys = []
		for i in range(0, numCNs):
			with open("upload/CN%d/keys/nodekey" % i) as f:
				k = f.readline().strip()
			privateKeys.append(k)
		return privateKeys

	def getSCNPrivateKeys(self):
		numSCNs = self.jsonConf["deploy"]["SCN"]["aws"]["numNodes"]

		privateKeys = []
		for i in range(0, numSCNs):
			with open("upload/SCN%d/keys/nodekey" % i) as f:
				k = f.readline().strip()
			privateKeys.append(k)
		return privateKeys

	def getTestKeysForLocust(self, node):
		# The private key for locust is in homi-output-[cn|scn]/keys-test/testkey**
		# The number is started from 6. key 1 ~ 5 is for test case
		startKeyIdx = 6
		endKeyIdx = 11

		privateKeys = []
		for i in range(startKeyIdx, endKeyIdx):
			k = self.getTestKey(node, i)
			privateKeys.append(k)
		return privateKeys

	def getTestKey(self, node, index):
		with open("homi-output-%s/keys_test/testkey%d" % (node, index)) as f:
			return f.readline().strip()

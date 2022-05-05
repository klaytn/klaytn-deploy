#!/usr/bin/env python3
import os
import sys
from AWSInstanceManager import AWSInstanceManager
from KlaytnCommon import ExecuteShell, Colorize, GetOverridOptions

class LocustSCSlaveInstanceManager(AWSInstanceManager):
	def __init__(self, jsonConf, userInfo):
		nodeType = "locustSCSlave"
		awsConf = jsonConf["deploy"][nodeType]["aws"]
		AWSInstanceManager.__init__(self, awsConf, nodeType, userInfo)

		self.nodeType = nodeType
		self.jsonConf = jsonConf

		numCNs = self.jsonConf["deploy"]["CN"]["aws"]["numNodes"]

		self.catLogCmdFormat = "cd ~/%s && cat slave-%s.%d.log"
		self.tailLogCmdFormat = "cd ~/%s && tail -f slave-%s.%d.log"

		if self.jsonConf["deploy"]["locustSCMaster"]["enabled"] == False:
			print ("Since locustSCMaster is disabled, skipping locust slaveSC...")
			print ("locustSCSlave cannot be enabled if locustSCMaster is disabled.")

		if self.jsonConf["deploy"][nodeType]["enabled"] == False:
			print ("Since locustSCSlave is disabled, skipping locust slave...")
			sys.exit(0)

	def getMasterSCIp(self):
		with open("upload/locustSCMaster0/privateip") as f:
			masterIp = f.readline().strip()
		return masterIp

	def getENIp(self):
		with open("upload/EN0/privateip") as f:
			ip = f.readline().strip()
		return ip

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

		locustBinaryPath = self.jsonConf["source"]["locustSC"]["binaryPath"]
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
		#eachNumAccForSignedTx = self.jsonConf["deploy"][self.nodeType]["numAccForSignedTx"] / numNodes / numSlaves
		#activeAccPercent = self.jsonConf["deploy"][self.nodeType]["activeAccPercent"]

		mcEndpoints = []
		scEndpoints = []
		for nodeType in self.jsonConf["deploy"][self.nodeType]["endpoints"]:
			numNodes = self.jsonConf["deploy"][nodeType]["aws"]["numNodes"]
			# TODO replace nodeIdx 0 with accureate one
			port = GetOverridOptions(self.jsonConf, nodeType, 0)["RPC_PORT"]
			for i in range(0, numNodes):
				with open("upload/%s%d/privateip" % (nodeType, i)) as f:
					ip = f.readline().strip()
				if nodeType in ["SCN", "SPN", "SEN"]:
					scEndpoints.append("%s:%d" % (ip, port))
				else:
					if "http://" in nodeType:
						# in this case, the value is an URL, not nodetype.
						scEndpoints.append(nodeType.lstrip("http://"))
					else:
						mcEndpoints.append("%s:%d" % (ip, port))

		if len(mcEndpoints) == 0:
			Exception("Parent chain Endpoint for SC locust slave should not be 0")
		if len(scEndpoints) == 0:
			Exception("Child chain Endpoint for SC locust slave should not be 0")

		subBridgeEndpoints = ""
		subBridgeNode = self.jsonConf["deploy"]["ServiceChain"]["bridges"]["subBridge"]
		subBridgeNum = self.jsonConf["deploy"]["ServiceChain"]["bridges"]["num"]
		port = GetOverridOptions(self.jsonConf, "SEN", 0)["RPC_PORT"]
		for i in range(0, subBridgeNum):
			with open("upload/%s%d/privateip" % (subBridgeNode, i)) as f:
				ip = f.readline().strip()
			subBridgeEndpoints += "http://%s:%d" % (ip, port)
			if i != subBridgeNum-1:
				subBridgeEndpoints += ","

		mcKeys = self.getTestKeysForLocustSC("cn")
		scKeys = self.getTestKeysForLocustSC("scn")
		masterIp = self.getMasterSCIp()
		enIp = self.getENIp()

		threshold = self.jsonConf["deploy"]["ServiceChain"]["valueTransfer"]["threshold"]

		tc = ",".join(self.jsonConf["deploy"][self.nodeType]["testcases"])
		lenHosts = len(hosts)
		for i in range(startNodeId, lenHosts):
			for j in range(0, numSlaves):
				idx = i * numSlaves + j
				mcKey = mcKeys[idx % len(mcKeys)]
				scKey = scKeys[idx % len(scKeys)]
				mcEndpoint = mcEndpoints[idx % len(mcEndpoints)]
				scEndpoint = scEndpoints[idx % len(scEndpoints)]
				self.execute([hosts[i-startNodeId]], "nohup bash -c \'./%s/bin/klayslave --max-rps %s --master-host %s --master-port 5557 -threshold %d -mcKey %s -scKey %s -tc=\"%s\" -mcEndpoint http://%s -mcIP %s -scEndpoint http://%s > %s/slave-%s.%d.log 2>&1 -subbridges %s &\'" % (self.nodeType, eachRps, masterIp, threshold, mcKey, scKey, tc, mcEndpoint, enIp, scEndpoint, self.nodeType, mcKey, j, subBridgeEndpoints))

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

	def stopHosts(self, hosts):
		self.execute(hosts, "killall -2 klayslave")
		self.execute(hosts, "pkill klayslave")

	def CatLogById(self, nodeIdx, slaveIdx):
		self.checkIndex(nodeIdx)
		self.checkSlaveIndex(slaveIdx)
		numSlaves = self.jsonConf["deploy"][self.nodeType]["slavesPerNode"]
		privateKeys = self.getCNPrivateKeys()
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
		privateKeys = self.getCNPrivateKeys()
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
		numCNs = self.jsonConf["deploy"]["SCN"]["aws"]["numNodes"]

		privateKeys = []
		for i in range(0, numCNs):
			with open("upload/SCN%d/keys/nodekey" % i) as f:
				k = f.readline().strip()
			privateKeys.append(k)
		return privateKeys

	def getTestKeysForLocustSC(self, node):
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

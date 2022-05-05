#!/usr/bin/env python3

import sys
from AWSInstanceManager import AWSInstanceManager
from KlaytnCommon import ExecuteShell, Colorize

class LocustSCMasterInstanceManager(AWSInstanceManager):
	def __init__(self, jsonConf, userInfo):
		nodeType = "locustSCMaster"
		awsConf = jsonConf["deploy"][nodeType]["aws"]
		AWSInstanceManager.__init__(self, awsConf, nodeType, userInfo)

		self.nodeType = nodeType
		self.jsonConf = jsonConf

		if self.jsonConf["deploy"][nodeType]["enabled"] == False:
			print ("Since locustSCMaster is disabled, skipping locust master...")
			sys.exit(0)

	def Prepare(self):
		targetDir = "upload/%s0" % self.nodeType
		ExecuteShell("mkdir -p %s" % targetDir)

		locustBinaryPath = self.jsonConf["source"]["locustSC"]["binaryPath"]
		ExecuteShell("cp -r %s/* %s" % (locustBinaryPath, targetDir))

		ExecuteShell("cp klaytn-load-tester/dist/locustfile.py %s" % targetDir)

	def Upload(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		print ("upload to %s" % (self.nodeType))
		localDir = "upload/%s0" % self.nodeType
		remoteDir = "~/%s" % self.nodeType
		self.execute(hosts, "mkdir -p %s" % remoteDir)
		
		srclist = []
		destlist = []
		srclist.append("%s/*" % (localDir))
		destlist.append(remoteDir)
		self.uploadList(hosts, srclist, destlist)

	def Init(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")
		self.installIfNotExist(hosts, "~/.local/bin/locust --version")


	def Start(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		remoteDir = "~/%s" % self.nodeType
		self.execute(hosts, "nohup bash -c \'~/.local/bin/locust -f %s/locustfile.py --master > %s/master.log 2>&1 &\'" % (remoteDir,remoteDir))

	def Stop(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		remoteDir = "~/%s" % self.nodeType
		self.execute(hosts, "killall -2 locust")
		self.execute(hosts, "pkill locust")

	def PrintUrl(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		print (Colorize("To connect locustSCMaster: http://%s:8089" % (hosts[0]), "green"))

	def CatLog(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		remoteDir = "~/%s" % self.nodeType
		self.execute(hosts, "cd %s && cat master.log" % remoteDir)


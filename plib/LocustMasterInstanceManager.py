#!/usr/bin/env python3

import sys
from AWSInstanceManager import AWSInstanceManager
from KlaytnCommon import ExecuteShell, Colorize

class LocustMasterInstanceManager(AWSInstanceManager):
	def __init__(self, jsonConf, userInfo):
		nodeType = "locustMaster"
		awsConf = jsonConf["deploy"][nodeType]["aws"]
		AWSInstanceManager.__init__(self, awsConf, nodeType, userInfo)

		self.nodeType = nodeType
		self.jsonConf = jsonConf

		if self.jsonConf["deploy"][nodeType]["enabled"] == False:
			print ("Since locustMaster is disabled, skipping locust master...")
			sys.exit(0)

	def Prepare(self):
		targetDir = "upload/%s0" % self.nodeType
		ExecuteShell("mkdir -p %s" % targetDir)

		locustBinaryPath = self.jsonConf["source"]["locust"]["binaryPath"]
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
		additional_params = ""

		if self.jsonConf["deploy"][self.nodeType]["performanceTest"]["noweb"] == True:
			print ("###########################################################")
			print ("## Starting automated locust test with below information ##")
			print ("###########################################################")
			users = self.jsonConf["deploy"][self.nodeType]["performanceTest"]["users"]
			print ("- users: %s" % users)
			hatchRate = self.jsonConf["deploy"][self.nodeType]["performanceTest"]["hatchRate"]
			print ("- hatchRate: %s" % hatchRate)
			runTime = self.jsonConf["deploy"][self.nodeType]["performanceTest"]["runTime"]
			print ("- runTime: %s" % runTime)
			rps = self.jsonConf["deploy"]["locustSlave"]["RPS"]
			print ("- rps: %s" % rps)
			numNodes = self.jsonConf["deploy"]["locustSlave"]["aws"]["numNodes"]
			print ("- numNodes: %s" % numNodes)
			numSlaves = self.jsonConf["deploy"]["locustSlave"]["slavesPerNode"]
			print ("- numSlaves: %s" % numSlaves)

			additional_params = "--no-web --only-summary -c %d -r %d --run-time %s --expect-slaves=%d" % (users,hatchRate,runTime,numNodes * numSlaves)

		self.execute(hosts, "nohup bash -c \'~/.local/bin/locust -f %s/locustfile.py --master %s > %s/master.log 2>&1 &\'" % (remoteDir,additional_params,remoteDir))

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

		print (Colorize("To connect locustMaster: http://%s:8089" % (hosts[0]), "green"))

	def CatLog(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		remoteDir = "~/%s" % self.nodeType
		self.execute(hosts, "cd %s && cat master.log" % remoteDir)

	def TailLog(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print("No hosts available.")
			return

		remoteDir = "~/%s" % self.nodeType
		self.execute(hosts, "cd %s && tail -f master.log" % remoteDir)

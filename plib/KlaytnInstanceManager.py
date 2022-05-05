#!/usr/bin/env python3
import json
import datetime
import re, os
import signal
import subprocess
import urllib.request
from urllib.error import HTTPError
import ssl
from AWSInstanceManager import AWSInstanceManager
from KlaytnCommon import GetPrivateIp, ExecuteShell, EscapeChars, ExecuteShellBackground, GetInitAdditional, GetOverridOptions, CanDownloadRelease

class KlaytnInstanceManager(AWSInstanceManager):
	def __init__(self, jsonConf, nodeType, binname):
		awsConf = jsonConf["deploy"][nodeType]["aws"]
		self.userInfo = jsonConf["userInfo"]
		AWSInstanceManager.__init__(self, awsConf, nodeType, self.userInfo)
		graylogPrivateIP = GetPrivateIp("upload/graylog0/privateip")
		graylogInputPort = jsonConf["deploy"]["graylog"]["inputPort"]
		self.jsonConf = jsonConf
		self.binname = binname
		# TODO replace nodeIdx 0 with accureate one
		self.dataDir= GetOverridOptions(self.jsonConf, self.nodeType, 0)["DATA_DIR"]
		self.logDir = GetOverridOptions(self.jsonConf, self.nodeType, 0)["LOG_DIR"]

		self.chaindata = None
		if "chaindata" in self.jsonConf["source"]["klaytn"]:
			self.chaindata = self.jsonConf["source"]["klaytn"]["chaindata"]
		self.overwriteGenesis = None # if overwriteGenesis is given, replace the dataDir
		if "overwriteGenesis" in self.jsonConf["source"]["klaytn"]:
			self.overwriteGenesis = self.jsonConf["source"]["klaytn"]["overwriteGenesis"]

		if "lumberjack" == self.chaindata or self.overwriteGenesis == True:
			self.dataDir= "/var/kend/data" # the path where the chaindata from lumberjack image is stored

		startVars = []
		if "accessKeyID" in self.userInfo["aws"] :
			startVars.append("AWS_ACCESS_KEY_ID="+self.userInfo["aws"]["accessKeyID"])
		if "secretAccessKey" in self.userInfo["aws"] :
			startVars.append("AWS_SECRET_ACCESS_KEY="+self.userInfo["aws"]["secretAccessKey"])
		startVars = " ".join(startVars)
		self.initCmd1 = "cd ~/klaytn && rm -rf data && rm -rf logs && mkdir -p data/klay && mkdir -p logs && cp keys/nodekey data/klay/nodekey"
		self.initCmd2 = "cd ~/klaytn && if [ -e {0} ]; then cp {0} {1}/;fi".format("conf/static-nodes.json", self.dataDir)
		self.initCmd3 = "if [ -f ~/klaytn/conf/genesis.json ]; then cd ~/klaytn && {0} ./bin/{1} --datadir {2} init %s conf/genesis.json; fi ".format(startVars, self.binname, self.dataDir)
		self.initCmd4 = "sudo sed -i '1i*.* @@%s:%s' /etc/rsyslog.d/50-default.conf" % (graylogPrivateIP, graylogInputPort)
		self.initCmd5 = """sudo sed -i '1,6d' /etc/rsyslog.conf ;sudo sed -i '1imodule(load=\\\"imfile\\\" PollingInterval=\\\"1\\\")' /etc/rsyslog.conf ; sudo sed -i '2iinput(type=\\\"imfile\\\"' /etc/rsyslog.conf ; sudo sed -i '3iFile=\\\"/home/ubuntu/klaytn/logs/%sd.out\\\"' /etc/rsyslog.conf ; sudo sed -i '4iTag=\\\"%s%d\\\"' /etc/rsyslog.conf ; sudo sed -i '5iSeverity=\\\"debug\\\"' /etc/rsyslog.conf ; sudo sed -i '6iFacility=\\\"local0\\\")' /etc/rsyslog.conf"""
		self.initSCNCmd = "sudo mkdir -p {0}/scn && sudo mkdir -p {0}/keystore && sudo mkdir -p {0}/klay && sudo cp ~/klaytn/conf/*.json {0}/ && sudo cp -r ~/klaytn/parent_bridge_account {0}/ && sudo cp -r ~/klaytn/child_bridge_account {0}/ && sudo cp ~/klaytn/keys/*bridgekey {0}/klay/ && sudo cp ~/klaytn/keys/passwd* {0}/scn/ && sudo cp ~/klaytn/keys/UTC-* {0}/keystore/ && sudo chown -R ubuntu:ubuntu ~/klaytn".format(self.dataDir)
		self.initSENCmd = "sudo cp ~/klaytn/conf/*.json {0}/ && sudo cp ~/klaytn/keys/passwd* {0}/sen/ && sudo cp keys/UTC-* {0}/keystore/".format(self.dataDir)
		self.childBridgeCmd = "sudo rm -rf {0}/parent_bridge_account && sudo rm -rf {0}/child_bridge_account && sudo cp -r ~/klaytn/parent_bridge_account {0}/ && sudo cp -r ~/klaytn/child_bridge_account {0}/ && sudo cp ~/klaytn/conf/main-bridges.json {0}/ && sudo chown -R ubuntu:ubuntu ~/klaytn".format(self.dataDir)
		self.removeBridgeKeyCmd = "cd ~/klaytn && rm -rf parent_bridge_account && rm -rf child_bridge_account "
		self.startCmdFormat = "cd ~/klaytn && %s ./bin/%sd start" % (startVars, self.binname)
		self.stopCmd = "cd ~/klaytn && ./bin/%sd stop"
		self.forceStopCmd = "cd ~/klaytn && killall -9 %s"
		self.statusCmd = "cd ~/klaytn && ./bin/%sd status"
		self.catLogCmd = "cd ~/klaytn && cat %s/%sd.out"
		self.attachCmd = "./klaytn/bin/%s attach %s/klay.ipc"
		self.tailLogCmdFormat = "cd ~/klaytn && tail -f %s/%sd.out"
		self.jsExecCmdFormat = "cd ~/klaytn && ./bin/%s --exec '%s' attach %s/klay.ipc"
		self.versionRe = re.compile('Klaytn v[0-9]+.[0-9]+.[0-9]+(-rc.[0-9]+)?\+[0-9a-z]{10}')

	def Upload(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("[%s] No hosts available." % self.nodeType)
			return

		if self.nodeType == self.jsonConf["deploy"]["ServiceChain"]["bridges"]["subBridge"]:
			self.execute(hosts, self.removeBridgeKeyCmd)

		indices = range(0, len(hosts))
		targetIndices = list(indices)
		targetHosts = list(hosts)
		self.uploadFiles(targetIndices, targetHosts)
		self.uploadPropagateBin(range(0,len(targetHosts)), targetHosts)

	def UploadById(self, index):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		if len(hosts) == 0:
			print ("[%s] No hosts available." % self.nodeType)
			return

		if self.nodeType == self.jsonConf["deploy"]["ServiceChain"]["bridges"]["subBridge"]:
			self.execute(hosts, self.removeBridgeKeyCmd)

		indices = [index]
		targetIndices = list(indices)
		targetHosts = list(hosts)
		self.uploadFiles(targetIndices, targetHosts)
		self.uploadPropagateBin([index], targetHosts)


	def Trace(self, duration):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts avaiable.")
			return
		filename = "trace.%s" % (datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
		cmd = ['debug.goTrace("~/%s",%d)' % (filename, duration)]
		print ("Start tracing for %d seconds..." % duration)
		self.JsExec(cmd)
		self.Download(filename)

		print ("To exit, press CTRL+C")
		for i in range(0, len(hosts)):
			filepath = "download/%s%d/%s" % (self.nodeType, i, filename)
			p = ExecuteShellBackground(["go", "tool", "trace", filepath])
		p.wait()

	def TraceById(self, index, duration):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		filename = "trace.%s" % (datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
		cmd = ['debug.goTrace("~/%s",%d)' % (filename, duration)]
		print ("Start tracing for %d seconds..." % duration)
		self.JsExecById(index, cmd)
		self.DownloadById(index, filename)

		print ("To exit, press CTRL+C")
		filepath = "download/%s%d/%s" % (self.nodeType, index, filename)
		p = ExecuteShellBackground(["go", "tool", "trace", filepath])
		p.wait()

	def Profile(self, duration, mem):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts avaiable.")
			return
		filename = "cpuProfile.%s" % (datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

		cmd= []
		if mem:
			print ("Start memory profiling...")
			cmd = ['debug.writeMemProfile("~/%s")' % (filename)]
		else:
			print ("Start CPU profiling for %d seconds..." % duration)
			cmd = ['debug.cpuProfile("~/%s",%d)' % (filename, duration)]

		self.JsExec(cmd)
		self.Download(filename)

		print ("To exit, press CTRL+C")
		for i in range(0, len(hosts)):
			filepath = "download/%s%d/%s" % (self.nodeType, i, filename)
			p = ExecuteShellBackground(["go", "tool", "pprof", "-http", ":", filepath])
		p.wait()

	def ProfileById(self, index, duration, mem):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		filename = "cpuProfile.%s" % (datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

		cmd= []
		if mem:
			print ("Start memory profiling...")
			cmd = ['debug.writeMemProfile("~/%s")' % (filename)]
		else:
			print ("Start CPU profiling for %d seconds..." % duration)
			cmd = ['debug.cpuProfile("~/%s",%d)' % (filename, duration)]

		self.JsExecById(index, cmd)
		self.DownloadById(index, filename)

		print ("To exit, press CTRL+C")
		filepath = "download/%s%d/%s" % (self.nodeType, index, filename)
		p = ExecuteShellBackground(["go", "tool", "pprof", "-http", ":", filepath])
		p.wait()

	def uploadPropagateBin(self, indices, hosts):
		ref = self.jsonConf["source"]["klaytn"]["git"]["ref"]
		branch = self.jsonConf["source"]["klaytn"]["git"]["branch"]

		if isinstance(branch, list):
			for i in indices:
				bi = i if i < len(branch) else -1
				self.uploadPropagateBinCore(ref, branch[bi], [hosts[i]])
		else:
			self.uploadPropagateBinCore(ref, branch, hosts)

	def uploadPropagateBinCore(self, ref, branch, hosts):
		if CanDownloadRelease(ref, branch):
			download_url = "http://packages.klaytn.net/klaytn/{0}/{1}-{0}-0-linux-amd64.tar.gz".format(branch.replace("-", "~"), self.binname)
			print("Downloading binaries from github", download_url)
			self.execute(hosts, "rm -rf ~/klaytn/bin/* && wget -q -O ~/klaytn_bin.tar.gz %s && mkdir -p ~/klaytn_bin && tar -xzf ~/klaytn_bin.tar.gz -C ~/klaytn_bin && cp -r ~/klaytn_bin/**/bin ~/klaytn/" % (
				download_url))
		else:
			print("Uploading binaries from your pc")
			src = "%s/bin/%s" % (self.jsonConf["source"]["klaytn"]["binaryPath"], self.binname)
			dest = "klaytn/bin/%s" % (self.binname)
			self.uploadPropagate(hosts, src, dest)

	def makeSkipList(self, indices, hosts):
		cmd = "cd ~/klaytn; ./bin/%s version" % (self.binname)
		retMap = self.executeWithReturn(hosts, cmd)
		os.system("make -C klaytn all")
		expected = subprocess.check_output("./klaytn/build/bin/%s version" % (self.binname), shell=True).strip()
		# if expected only have version number, add commit id
		if self.versionRe.match(expected) == None:
			commitId = subprocess.check_output("cd klaytn; git rev-parse HEAD", shell=True).strip()
			expected = expected + "+%s" % (commitId[:10])
		retHosts = []
		retIndices = []
		for i in indices:
			if retMap[hosts[i]].startswith(expected) == False:
				retIndices.append(indices[i])
				retHosts.append(hosts[i])
		return retIndices, retHosts

	def uploadFiles(self, indices, hosts):
		self.execute(hosts, "mkdir -p ~/klaytn")
		srclist = []
		destlist = []
		for i in range(0, len(hosts)):
			print ("upload to %s%d" % (self.nodeType, indices[i]))
			srclist.append("upload/%s%d/*" % (self.nodeType, indices[i]))
			destlist.append("~/klaytn")
		self.uploadList(hosts, srclist, destlist)

	def Download(self, filename):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")
		self.downloadFiles(range(0,len(hosts)), hosts, filename)

	def DownloadById(self, index, filename):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		self.downloadFiles([index], hosts, filename)

	def downloadFiles(self, indices, hosts, filename):
		srclist = []
		destlist = []
		for i in range(0, len(hosts)):
			print ("download %s%d/%s to download/%s%d/%s" % (self.nodeType, indices[i], filename, self.nodeType, indices[i], filename))
			srclist.append(filename)
			ExecuteShell("mkdir -p download/%s%d/%s" % (self.nodeType, indices[i], os.path.dirname(filename)))
			destlist.append("download/%s%d/%s" %(self.nodeType, indices[i], filename))
		self.downloadList(hosts, srclist, destlist)

	def InitBlockchain(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")
		self.init(hosts)

	def InitBlockchainById(self, index):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		self.init(hosts)

	def Start(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")
		self.start(hosts)

	def StartById(self, index):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		self.start(hosts)

	def Status(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")
		self.status(hosts)

	def StatusById(self, index):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		self.status(hosts)

	def Stop(self, force):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")
		self.stop(hosts, force)

	def StopById(self, index, force):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		self.stop(hosts, force)

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

	def CatLogById(self, index):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		self.execute(hosts, self.catLogCmd % (self.logDir, self.binname))

	def AttachById(self, index):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		self.executeTty(hosts, self.attachCmd % (self.binname, self.dataDir))

	def TailLogById(self, index):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		#prefix_str="\033[0;3%dm[%s%02d] \033[0m" % ((index%6+1), self.nodeType, index)
		#self.execute(hosts, self.tailLogCmdFormat % (self.binname, prefix_str))
		self.execute(hosts, self.tailLogCmdFormat % (self.logDir, self.binname))

	def JsExec(self, cmd):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")
		cmd = EscapeChars(" ".join(cmd), ['"', "'"])
		self.execute(hosts, self.jsExecCmdFormat % (self.binname, cmd, self.dataDir), False)

	def JsExecById(self, index, cmd):
		self.checkIndex(index)
		hosts = self.GetPublicIPAddressesById(index)
		cmd = EscapeChars(" ".join(cmd), ['"', "'"])
		self.execute(hosts, self.jsExecCmdFormat % (self.binname, cmd, self.dataDir))

	################################################################################
	# Private functions
	################################################################################
	def start(self, hosts):
		self.execute(hosts, self.startCmdFormat)

	def status(self, hosts):
		self.execute(hosts, self.statusCmd % (self.binname))

	def stop(self, hosts, force):
		if force:
			print ("[%s] killing process using killall.." % self.nodeType)
			self.execute(hosts, self.forceStopCmd % (self.binname))
		else:
			self.execute(hosts, self.stopCmd % (self.binname))

	def init(self, hosts):
		if self.chaindata == "lumberjack":
			self.initLumberjack(hosts)
			if self.overwriteGenesis == True:
				self.initNewNetwork(hosts)
		else:
			self.initNewNetwork(hosts)
			if self.chaindata:
				print("[downloading chaindata] This could take some time")
				cmd="if [[ \\\"wget -S --spider %s  2>&1 | grep 'HTTP/1.1 200 OK'\\\" ]]; then wget -O ~/chaindata.tar.gz %s && sudo tar -xzvf ~/chaindata.tar.gz -C ~/klaytn/data; fi" % (self.chaindata, self.chaindata)
				self.execute(hosts, cmd)

		serviceChainConfig = self.jsonConf["deploy"]["ServiceChain"]
		if serviceChainConfig["enabled"] and self.nodeType == serviceChainConfig["bridges"]["subBridge"]:
			bridgeNum = serviceChainConfig["bridges"]["num"]
			self.execute(hosts[:bridgeNum], self.childBridgeCmd)

		if self.jsonConf["deploy"]["graylog"]["enabled"] == True:
			for i in range(0, len(hosts)):
				print ("updating %s%d's rsyslog config..." % (self.nodeType,i))
				singlehost = []
				singlehost.append(hosts.pop(0))
				self.execute(singlehost, self.initCmd4)
				self.execute(singlehost, self.initCmd5 % (self.binname, self.nodeType, i))

	def initLumberjack(self, hosts):
		# stop kend if kend is running
		self.execute(hosts, "sudo systemctl stop kend")

		# mv lumberjack
		self.execute(hosts, "if [ -f /usr/local/bin/lumberjack.py ]; then sudo mv /usr/local/bin/lumberjack.py /usr/local/bin/lumberjack.py.bak; fi")

		# delete except chaindata
		self.execute(hosts, "sudo rm -rf %s/ken" % self.dataDir, self.nodeType) # lumberjack has ken in data dir
		self.execute(hosts, "sudo rm -rf %s/keystore" % self.dataDir)
		self.execute(hosts, "sudo rm -rf %s/klay/LOCK" % self.dataDir)
		self.execute(hosts, "sudo rm -rf %s/klay/nodekey" % self.dataDir)
		self.execute(hosts, "sudo rm -rf %s/klay/nodes" % self.dataDir)
		self.execute(hosts, "sudo rm -rf %s/klay/transactions.rlp" % self.dataDir)
		self.execute(hosts, "sudo rm -rf %s/nohup.out" % self.dataDir)
		self.execute(hosts, "sudo rm -rf %s/static-nodes.json" % self.dataDir)

		self.execute(hosts, self.initCmd2)

		# set data dir (need root permission)
		defaultDataDir = "~/klaytn/data"
		self.execute(hosts, "[ ! -d {0} ] && sudo mkdir -p {0}/klay".format(self.dataDir))
		self.execute(hosts, "[ -d {0} ] && rm -rf {0}".format(defaultDataDir))
		if defaultDataDir == self.dataDir:
			self.execute(hosts, "mkdir -p {0}".format(defaultDataDir))
		else:  # make soft link to "~/klaytn/data"
			self.execute(hosts, "ln -s {1} {0}".format(defaultDataDir, self.dataDir))

		# set log dir
		defaultLogDir = "~/klaytn/logs"
		# delete everything in log dir
		if self.logDir[0] == "~":  # inside userName dir
			self.execute(hosts, "rm -rf {0} && mkdir -p {0}".format(self.logDir))
		else:  # need root permission
			self.execute(hosts, "sudo rm -rf {0} && sudo mkdir -p {0}".format(self.logDir))
		self.execute(hosts, "[ -d {0} ] && rm -rf {0}".format(defaultLogDir))  # delete everything in "~/klaytn/logs"
		if defaultLogDir == self.logDir:
			self.execute(hosts, "mkdir -p {0}".format(defaultLogDir))
		else:  # make soft link to "~/klaytn/logs"
			self.execute(hosts, "ln -s {1} {0}".format(defaultLogDir, self.logDir))

		# in case when data dir and log dir is at root
		self.execute(hosts, "[ -d {0} ] && sudo chmod -R 777 {0}".format(self.dataDir))
		self.execute(hosts, "[ -d {0} ] && sudo chmod -R 777 {0}".format(self.logDir))

		self.execute(hosts, "cp ~/klaytn/keys/nodekey %s/klay/nodekey" % self.dataDir)

	def initNewNetwork(self, hosts):
		self.execute(hosts, self.initCmd1)
		self.execute(hosts, self.initCmd2)
		for i in range(len(hosts)) :
			initAdditional = GetInitAdditional(self.jsonConf, self.nodeType, i)
			self.ssh(hosts[i], self.initCmd3 % initAdditional)

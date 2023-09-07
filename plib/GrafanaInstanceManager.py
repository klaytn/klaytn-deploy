#!/usr/bin/env python3
import os
import yaml
from AWSInstanceManager import AWSInstanceManager
from KlaytnCommon import ExecuteShell, Colorize

class GrafanaInstanceManager(AWSInstanceManager):
	def __init__(self, jsonConf, userInfo):
		nodeType = "grafana"
		awsConf = jsonConf["deploy"][nodeType]["aws"]
		AWSInstanceManager.__init__(self, awsConf, nodeType, userInfo)
		self.initCmd = "mkdir -p ~/%s" % nodeType
		self.prometheusPort = jsonConf["deploy"][nodeType]["prometheusPort"]
		self.jsonConf = jsonConf
		with open("%s/prometheus.yml" % nodeType) as f:
			self.prometheusYmlTemplate=yaml.safe_load(f)

	def Prepare(self):
		cnips, pnips, enips, scnips, spnips, senips = self.gatherIPs()

		targets = []
		hosts = {}
		for i in range(0, len(cnips)):
			hostname = "CN%d" % i
			targets.append("%s:%d" % (hostname, self.prometheusPort))
			hosts[hostname] = cnips[i]

		for i in range(0, len(pnips)):
			hostname = "PN%d" % i
			targets.append("%s:%d" % (hostname, self.prometheusPort))
			hosts[hostname] = pnips[i]

		for i in range(0, len(enips)):
			hostname = "EN%d" % i
			targets.append("%s:%d" % (hostname, self.prometheusPort))
			hosts[hostname] = enips[i]

		for i in range(0, len(scnips)):
			hostname = "SCN%d" % i
			targets.append("%s:%d" % (hostname, self.prometheusPort))
			hosts[hostname] = scnips[i]

		for i in range(0, len(spnips)):
			hostname = "SPN%d" % i
			targets.append("%s:%d" % (hostname, self.prometheusPort))
			hosts[hostname] = spnips[i]

		for i in range(0, len(senips)):
			hostname = "SEN%d" % i
			targets.append("%s:%d" % (hostname, self.prometheusPort))
			hosts[hostname] = senips[i]

		# make directory exists.
		targetDir = "upload/%s0" % self.nodeType
		ExecuteShell("mkdir -p %s" % targetDir)

		# make host file
		with open("%s/hosts" % targetDir, "w") as f:
			for k, v in hosts.items():
				f.write("%s %s\n" % (v, k))

		# make promethus yaml
		self.prometheusYmlTemplate["scrape_configs"][0]["static_configs"][0]["targets"] = targets
		with open("%s/prometheus.yml" % targetDir, "w") as f:
			f.write(yaml.dump(self.prometheusYmlTemplate, default_flow_style=False))

		# copy template files
		srcDir = self.nodeType
		ExecuteShell("cp %s/grafana_klaytn*.json %s" % (srcDir, targetDir))
		ExecuteShell("cp %s/klaytn.yaml %s" % (srcDir, targetDir))
		ExecuteShell("cp %s/klaytn-dashboard.yaml %s" % (srcDir, targetDir))

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

	def Download(self, filename):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")
		self.downloadFiles(range(0,len(hosts)), hosts, filename)

	def downloadFiles(self, indices, hosts, filename):
		srclist = []
		destlist = []
		for i in range(0, len(hosts)):
			print ("download %s%d/%s to download/%s%d/%s" % (self.nodeType, indices[i], filename, self.nodeType, indices[i], filename))
			srclist.append(filename)
			ExecuteShell("mkdir -p download/%s%d/%s" % (self.nodeType, indices[i], os.path.dirname(filename)))
			destlist.append("download/%s%d/%s" %(self.nodeType, indices[i], filename))
		self.downloadList(hosts, srclist, destlist)

	def Init(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		self.execute(hosts, "echo 'export PATH=\\$PATH:/usr/sbin' >> /home/%s/.bashrc" % (self.awsConf["userName"]))
		self.installIfNotExist(hosts, "grafana-server -v")
		self.installIfNotExist(hosts, "prometheus --version")

		remoteDir = "~/%s" % self.nodeType
		remotePromDir = "/etc/prometheus"
		remoteGrafanaDir = "/etc/grafana"
		self.execute(hosts, "mkdir -p %s" % remotePromDir)
		self.execute(hosts, "mkdir -p %s" % remoteGrafanaDir)
		self.execute(hosts, "head -2 /etc/hosts | sudo tee /etc/hosts")
		self.execute(hosts, "cat %s/hosts | sudo tee -a /etc/hosts" % (remoteDir))
		self.execute(hosts, "sudo cp %s/prometheus.yml %s/prometheus.yml" % (remoteDir, remotePromDir))
		self.execute(hosts, "sudo cp %s/klaytn.yaml  %s/provisioning/datasources/" % (remoteDir, remoteGrafanaDir))
		self.execute(hosts, "sudo cp %s/klaytn-dashboard.yaml  %s/provisioning/dashboards/" % (remoteDir, remoteGrafanaDir))
		self.execute(hosts, "sudo cp %s/grafana_klaytn*.json  %s/provisioning/dashboards/" % (remoteDir, remoteGrafanaDir))


	def Start(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		self.execute(hosts, "nohup prometheus --config.file=/etc/prometheus/prometheus.yml > /dev/null 2>&1 &")
		self.execute(hosts, "sudo systemctl start grafana-server")

	def Stop(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		self.execute(hosts, "pkill prometheus")
		self.execute(hosts, "sudo systemctl stop grafana-server")

	def PrintUrl(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		print (Colorize("To connect Prometheus: http://%s:9090" % (hosts[0]), "green"))
		print (Colorize("To connect Grafana: http://%s:3000 (admin/admin)" % (hosts[0]), "green"))

	################################################################################
	# Private functions
	################################################################################
	def gatherIPs(self):
		numCNs = self.jsonConf["deploy"]["CN"]["aws"]["numNodes"]
		numPNs = self.jsonConf["deploy"]["PN"]["aws"]["numNodes"]
		numENs = self.jsonConf["deploy"]["EN"]["aws"]["numNodes"]
		numSCNs = self.jsonConf["deploy"]["SCN"]["aws"]["numNodes"]
		numSPNs = self.jsonConf["deploy"]["SPN"]["aws"]["numNodes"]
		numSENs = self.jsonConf["deploy"]["SEN"]["aws"]["numNodes"]

		cnips = []
		for i in range(0, numCNs):
			filename = "upload/CN%d/privateip" % i
			with open(filename) as f:
				ip = f.readline().strip()
				cnips.append(ip)

		pnips = []
		for i in range(0, numPNs):
			filename = "upload/PN%d/privateip" % i
			with open(filename) as f:
				ip = f.readline().strip()
				pnips.append(ip)

		enips = []
		for i in range(0, numENs):
			filename = "upload/EN%d/privateip" % i
			with open(filename) as f:
				ip = f.readline().strip()
				enips.append(ip)

		scnips = []
		for i in range(0, numSCNs):
			filename = "upload/SCN%d/privateip" % i
			with open(filename) as f:
				ip = f.readline().strip()
				scnips.append(ip)

		spnips = []
		for i in range(0, numSPNs):
			filename = "upload/SPN%d/privateip" % i
			with open(filename) as f:
				ip = f.readline().strip()
				spnips.append(ip)

		senips = []
		for i in range(0, numSENs):
			filename = "upload/SEN%d/privateip" % i
			with open(filename) as f:
				ip = f.readline().strip()
				senips.append(ip)

		return cnips, pnips, enips, scnips, spnips, senips


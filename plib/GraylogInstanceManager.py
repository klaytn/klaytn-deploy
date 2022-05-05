#!/usr/bin/env python3
import os
import sys
import yaml
from AWSInstanceManager import AWSInstanceManager
from KlaytnCommon import ExecuteShell, Colorize

class GraylogInstanceManager(AWSInstanceManager):
	def __init__(self, jsonConf, userInfo):
		nodeType = "graylog"
		awsConf = jsonConf["deploy"][nodeType]["aws"]
		AWSInstanceManager.__init__(self, awsConf, nodeType, userInfo)
		self.jsonConf = jsonConf

		if self.jsonConf["deploy"][nodeType]["enabled"] == False:
			print ("Since graylog is disabled, skipping graylog...")
			sys.exit(0)

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

		self.execute(hosts, "sudo sed -i '3d' /etc/nginx/conf.d/graylog.conf")
		self.execute(hosts, "sudo sed -i '3iserver_name %s;' /etc/nginx/conf.d/graylog.conf" % hosts[0])
		self.execute(hosts, "sudo systemctl restart nginx")
		self.execute(hosts, "sudo systemctl restart graylog-server.service")

	def Start(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		self.execute(hosts, "sudo sed -i '3d' /etc/nginx/conf.d/graylog.conf")
		self.execute(hosts, "sudo sed -i '3iserver_name %s;' /etc/nginx/conf.d/graylog.conf" % hosts[0])
		self.execute(hosts, "sudo systemctl restart nginx")
		ExecuteShell("./deploy cn exec 'sudo systemctl restart rsyslog'")
		ExecuteShell("./deploy pn exec 'sudo systemctl restart rsyslog'")
		ExecuteShell("./deploy en exec 'sudo systemctl restart rsyslog'")
		ExecuteShell("./deploy scn exec 'sudo systemctl restart rsyslog'")


	def Stop(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		self.execute(hosts, "sudo systemctl stop graylog-server.service")

	def PrintUrl(self):
		hosts = self.GetPublicIPAddresses()
		if len(hosts) == 0:
			print ("No hosts available.")

		print (Colorize("To connect Graylog: http://%s/search (admin/admin)" % (hosts[0]), "green"))

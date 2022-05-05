#!/usr/bin/env python3

import sys
from KlaytnInstanceManager import KlaytnInstanceManager

class KlaytnBootnodeManager(KlaytnInstanceManager):
	def __init__(self, jsonConf, nodeType, binname):
		KlaytnInstanceManager.__init__(self, jsonConf, nodeType, binname)

		self.initCmd = "cd ~/klaytn && rm -rf data && rm -rf logs && mkdir -p data && mkdir -p logs"

		if jsonConf["deploy"][nodeType]["enabled"] == False:
			print ("Since boot node (%s) is disabled in the configuration, skipping..." % (nodeType))
			sys.exit(0)

	def init(self, hosts):
		self.execute(hosts, self.initCmd)

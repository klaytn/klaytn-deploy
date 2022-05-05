#!/usr/bin/env python3

import json
import pprint

class CypressTopologyGenerator:
	def __init__(self, numCNs, numPNs, numENs, PNsPerCN, PNsPerEN):
		self.json = {}

		# full mesh for CNs
		cnlist = []
		for i in range(0, numCNs):
			cnlist.append("CN%d"%i)

		for i in range(0, numCNs):
			self.json["CN%d"%i] = cnlist

		# PNsPerCN
		for i in range(0, numPNs):
			self.json["PN%d"%i] = []
			self.json["PN%d"%i].append("CN%d"% ( i / PNsPerCN ))
		# PNsPerPN
		for i in range(0, numPNs):
			if (i % 2) == 0:
				self.json["PN%d"%i].append("PN%d"% ( ( i + numPNs - 1 ) % numPNs ) )
			else:
				self.json["PN%d"%i].append("PN%d"% ( ( i + 1 ) % numPNs ) )

		# PNsPerEN
		for i in range(0, numENs):
			self.json["EN%d"%i] = []
			pnidx = i
			for _ in range(0, PNsPerEN):
				pnidx = (pnidx+numPNs/PNsPerEN) % numPNs
				self.json["EN%d"%i].append("PN%d" % pnidx)

	def Print(self):
		print (self.json)

	def getJson(self):
		return self.json

	def GetTopology(self):
		return self.json


if __name__ == "__main__":
	t = CypressTopologyGenerator(20, 40, 40, 2, 2)
	pprint.PrettyPrinter().pprint(t.getJson())

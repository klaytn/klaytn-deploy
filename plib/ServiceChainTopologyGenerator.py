#!/usr/bin/env python3

import pprint


class ServiceChainTopologyGenerator:
    def __init__(self, numSCNs, numSPNs, numSENs, SPNperSENs):
        self.json = {}

        # all SCN list
        scnlist = ["SCN%d"%i for i in range(numSCNs)]

        # full mesh for SCN
        for i in range(0, numSCNs):
            self.json["SCN%d"%i] = scnlist

        # SPN connection.
        # connect to 1 SCN
        # circle connection for SPN
        for i in range(0, numSPNs):
            self.json["SPN%d" % i] = ["SCN%d" % (i % numSCNs), "SPN%d" % ((i+1) % numSPNs)]

        # SEN connection
        # connect to {SPNperSENs} SPN
        for i in range(0, numSENs):
            self.json["SEN%d" % i] = []
            pnidx = (i * SPNperSENs)
            for j in range(0, SPNperSENs):
                pnidx = (pnidx + 1) % numSPNs
                self.json["SEN%d" % i].append("SPN%d" % pnidx)

    def Print(self):
        print (self.json)

    def getJson(self):
        return self.json

    def GetTopology(self):
        return self.json


if __name__ == "__main__":
    t = ServiceChainTopologyGenerator(4, 4, 6, 2)
    pprint.PrettyPrinter().pprint(t.getJson())

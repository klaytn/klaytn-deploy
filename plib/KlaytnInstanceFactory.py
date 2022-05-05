#!/usr/bin/env python3
import sys
from KlaytnInstanceManager import KlaytnInstanceManager
from KlaytnBootnodeManager import KlaytnBootnodeManager

def KlaytnInstanceFactory(jsonConf, nodeType, binname):
	if nodeType == "BN" or nodeType == "CNBN":
		return KlaytnBootnodeManager(jsonConf, nodeType, binname)
	else:
		return KlaytnInstanceManager(jsonConf, nodeType, binname)


#!/usr/bin/env python3

import json
import os
import pprint
import re
import ssl
import subprocess
import urllib
from urllib.error import HTTPError


def EscapeChars(s, escapelist):
	escaped=""
	for c in s:
		if c in escapelist:
			escaped = escaped + "\\"
		escaped = escaped + c

	return escaped

def ExecuteShell(cmd):
	exitcode = os.system(cmd)
	if exitcode != 0:
		raise Exception("execution failed. exitcode = %s" % exitcode)

def ExecuteShellBackground(cmd):
	return subprocess.Popen(cmd)

def jsonConfigOverride(jsonTemplate, jsonOverride):
	if type(jsonTemplate) is dict:
		for k, v in jsonTemplate.items():
			if k in jsonOverride:
				if (k == "overrideOptions" or k == "initOption") and isinstance(jsonOverride[k], list):
					for optionIndex in range(len(jsonOverride[k])):
						jsonOverride[k][optionIndex] = jsonConfigOverride(jsonTemplate[k], jsonOverride[k][optionIndex])
				else:
					jsonOverride[k] = jsonConfigOverride(jsonTemplate[k], jsonOverride[k])
			else:
				jsonOverride[k] = jsonTemplate[k]

	return jsonOverride

def LoadConfig(jsonConfFilename):
	with open("conf.template.json") as f:
		jsonTemplate = json.load(f)
	with open(jsonConfFilename) as f:
		jsonOverride = json.load(f)

	return jsonConfigOverride(jsonTemplate, jsonOverride)

def Colorize(str, color):
	colorMap = {
		"off": "\033[0m",
		"black": "\033[0;30m",
		"red": "\033[0;31m",
		"green": "\033[0;32m",
		"yellow": "\033[0;33m",
		"blue": "\033[0;34m",
		"purple": "\033[0;35m",
		"cyan": "\033[0;36m",
		"white": "\033[0;37m",
	}

	return "%s%s%s" % (colorMap[color], str, colorMap["off"])

def GetPrivateIp(filename):
	ip = "0.0.0.0"
	if os.path.isfile(filename):
		with open(filename) as f:
			l = f.readline()
			ip = l.strip()

	return ip

def GenKNIMap(jsonConf):
	numCNs = jsonConf["deploy"]["CN"]["aws"]["numNodes"]
	numPNs = jsonConf["deploy"]["PN"]["aws"]["numNodes"]
	numENs = jsonConf["deploy"]["EN"]["aws"]["numNodes"]
	numSCNs = jsonConf["deploy"]["SCN"]["aws"]["numNodes"]
	numSPNs = jsonConf["deploy"]["SPN"]["aws"]["numNodes"]
	numSENs = jsonConf["deploy"]["SEN"]["aws"]["numNodes"]

	with open("homi-output-cn/scripts/static-nodes.json") as f:
		staticNodesCN = json.load(f)
	if numPNs > 0:
		with open("homi-output-pn/scripts/static-nodes.json") as f:
			staticNodesPN = json.load(f)
	if numENs > 0:
		with open("homi-output-en/scripts/static-nodes.json") as f:
			staticNodesEN = json.load(f)
	if numSCNs > 0:
		with open("homi-output-scn/scripts/static-nodes.json") as f:
			staticNodesSCN = json.load(f)
	if numSPNs > 0:
		with open("homi-output-spn/scripts/static-nodes.json") as f:
			staticNodesSPN = json.load(f)
	if numSENs > 0:
		with open("homi-output-sen/scripts/static-nodes.json") as f:
			staticNodesSEN = json.load(f)

	kni = re.compile('(^kni://.*@)(0\.0\.0\.0)(:.*\?discport=)(.*$)')

	KNIMap = {}

	for i in range(0, numCNs):
		nodeDir = "CN%d" % i
		ip = GetPrivateIp("upload/%s/privateip"%nodeDir)
		l = staticNodesCN[i]
		m = kni.match(l)
		KNIMap[nodeDir] = "%s%s%s" % (m.group(1), ip, m.group(3))

	for i in range(0, numPNs):
		nodeDir = "PN%d" % i
		ip = GetPrivateIp("upload/%s/privateip"%nodeDir)
		l = staticNodesPN[i]
		m = kni.match(l)
		KNIMap[nodeDir] = "%s%s%s" % (m.group(1), ip, m.group(3))

	for i in range(0, numENs):
		nodeDir = "EN%d" % i
		ip = GetPrivateIp("upload/%s/privateip"%nodeDir)
		l = staticNodesEN[i]
		m = kni.match(l)
		KNIMap[nodeDir] = "%s%s%s" % (m.group(1), ip, m.group(3))

	for i in range(0, numSCNs):
		kni = re.compile('(^kni://.*@)(0\.0\.0\.0)(:)(.*)(\?discport=)(.*$)')
		nodeDir = "SCN%d" % i
		ip = GetPrivateIp("upload/%s/privateip"%nodeDir)
		l = staticNodesSCN[i]
		m = kni.match(l)
		KNIMap[nodeDir] = "%s%s:%s%s" % (m.group(1), ip, "22323", m.group(5))

	for i in range(0, numSPNs):
		kni = re.compile('(^kni://.*@)(0\.0\.0\.0)(:)(.*)(\?discport=)(.*$)')
		nodeDir = "SPN%d" % i
		ip = GetPrivateIp("upload/%s/privateip"%nodeDir)
		l = staticNodesSPN[i]
		m = kni.match(l)
		KNIMap[nodeDir] = "%s%s:%s%s" % (m.group(1), ip, "32323", m.group(5))

	for i in range(0, numSENs):
		kni = re.compile('(^kni://.*@)(0\.0\.0\.0)(:)(.*)(\?discport=)(.*$)')
		nodeDir = "SEN%d" % i
		ip = GetPrivateIp("upload/%s/privateip"%nodeDir)
		l = staticNodesSEN[i]
		m = kni.match(l)
		KNIMap[nodeDir] = "%s%s:%s%s" % (m.group(1), ip, "32323", m.group(5))

	return KNIMap

def GetInitAdditional(jsonConf, nodeType, nodeIdx) :
	if "initOption" in jsonConf["deploy"][nodeType]:
		initAdditionals = jsonConf["deploy"][nodeType]["initOption"]
		option = ""

		# create dynamoDB table name if not specified in initOption
		isCreated, tableName = GetTableName(jsonConf, nodeType, nodeIdx)
		if isCreated:
			option = "--db.dynamo.tablename " + tableName + " "

		if isinstance(initAdditionals, list):
			# extract initAddional if it is type list
			if nodeIdx >= len(initAdditionals):
				nodeIdx = -1  # last one
			option += initAdditionals[nodeIdx]
		else:
			option += initAdditionals

		return option
	return ""

def GetOverridOptions(jsonConf, nodeType, nodeIdx):
	if "overrideOptions" in jsonConf["deploy"][nodeType]:
		overrideOptions = jsonConf["deploy"][nodeType]["overrideOptions"]
		if isinstance(overrideOptions, list):
			if nodeIdx >= len(overrideOptions):
				nodeIdx = -1 # last one
			return overrideOptions[nodeIdx]
		else:
			return overrideOptions
	return ""


def GetTableName(jsonConf, nodeType, nodeIdx):
	# You should obey S3 bucket naming to run dynamoDB
	# https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-s3-bucket-naming-requirements.html
	if "initOption" in jsonConf["deploy"][nodeType]:
		initOption = jsonConf["deploy"][nodeType]["initOption"]
		# extract initOption if it type list
		if isinstance(initOption, list):
			initOption = initOption[:] # copy before changing
			if nodeIdx >= len(initOption):
				nodeIdx = -1
			initOption = initOption[nodeIdx]
		# get table name if specified
		if "--db.dynamo.tablename" in initOption:
			words = initOption.replace("=", " ").split()
			return False, words[words.index("--db.dynamo.tablename")+1]

	userTag = jsonConf["userInfo"]["aws"]["tags"]["User"]
	return True, userTag.lower().replace("_", "-").replace("/", "-").replace(" ", "-") + "-" + nodeType.lower() + str(nodeIdx)

# check if the binary can be downloaded. url example: https://github.com/klaytn/klaytn/archive/refs/tags/v1.6.1.tar.gz
def CanDownloadRelease(ref, branch):
	if ref == "git@github.com:klaytn/klaytn.git" or ref == "https://github.com/klaytn/klaytn.git":
		try:
			check_url = "https://github.com/klaytn/klaytn/archive/refs/tags/" + branch + ".tar.gz"
			status = urllib.request.urlopen(check_url, context=ssl._create_unverified_context()).getcode()
			if status == 200:
				print("Klaytn release exists at", check_url)
				return True
		except HTTPError as e:
			pass
	print("No github release for", ref, "at", branch)
	return False

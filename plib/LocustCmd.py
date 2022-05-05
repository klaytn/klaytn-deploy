#!/usr/bin/env python3

import os
import platform

from LocustMasterCmd import LocustMasterCmd
from LocustSlaveCmd import LocustSlaveCmd
from KlaytnCommon import LoadConfig, ExecuteShell

class LocustCmd:
	def __init__(self, parsers):
		parser = parsers.add_parser("locust", help="Execute functions related to locust.")
		subparsers = parser.add_subparsers(dest="locust_subparser")

		p = subparsers.add_parser("build", help="Build klaytn-load-tester.")
		p.set_defaults(func=self.build)

		p = subparsers.add_parser("extract", help="Extract binary files from the docker image of klaytn-load-tester.")
		p.set_defaults(func=self.extract)

		LocustMasterCmd(subparsers)
		LocustSlaveCmd(subparsers)

	def isEnabled(self, jsonConf):
		return jsonConf["deploy"]["locustSlave"]["enabled"] == True and jsonConf["deploy"]["locustMaster"]["enabled"] == True

	def build(self, args):
		jsonConf = LoadConfig(args.conf)

		if not self.isEnabled(jsonConf):
			return

		ref = jsonConf["source"]["locust"]["git"]["ref"]
		branch = jsonConf["source"]["locust"]["git"]["branch"]
		dockerImageTag = "%s-%s" % (jsonConf["source"]["locust"]["dockerImageTag"], jsonConf["userInfo"]["aws"]["userTag"])
		dockerImageTag = dockerImageTag.lower()

		locustDir = "klaytn-load-tester"

		if os.path.exists(locustDir):
			ExecuteShell("rm -rf %s" % locustDir)

		if os.path.exists(locustDir) == False:
			ExecuteShell("git clone %s" % ref)

		klaytnDir = "klaytn"
		klaytnRef = jsonConf["source"]["klaytn"]["git"]["ref"]
		klaytnBranch = jsonConf["source"]["klaytn"]["git"]["branch"]

		if os.path.exists("%s/%s" % (locustDir, klaytnDir)) == False:
			ExecuteShell("cd %s && git clone %s" % (locustDir, klaytnRef))
		ExecuteShell("cd %s/%s && git checkout master && git fetch -f %s %s && git checkout %s && git checkout -B build" % (locustDir, klaytnDir, klaytnRef, klaytnBranch, klaytnBranch))
		ExecuteShell("cd %s && git checkout master && git fetch -f %s %s && git checkout %s  && git checkout -B build  && docker build -t %s ." % (locustDir, ref, branch, branch, dockerImageTag))
		
		if jsonConf["deploy"]["locustSlave"]["enabledEthTest"] == True:
			ExecuteShell("cd %s/klayslave && git submodule init && git submodule update && cd ethTxGenerator && env GOOS=linux GOARCH=amd64 go build -v" % (locustDir))

	def extract(self, args):
		jsonConf = LoadConfig(args.conf)

		if not self.isEnabled(jsonConf):
			return

		dockerImageTag = "%s-%s" % (jsonConf["source"]["locust"]["dockerImageTag"], jsonConf["userInfo"]["aws"]["userTag"])
		dockerImageTag = dockerImageTag.lower()
		binaryPath = jsonConf["source"]["locust"]["binaryPath"]
		dockerPkgPath = jsonConf["source"]["locust"]["dockerPkgPath"]
		enabledEthTest = jsonConf["deploy"]["locustSlave"]["enabledEthTest"]

		locustDir = "klaytn-load-tester"

		ExecuteShell("mkdir -p %s" % binaryPath)
		if enabledEthTest == True:
			ExecuteShell("cp %s/klayslave/ethTxGenerator/ethTxGenerator %s/bin/" % (locustDir, binaryPath))

		docker_run_platform = ""
		if platform.machine() == "arm64":
			docker_run_platform = "--platform linux/amd64"
		ExecuteShell("docker run %s --rm -v $(pwd)/%s:/tmp1 %s bash -c 'cp -r %s/* /tmp1'" %
			(docker_run_platform, binaryPath, dockerImageTag, dockerPkgPath))

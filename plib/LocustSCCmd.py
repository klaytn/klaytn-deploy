#!/usr/bin/env python3

import os
import platform

from LocustSCMasterCmd import LocustSCMasterCmd
from LocustSCSlaveCmd import LocustSCSlaveCmd
from KlaytnCommon import LoadConfig, ExecuteShell

class LocustSCCmd:
	def __init__(self, parsers):
		parser = parsers.add_parser("locustSC", help="Execute functions related to locustSC.")
		subparsers = parser.add_subparsers(dest="locust_subparser")

		p = subparsers.add_parser("build", help="Build locustSC-load-tester.")
		p.set_defaults(func=self.build)

		p = subparsers.add_parser("extract", help="Extract binary files from the docker image of locustSC-load-tester.")
		p.set_defaults(func=self.extract)

		LocustSCMasterCmd(subparsers)
		LocustSCSlaveCmd(subparsers)

	def isEnabled(self, jsonConf):
		return jsonConf["deploy"]["locustSCSlave"]["enabled"] == True and jsonConf["deploy"]["locustSCMaster"]["enabled"] == True

	def build(self, args):
		jsonConf = LoadConfig(args.conf)

		if not self.isEnabled(jsonConf):
			return

		ref = jsonConf["source"]["locustSC"]["git"]["ref"]
		branch = jsonConf["source"]["locustSC"]["git"]["branch"]
		dockerImageTag = "%s-%s" % (jsonConf["source"]["locustSC"]["dockerImageTag"], jsonConf["userInfo"]["aws"]["tags"]["User"])
		dockerImageTag = dockerImageTag.lower()

		locustDir = "klaytn-load-tester"

		if os.path.exists(locustDir) :
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

	def extract(self, args):
		jsonConf = LoadConfig(args.conf)

		if not self.isEnabled(jsonConf):
			return

		dockerImageTag = "%s-%s" % (jsonConf["source"]["locustSC"]["dockerImageTag"], jsonConf["userInfo"]["aws"]["tags"]["User"])
		dockerImageTag = dockerImageTag.lower()
		binaryPath = jsonConf["source"]["locustSC"]["binaryPath"]
		dockerPkgPath = jsonConf["source"]["locustSC"]["dockerPkgPath"]

		ExecuteShell("mkdir -p %s" % binaryPath)

		docker_run_platform = ""
		if platform.machine() == "arm64":
			docker_run_platform = "--platform linux/amd64"
		ExecuteShell("docker run %s --rm -v $(pwd)/%s:/tmp1 %s bash -c 'cp -r %s/* /tmp1'" %
			(docker_run_platform, binaryPath, dockerImageTag, dockerPkgPath))

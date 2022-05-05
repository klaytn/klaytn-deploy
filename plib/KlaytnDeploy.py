#!/usr/bin/env python3
from __future__ import with_statement
import boto3
import json
from subprocess import call,check_call
import os,errno, pexpect, sys
import shutil
import re
import pprint
import argparse
from KlaytnInstanceManager import KlaytnInstanceManager
from KlaytnNodeCmd import KlaytnNodeCmd
from KlaytnCmd import KlaytnCmd
from KlaytnCommon import ExecuteShell
from GrafanaCmd import GrafanaCmd
from GraylogCmd import GraylogCmd
from LocustCmd import LocustCmd
from LocustSCCmd import LocustSCCmd
from PrintCmd import PrintCmd
from AWSDBCmd import AWSDBCmd

################################################################################
# Global functions
################################################################################
if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--conf", type=str, default="conf.json", help="configuartion file. default=conf.json")
	subparsers = parser.add_subparsers(dest='subparser')

	# Print
	PrintCmd(subparsers)

	# Build Klaytn
	KlaytnCmd(subparsers)

	# Add commands related to Klaytn nodes.
	KlaytnNodeCmd("CN", subparsers)
	KlaytnNodeCmd("PN", subparsers)
	KlaytnNodeCmd("EN", subparsers)
	KlaytnNodeCmd("BN", subparsers)
	KlaytnNodeCmd("CNBN", subparsers)
	KlaytnNodeCmd("SCN", subparsers)
	KlaytnNodeCmd("SPN", subparsers)
	KlaytnNodeCmd("SEN", subparsers)

	# grafana
	GrafanaCmd(subparsers)

	# graylog
	GraylogCmd(subparsers)

	# locust
	LocustCmd(subparsers)

	# locust service chain
	LocustSCCmd(subparsers)

	# DynamoDB table and S3 command
	AWSDBCmd(subparsers)

	args = parser.parse_args()

	confFileName = args.conf
	if args.conf == "conf.json" and os.getenv("KLAYTN_DEPLOY_CONF") != None:
		confFileName = os.getenv("KLAYTN_DEPLOY_CONF")

	# check existence of conf file.
	if os.path.exists(confFileName) == False:
		print ("It seems that you don't have %s yet." % (confFileName))
		print ("$ cp conf.template.json %s" % (confFileName))
		print ("Then, modify % as you want." % (confFileName))
		sys.exit(1)

	try:
		func = args.func
	except AttributeError:
		parser.error("too few arguments")
	func(args)

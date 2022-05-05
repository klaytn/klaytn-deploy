#!/usr/bin/env python3

import os
import json
import pprint
from KlaytnCommon import LoadConfig, ExecuteShell
from PrepareFiles import PrepareFiles

class PrintCmd:
	def __init__(self, parsers):
		parser = parsers.add_parser("show")
		subparsers = parser.add_subparsers(dest="showsubparser")

		p = subparsers.add_parser("conf", help="Print current configuration of klaytn-deploy.")
		p.set_defaults(func=self.conf)

	def conf(self, args):
		jsonConf = LoadConfig(args.conf)
		print (json.dumps(jsonConf, indent=4, separators=(',', ': ')))

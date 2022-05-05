#!/usr/bin/env python3

import json
from GraylogInstanceManager import GraylogInstanceManager
from KlaytnCommon import LoadConfig

class GraylogCmd:
	def __init__(self, parsers):
		self.nodeType = "graylog"
		parser = parsers.add_parser(self.nodeType)
		subparsers = parser.add_subparsers(dest="Graylogsubparser")

		p = subparsers.add_parser("create", help="Create a Graylog instance.")
		p.set_defaults(func=self.create)

		p = subparsers.add_parser("terminateInstances", help="Terminate the Graylog instance.")
		p.set_defaults(func=self.terminateInstances)

		p = subparsers.add_parser("stopInstances", help="Stop the Graylog instance.")
		p.set_defaults(func=self.stopInstances)

		p = subparsers.add_parser("startInstances", help="Start the Graylog instance.")
		p.set_defaults(func=self.startInstances)

		p = subparsers.add_parser("ssh", help="Connect to the Graylog instance via ssh.")
		p.set_defaults(func=self.ssh)

		p = subparsers.add_parser("upload", help="Upload files to the Graylog instance.")
		p.set_defaults(func=self.upload)

		p = subparsers.add_parser("init", help="Initialize the Graylog instance to get started.")
		p.set_defaults(func=self.init)

		p = subparsers.add_parser("start", help="Start the Graylog instance.")
		p.set_defaults(func=self.start)

		p = subparsers.add_parser("stop", help="Stop the Graylog instance.")
		p.set_defaults(func=self.stop)

		p = subparsers.add_parser("url", help="Print URL of the Graylog website.")
		p.set_defaults(func=self.url)

	def create(self, args):
		self.loadConfig(args.conf)
		node = GraylogInstanceManager(self.config, self.config["userInfo"])
		node.CreateInstances()

	def terminateInstances(self, args):
		self.loadConfig(args.conf)
		node = GraylogInstanceManager(self.config, self.config["userInfo"])
		node.TerminateInstances(self.config)

	def stopInstances(self, args):
		self.loadConfig(args.conf)
		node = GraylogInstanceManager(self.config, self.config["userInfo"])
		node.StopInstances()

	def startInstances(self, args):
		self.loadConfig(args.conf)
		node = GraylogInstanceManager(self.config, self.config["userInfo"])
		node.StartInstances()

	def ssh(self, args):
		self.loadConfig(args.conf)
		node = GraylogInstanceManager(self.config, self.config["userInfo"])
		node.Ssh(0, "")

	def upload(self, args):
		self.loadConfig(args.conf)
		node = GraylogInstanceManager(self.config, self.config["userInfo"])
		node.Upload()

	def init(self, args):
		self.loadConfig(args.conf)
		node = GraylogInstanceManager(self.config, self.config["userInfo"])
		node.Init()

	def start(self, args):
		self.loadConfig(args.conf)
		node = GraylogInstanceManager(self.config, self.config["userInfo"])
		node.Start()

	def stop(self, args):
		self.loadConfig(args.conf)
		node = GraylogInstanceManager(self.config, self.config["userInfo"])
		node.Stop()

	def url(self, args):
		self.loadConfig(args.conf)
		node = GraylogInstanceManager(self.config, self.config["userInfo"])
		node.PrintUrl()

	################################################################################
	# Private functions
	################################################################################
	def checkNumNodes(self):
		if self.config["deploy"][self.nodeType]["aws"]["numNodes"] != 1:
			raise Exception("numNodes should be one!")

	def loadConfig(self, confFileName):
		self.config = LoadConfig(confFileName)
		self.checkNumNodes()

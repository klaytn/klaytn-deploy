#!/usr/bin/env python3

from KlaytnCommon import LoadConfig
from LocustSCMasterInstanceManager import LocustSCMasterInstanceManager

class LocustSCMasterCmd:
	def __init__(self, parsers):
		self.nodeType = "locustSCMaster"

		parser = parsers.add_parser("master", help="Commands related to a locust master SC node.")
		subparsers = parser.add_subparsers(dest="locust_master_subparser")

		p = subparsers.add_parser("create", help="Create a locust master SC instance.")
		p.set_defaults(func=self.create)

		p = subparsers.add_parser("terminateInstances", help="Terminate the locust master SC instance.")
		p.set_defaults(func=self.terminateInstances)

		p = subparsers.add_parser("stopInstances", help="Stop the locust master SC instance.")
		p.set_defaults(func=self.stopInstances)

		p = subparsers.add_parser("startInstances", help="Start the locust master SC instance.")
		p.set_defaults(func=self.startInstances)

		p = subparsers.add_parser("ssh", help="Connect to the locust master SC instance via ssh.")
		p.set_defaults(func=self.ssh)

		p = subparsers.add_parser("prepare", help="Prepare files to be uploaded to the locust master SC instance.")
		p.set_defaults(func=self.prepare)

		p = subparsers.add_parser("upload", help="Upload files to the locust master SC instance.")
		p.set_defaults(func=self.upload)

		p = subparsers.add_parser("init", help="Initialize the locust master SC instnace to get started.")
		p.set_defaults(func=self.init)

		p = subparsers.add_parser("start", help="Start the locust master SC.")
		p.set_defaults(func=self.start)

		p = subparsers.add_parser("stop", help="Stop the locust master SC process.")
		p.set_defaults(func=self.stop)

		p = subparsers.add_parser("url", help="Print URL of the locust master SC website.")
		p.set_defaults(func=self.url)

		p = subparsers.add_parser("log", help="Print log of the locust master SC")
		p.set_defaults(func=self.log)

	def create(self, args):
		self.loadConfig(args.conf)
		node = LocustSCMasterInstanceManager(self.config, self.config["userInfo"])
		node.CreateInstances()

	def terminateInstances(self, args):
		self.loadConfig(args.conf)
		node = LocustSCMasterInstanceManager(self.config, self.config["userInfo"])
		node.TerminateInstances(self.config)

	def stopInstances(self, args):
		self.loadConfig(args.conf)
		node = LocustSCMasterInstanceManager(self.config, self.config["userInfo"])
		node.StopInstances()

	def startInstances(self, args):
		self.loadConfig(args.conf)
		node = LocustSCMasterInstanceManager(self.config, self.config["userInfo"])
		node.StartInstances()

	def ssh(self, args):
		self.loadConfig(args.conf)
		node = LocustSCMasterInstanceManager(self.config, self.config["userInfo"])
		node.Ssh(0, "")

	def prepare(self, args):
		self.loadConfig(args.conf)
		node = LocustSCMasterInstanceManager(self.config, self.config["userInfo"])
		node.Prepare()

	def upload(self, args):
		self.loadConfig(args.conf)
		node = LocustSCMasterInstanceManager(self.config, self.config["userInfo"])
		node.Upload()

	def init(self, args):
		self.loadConfig(args.conf)
		node = LocustSCMasterInstanceManager(self.config, self.config["userInfo"])
		node.Init()

	def start(self, args):
		self.loadConfig(args.conf)
		node = LocustSCMasterInstanceManager(self.config, self.config["userInfo"])
		node.Start()

	def stop(self, args):
		self.loadConfig(args.conf)
		node = LocustSCMasterInstanceManager(self.config, self.config["userInfo"])
		node.Stop()

	def url(self, args):
		self.loadConfig(args.conf)
		node = LocustSCMasterInstanceManager(self.config, self.config["userInfo"])
		node.PrintUrl()

	def log(self, args):
		self.loadConfig(args.conf)
		node = LocustSCMasterInstanceManager(self.config, self.config["userInfo"])
		node.CatLog()

	################################################################################
	# Private functions
	################################################################################
	def checkNumNodes(self):
		if self.config["deploy"][self.nodeType]["aws"]["numNodes"] != 1:
			raise Exception("numNodes should be one!")

	def loadConfig(self, confFileName):
		self.config = LoadConfig(confFileName)
		self.checkNumNodes()

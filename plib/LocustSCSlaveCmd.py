#!/usr/bin/env python3

from KlaytnCommon import LoadConfig
from LocustSCSlaveInstanceManager import LocustSCSlaveInstanceManager

class LocustSCSlaveCmd:
	def __init__(self, parsers):
		self.nodeType = "locustSCSlave"

		parser = parsers.add_parser("slave", help="Commands related to locust slaves SC.")
		subparsers = parser.add_subparsers(dest="locust_slave_subparser")

		p = subparsers.add_parser("create", help="Create locust slave SC instances.")
		p.set_defaults(func=self.create)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("terminateInstances", help="Terminate locust slave SC instances.")
		p.set_defaults(func=self.terminateInstances)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("stopInstances", help="Stop locust slave SC instances.")
		p.set_defaults(func=self.stopInstances)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("startInstances", help="Start locust slave SC instances.")
		p.set_defaults(func=self.startInstances)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("ssh", help="Connect to the specified locust slave SC instance.")
		p.set_defaults(func=self.ssh)
		p.add_argument("id", type=int)

		p = subparsers.add_parser("prepare", help="Prepare files to be uploaded to the locust slave SC instances.")
		p.set_defaults(func=self.prepare)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("upload", help="Upload files to the locust slave SC instances.")
		p.set_defaults(func=self.upload)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("init", help="Initialize the locust slave SC instances to get started.")
		p.set_defaults(func=self.init)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("start", help="Start locust slaves SC.")
		p.set_defaults(func=self.start)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("stop", help="Stop locust slave SC processes.")
		p.set_defaults(func=self.stop)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("log", help="Print log of the specified locust slave SC.")
		p.set_defaults(func=self.log)
		p.add_argument("id", type=int, default=-1)
		p.add_argument("slaveId", type=int, default=-1, help="slave instance ID")

		p = subparsers.add_parser("taillog", help="Print log of the specified locust slave SC using tail -f.")
		p.set_defaults(func=self.tailLog)
		p.add_argument("id", type=int, default=-1)
		p.add_argument("slaveId", type=int, default=-1, help="slave instance ID")

	def create(self, args):
		self.loadConfig(args.conf)
		node = LocustSCSlaveInstanceManager(self.config, self.config["userInfo"])
		if args.id == -1:
			# create all instances
			node.CreateInstances()
		else:
			# create the specified instance
			node.CreateInstanceById(args.id)

	def terminateInstances(self, args):
		self.loadConfig(args.conf)
		node = LocustSCSlaveInstanceManager(self.config, self.config["userInfo"])
		if args.id == -1:
			# create all instances
			node.TerminateInstances(self.config)
		else:
			# create the specified instance
			node.TerminateInstanceById(args.id, self.config)

	def stopInstances(self, args):
		self.loadConfig(args.conf)
		node = LocustSCSlaveInstanceManager(self.config, self.config["userInfo"])
		if args.id == -1:
			# create all instances
			node.StopInstances()
		else:
			# create the specified instance
			node.StopInstanceById(args.id)

	def startInstances(self, args):
		self.loadConfig(args.conf)
		node = LocustSCSlaveInstanceManager(self.config, self.config["userInfo"])
		if args.id == -1:
			# create all instances
			node.StartInstances()
		else:
			# create the specified instance
			node.StartInstanceById(args.id)

	def ssh(self, args):
		self.loadConfig(args.conf)
		node = LocustSCSlaveInstanceManager(self.config, self.config["userInfo"])
		if args.id == -1:
			raise Exception("id should be explicitly specified.")
		else:
			# create the specified instance
			node.Ssh(args.id, "")

	def prepare(self, args):
		self.loadConfig(args.conf)
		node = LocustSCSlaveInstanceManager(self.config, self.config["userInfo"])
		if args.id == -1:
			node.Prepare()
		else:
			# create the specified instance
			node.PrepareById(args.id)

	def upload(self, args):
		self.loadConfig(args.conf)
		node = LocustSCSlaveInstanceManager(self.config, self.config["userInfo"])
		if args.id == -1:
			node.Upload()
		else:
			# create the specified instance
			node.UploadById(args.id)

	def init(self, args):
		self.loadConfig(args.conf)
		node = LocustSCSlaveInstanceManager(self.config, self.config["userInfo"])
		if args.id == -1:
			node.Init()
		else:
			# create the specified instance
			node.InitById(args.id)

	def start(self, args):
		self.loadConfig(args.conf)
		node = LocustSCSlaveInstanceManager(self.config, self.config["userInfo"])
		if args.id == -1:
			node.Start()
		else:
			# create the specified instance
			node.StartById(args.id)

	def stop(self, args):
		self.loadConfig(args.conf)
		node = LocustSCSlaveInstanceManager(self.config, self.config["userInfo"])
		if args.id == -1:
			node.Stop()
		else:
			# create the specified instance
			node.StopById(args.id)

	def log(self, args):
		self.loadConfig(args.conf)
		node = LocustSCSlaveInstanceManager(self.config, self.config["userInfo"])
		if args.id == -1:
			raise Exception("id should be explicitly specified.")
		if args.slaveId == -1:
			raise Exception("slave should be explicitly specified.")
		node.CatLogById(args.id, args.slaveId)

	def tailLog(self, args):
		self.loadConfig(args.conf)
		node = LocustSCSlaveInstanceManager(self.config, self.config["userInfo"])
		if args.id == -1:
			raise Exception("id should be explicitly specified.")
		if args.slaveId == -1:
			raise Exception("slave should be explicitly specified.")
		node.TailLogById(args.id, args.slaveId)

	################################################################################
	# Private functions
	################################################################################
	def loadConfig(self, confFileName):
		self.config = LoadConfig(confFileName)

#!/usr/bin/env python3

import json
from KlaytnInstanceFactory import KlaytnInstanceFactory
from KlaytnCommon import LoadConfig

class KlaytnNodeCmd:
	def __init__(self, nodeType, parsers):
		self.nodeType = nodeType
		self.binname = self.getBinName()

		nodeTypeCmd = nodeType.lower()
		parser = parsers.add_parser(nodeTypeCmd)
		subparsers = parser.add_subparsers(dest="%ssubparser" % nodeTypeCmd)

		p = subparsers.add_parser("create", help="Creates %s instances." % (self.nodeType))
		p.set_defaults(func=self.create)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("terminateInstances", help="Terminates %s instances." % (self.nodeType))
		p.set_defaults(func=self.terminateInstances)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("stopInstances", help="Stops %s instances." % (self.nodeType))
		p.set_defaults(func=self.stopInstances)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("startInstances", help="Stops %s instances." % (self.nodeType))
		p.set_defaults(func=self.startInstances)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("getip", help="Print IPs of %s instances." % (self.nodeType))
		p.set_defaults(func=self.getIp)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("num", help="Print number of instances.")
		p.set_defaults(func=self.num)

		p = subparsers.add_parser("profile", help="profile an instance of %s." % (self.nodeType))
		p.set_defaults(func=self.profile)
		p.add_argument("--id", type=int, default=-1)
		p.add_argument("--duration", type=int, default=10, help="duration of tracing. unit=second. It only works for CPU profiling.")
		p.add_argument("--mem", action="store_true", help="profile memory instead of CPU.")

		p = subparsers.add_parser("trace", help="trace an instance of %s." % (self.nodeType))
		p.set_defaults(func=self.trace)
		p.add_argument("--id", type=int, default=-1)
		p.add_argument("--duration", type=int, default=10, help="duration of tracing. unit=second")

		p = subparsers.add_parser("updateip", help="Update files privateip and publicip in directories upload/%s*." % (self.nodeType))
		p.set_defaults(func=self.updateIp)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("upload", help="Upload files in upload/%s* to appropriate instances.")
		p.set_defaults(func=self.upload)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("download", help="Upload files in download/%s* to appropriate instances.")
		p.set_defaults(func=self.download)
		p.add_argument("filename", type=str)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("ssh", help="connect to the specified node via ssh.")
		p.set_defaults(func=self.ssh)
		p.add_argument("id", type=int)
		p.add_argument('cmd', nargs='*')

		p = subparsers.add_parser("init", help="initialize the instances.")
		p.set_defaults(func=self.init)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("start", help="Start k%s process." % (self.nodeType.lower()))
		p.set_defaults(func=self.start)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("status", help="Check status of k%s." % (self.nodeType.lower()))
		p.set_defaults(func=self.status)
		p.add_argument("--id", type=int, default=-1)

		p = subparsers.add_parser("stop", help="Stop k%s process." % (self.nodeType.lower()))
		p.set_defaults(func=self.stop)
		p.add_argument("--id", type=int, default=-1)
		p.add_argument("-f", "--force", action="store_true", help="kill process using killall")

		p = subparsers.add_parser("log", help="Print the log in the specified instance.")
		p.set_defaults(func=self.log)
		p.add_argument("id", type=int)

		p = subparsers.add_parser("taillog", help="Print the log in the specified instance using tail -f.")
		p.set_defaults(func=self.tailLog)
		p.add_argument("id", type=int)

		p = subparsers.add_parser("jsexec", help="Execute javascript code on k%s process." % (self.nodeType.lower()))
		p.set_defaults(func=self.jsExec)
		p.add_argument("--id", type=int, default=-1)
		p.add_argument('cmd', nargs='*')

		p = subparsers.add_parser("attach", help="attach to the node's ipc.")
		p.set_defaults(func=self.attach)
		p.add_argument("id", type=int, default=-1)

		p = subparsers.add_parser("exec", help="Execute the specified command via ssh.")
		p.set_defaults(func=self.exe)
		p.add_argument("--id", type=int, default=-1)
		p.add_argument('cmd', nargs='*')

		p = subparsers.add_parser("volume", help="Execute the specified command via ssh.")
		p.set_defaults(func=self.volume)
		p.add_argument("--id", type=int, default=-1)
		p.add_argument("--size", type=int, default=-1, help="specify the volume size in GiB.")
		p.add_argument("--disable-aws", default=False, action="store_true", help="Use this if you do not want to execute aws.modify_volume")

		p = subparsers.add_parser("deleteDB", help="Delete k%s's DynamoDB table." % (self.nodeType.lower()))
		p.set_defaults(func=self.deleteDB)
		p.add_argument("--id", type=int, default=-1)

	def getBinName(self):
		if self.nodeType == "CNBN":
			return "kbn"
		return "k%s" % (self.nodeType.lower())

	def create(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			# create all instances
			node.CreateInstances()
		else:
			# create the specified instance
			node.CreateInstanceById(args.id)

	def terminateInstances(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			# create all instances
			node.TerminateInstances(jsonConf)
		else:
			# create the specified instance
			node.TerminateInstanceById(args.id, jsonConf)

	def stopInstances(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			# create all instances
			node.StopInstances()
		else:
			# create the specified instance
			node.StopInstanceById(args.id)

	def startInstances(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			# create all instances
			node.StartInstances()
		else:
			# create the specified instance
			node.StartInstanceById(args.id)

	def num(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		print (len(node.GetPublicIPAddresses()))

	def getIp(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			# create all instances
			print (node.GetIpAddresses())
		else:
			# create the specified instance
			print (node.GetIpAddressById(args.id))

	def updateIp(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			# create all instances
                        node.WritePrivatePublicIPs()
		else:
			# create the specified instance
			node.WritePrivatePublicIPsById(args.id)

	def upload(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			# create all instances
			node.Upload()
		else:
			# create the specified instance
			node.UploadById(args.id)

	def profile(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			node.Profile(args.duration, args.mem)
		else:
			node.ProfileById(args.id, args.duration, args.mem)

	def trace(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			node.Trace(args.duration)
		else:
			node.TraceById(args.id, args.duration)

	def download(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			# create all instances
			node.Download(args.filename)
		else:
			# create the specified instance
			node.DownloadById(args.id, args.filename)

	def ssh(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			raise Exception("id should be explicitly specified.")
		else:
			# create the specified instance
			node.Ssh(args.id, args.cmd)

	def init(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			node.InitBlockchain()
		else:
			node.InitBlockchainById(args.id)

	def start(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			node.Start()
		else:
			# create the specified instance
			node.StartById(args.id)

	def stop(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			node.Stop(args.force)
		else:
			# create the specified instance
			node.StopById(args.id, args.force)

	def status(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			node.Status()
		else:
			# create the specified instance
			node.StatusById(args.id)

	def log(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			raise Exception("id should be explicitly specified.")
		else:
			# create the specified instance
			node.CatLogById(args.id)

	def attach(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			raise Exception("id should be explicitly specified.")
		else:
			# create the specified instance
			node.AttachById(args.id)

	def tailLog(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			raise Exception("id should be explicitly specified.")
		else:
			# create the specified instance
			node.TailLogById(args.id)

	def jsExec(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			node.JsExec(args.cmd)
		else:
			# create the specified instance
			node.JsExecById(args.id, args.cmd)

	def exe(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			node.Exe(args.cmd)
		else:
			# create the specified instance
			node.ExeById(args.id, args.cmd)

	def volume(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			node.Volume(args.size, args.disable_aws)
		else:
			# create the specified instance
			node.VolumeById(args.id, args.size, args.disable_aws)

	def deleteDB(self, args):
		jsonConf = LoadConfig(args.conf)
		node = KlaytnInstanceFactory(jsonConf, self.nodeType, self.binname)
		if args.id == -1:
			# delete all instances' dynamoDB tables
			node.TerminateDynamoDBTable(jsonConf)
		else:
			# delete a instance's dynamoDB table
			node.TerminateDynamoDBTableById(args.id, jsonConf)

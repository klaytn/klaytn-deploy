#!/usr/bin/env python3
import boto3
import sys
import os
import time
import subprocess
import json
from multiprocessing import Process, Queue
from KlaytnCommon import ExecuteShell, EscapeChars, GetTableName
from botocore.exceptions import NoRegionError, ClientError, WaiterError
from AWSDBCmd import DeleteDynamoDB

def sshExecute(host, sshKeyPath, username, cmd):
	sys.exit(os.system("ssh -i %s %s@%s \"%s\"" % (sshKeyPath, username, host, cmd)))

def sshExecuteWithReturn(host, sshKeyPath, username, cmd, queue):
	exitcode = 0
	out = ""
	try:
		out = subprocess.check_output("ssh -i %s %s@%s \"%s\"" % (sshKeyPath, username, host, cmd), stderr=subprocess.STDOUT, shell=True).strip()
	except subprocess.CalledProcessError as e:
		exitcode = e.returncode
		out = e.output

	queue.put((host, out))
	sys.exit(exitcode)

def sshExecuteTty(host, sshKeyPath, username, cmd):
	sys.exit(os.system("ssh -t -i %s %s@%s \"%s\"" % (sshKeyPath, username, host, cmd)))

def sshTransfer(host, sshKeyPath, username, src, dest):
	sys.exit(os.system("scp -r -i %s %s %s@%s:%s" % (sshKeyPath, src, username, host, dest)))

def sshDownload(host, sshKeyPath, username, src, dest):
	sys.exit(os.system("scp -r -i %s %s@%s:%s %s" % (sshKeyPath, username, host, src, dest)))

def sshTransferPropagate(srchost, host, sshKeyPath, username, src, dest):
	sys.exit(os.system("scp -3 -i %s %s@%s:%s %s@%s:%s" % (sshKeyPath, username, srchost, src, username, host, dest)))

def ParallelTransfer(hosts, sshKeyPath, username, src, dest):
	plist = []
	for h in hosts:
		p = Process(target=sshTransfer, args=(h, sshKeyPath, username, src, dest))
		p.start()
		plist.append(p)

	for i in range(0, len(plist)):
		plist[i].join()
		if plist[i].exitcode != 0:
			raise Exception("failed execution on host %s! exitcode=%s" % (hosts[i], plist[i].exitcode))

def ParallelTransferPropagate(hosts, sshKeyPath, username, src, dest):
	if len(hosts) == 0:
		return

	srchost = hosts[0]
	ExecuteShell("scp -r -i %s %s %s@%s:%s" % (sshKeyPath, src, username, srchost, dest))

	plist = ['']
	for i in range(1, len(hosts)):
		h = hosts[i]
		p = Process(target=sshTransferPropagate, args=(srchost, h, sshKeyPath, username, dest, dest))
		p.start()
		plist.append(p)

	for i in range(1, len(plist)):
		plist[i].join()
		if plist[i].exitcode != 0:
			raise Exception("failed execution on host %s! exitcode=%s" % (hosts[i], plist[i].exitcode))

def ParallelDownload(hosts, sshKeyPath, username, src, dest):
	plist = []
	for h in hosts:
		p = Process(target=sshDownload, args=(h, sshKeyPath, username, src, dest))
		p.start()
		plist.append(p)

	for i in range(0, len(plist)):
		plist[i].join()
		if plist[i].exitcode != 0:
			raise Exception("failed execution on host %s! exitcode=%s" % (hosts[i], plist[i].exitcode))

def ParallelTransferList(hosts, sshKeyPath, username, srclist, destlist):
	plist = []
	for i in range(0, len(hosts)):
		p = Process(target=sshTransfer, args=(hosts[i], sshKeyPath, username, srclist[i], destlist[i]))
		p.start()
		plist.append(p)

	for i in range(0, len(plist)):
		plist[i].join()
		if plist[i].exitcode != 0:
			raise Exception("failed execution on host %s! exitcode=%s" % (hosts[i], plist[i].exitcode))

def ParallelDownloadList(hosts, sshKeyPath, username, srclist, destlist):
	plist = []
	for i in range(0, len(hosts)):
		p = Process(target=sshDownload, args=(hosts[i], sshKeyPath, username, srclist[i], destlist[i]))
		p.start()
		plist.append(p)

	for i in range(0, len(plist)):
		plist[i].join()
		if plist[i].exitcode != 0:
			raise Exception("failed execution on host %s! exitcode=%s" % (hosts[i], plist[i].exitcode))

def ParallelExecuteTty(hosts, sshKeyPath, username, cmd):
	plist = []
	for h in hosts:
		p = Process(target=sshExecuteTty, args=(h, sshKeyPath, username, cmd))
		p.start()
		plist.append(p)

	for i in range(0, len(plist)):
		plist[i].join()
		if plist[i].exitcode != 0:
			raise Exception("failed execution on host %s! exitcode=%s" % (hosts[i], plist[i].exitcode))

def ParallelExecuteWithReturn(hosts, sshKeyPath, username, cmd, raiseError):
	plist = []
	ret = {}
	queue = Queue()
	for h in hosts:
		p = Process(target=sshExecuteWithReturn, args=(h, sshKeyPath, username, cmd, queue))
		p.start()
		plist.append(p)

	for i in range(0, len(plist)):
		plist[i].join()
		if raiseError and plist[i].exitcode != 0:
			raise Exception("failed execution on host %s! exitcode=%s" % (hosts[i], plist[i].exitcode))
		out = queue.get()
		ret[out[0]] = out[1]

	return ret

def SequentialExecute(hosts, sshKeyPath, username, cmd):
	for h in hosts:
		p = Process(target=sshExecute, args=(h, sshKeyPath, username, cmd))
		p.start()
		p.join()
		if p.exitcode != 0:
			raise Exception("failed execution on host %s! exitcode=%s" % (h, p.exitcode))

def ParallelExecute(hosts, sshKeyPath, username, cmd):
	plist = []
	for h in hosts:
		p = Process(target=sshExecute, args=(h, sshKeyPath, username, cmd))
		p.start()
		plist.append(p)

	for i in range(0, len(plist)):
		plist[i].join()
		if plist[i].exitcode != 0:
			raise Exception("failed execution on host %s! exitcode=%s" % (hosts[i], plist[i].exitcode))

class AWSInstanceManager:
	def __init__(self, awsConf, nodeType, userInfo):
		self.awsConf = awsConf
		self.nodeType = nodeType
		self.userInfo = userInfo

	################################################################################
	# Public functions
	################################################################################
	def CreateInstances(self):
		self.createNodeInstances()
		self.WritePrivatePublicIPs()

	def CreateInstanceById(self, nodeId):
		self.checkIndex(nodeId)
		self.createNodeInstanceById(nodeId)
		self.WritePrivatePublicIPsById(nodeId)

	def TerminateInstances(self, config):
		self.terminateNodeInstances()

	def TerminateInstanceById(self, nodeId, config):
		self.checkIndex(nodeId)
		self.terminateNodeInstanceById(nodeId)

	def TerminateAll(self):
		userTag = self.userInfo["aws"]["tags"]["User"]
		self.TerminateInstancesByUserTag(userTag)

	def StopInstances(self):
		self.stopNodeInstances()

	def StopInstanceById(self, nodeId):
		self.checkIndex(nodeId)
		self.stopNodeInstanceById(nodeId)

	def StopInstancesAll(self):
		userTag = self.userInfo["aws"]["tags"]["User"]
		self.StopInstancesByUserTag(userTag)

	def StartInstances(self):
		self.startNodeInstances()

	def StartInstanceById(self, nodeId):
		self.checkIndex(nodeId)
		self.startNodeInstanceById(nodeId)

	def StartInstancesAll(self):
		userTag = self.userInfo["aws"]["tags"]["User"]
		self.StartInstancesByUserTag(userTag)

	def GetIpAddresses(self):
		return self.getPrivatePublicIps()

	def GetPublicIPAddresses(self):
		privateIPs, publicIPs = self.getPrivatePublicIps()
		hosts = []
		# flatten publicIPs
		for i in range(0, len(publicIPs)):
			hosts.append(publicIPs["%s%d"%(self.nodeType, i)][0])

		return hosts

	def GetPublicIPAddressesById(self, index):
		privateIPs, publicIPs = self.getPrivatePublicIpsById(index)
		hosts = []
		# flatten publicIPs
		hosts.append(publicIPs["%s%d"%(self.nodeType, index)][0])

		return hosts

	def GetIpAddressById(self, nodeId):
		self.checkIndex(nodeId)
		return self.getPrivatePublicIpsById(nodeId)

	def Ssh(self, index, cmd):
		self.checkIndex(index)
		privateIPs, publicIPs = self.GetIpAddressById(index)

		for n, ips in publicIPs.items():
			break

		self.ssh(ips[0], cmd)

	################################################################################
	# Private functions
	################################################################################
	def ssh(self, host, cmd):
		sshKeyPath = self.userInfo["keyPath"]
		userName = self.awsConf["userName"]
		if len(cmd) == 0:
			ExecuteShell("ssh -i %s %s@%s" % (sshKeyPath, userName, host))
		else:
			ExecuteShell("ssh -i %s %s@%s '%s'" % (sshKeyPath, userName, host, cmd))

	def execute(self, hosts, cmd, parallel=True):
		sshKeyPath = self.userInfo["keyPath"]
		userName = self.awsConf["userName"]
		if parallel:
			ParallelExecute(hosts, sshKeyPath, userName, cmd)
		else:
			SequentialExecute(hosts, sshKeyPath, userName, cmd)

	def executeWithReturn(self, hosts, cmd):
		sshKeyPath = self.userInfo["keyPath"]
		userName = self.awsConf["userName"]
		return ParallelExecuteWithReturn(hosts, sshKeyPath, userName, cmd, False)

	def executeTty(self, hosts, cmd):
		sshKeyPath = self.userInfo["keyPath"]
		userName = self.awsConf["userName"]
		ParallelExecuteTty(hosts, sshKeyPath, userName, cmd)

	def upload(self, hosts, src, dest):
		sshKeyPath = self.userInfo["keyPath"]
		userName = self.awsConf["userName"]
		ParallelTransfer(hosts, sshKeyPath, userName, src, dest)

	def uploadPropagate(self, hosts, src, dest):
		sshKeyPath = self.userInfo["keyPath"]
		userName = self.awsConf["userName"]
		ParallelTransferPropagate(hosts, sshKeyPath, userName, src, dest)

	def download(self, hosts, src, dest):
		sshKeyPath = self.userInfo["keyPath"]
		userName = self.awsConf["userName"]
		ParallelDownload(hosts, sshKeyPath, userName, src, dest)

	def uploadList(self, hosts, srclist, destlist):
		sshKeyPath = self.userInfo["keyPath"]
		userName = self.awsConf["userName"]
		ParallelTransferList(hosts, sshKeyPath, userName, srclist, destlist)

	def downloadList(self, hosts, srclist, destlist):
		sshKeyPath = self.userInfo["keyPath"]
		userName = self.awsConf["userName"]
		ParallelDownloadList(hosts, sshKeyPath, userName, srclist, destlist)

	def findSubnetId(self, nodeIdx):
		subnet = self.userInfo["aws"]["subnet"]
		if "subnets" in self.awsConf:
			numSubnetIds = len(self.awsConf["subnets"])
			subnet = self.awsConf["subnets"][nodeIdx % numSubnetIds]

		return subnet

	def findZone(self, nodeIdx):
		zone = self.userInfo["aws"]["zone"]
		if "zones" in self.awsConf:
			numZones = len(self.awsConf["zones"])
			zone = self.awsConf["zones"][nodeIdx % numZones]

		return zone

	def findImageId(self, nodeIdx):
		imageId = self.awsConf["imageId"]
		if "imageIds" in self.awsConf:
			numImages = len(self.awsConf["imageIds"])
			imageId = self.awsConf["imageIds"][nodeIdx % numImages]

		return imageId

	def findSecurityGroups(self, nodeIdx):
		securityGroup = self.awsConf["securityGroup"]
		if "securityGroups" in self.awsConf:
			numImages = len(self.awsConf["securityGroups"])
			securityGroup = self.awsConf["securityGroups"][nodeIdx % numImages]

		return securityGroup

	def createNodeInstances(self):
		userTag = self.userInfo["aws"]["tags"]["User"]
		keyName = self.userInfo["aws"]["keyName"]
		nodeType = self.nodeType
		numNodes = self.awsConf["numNodes"]
		for i in range(0, numNodes):
			self.createInstance(userTag, nodeType, i, keyName)

	def createNodeInstanceById(self, nodeIdx):
		self.checkIndex(nodeIdx)
		userTag = self.userInfo["aws"]["tags"]["User"]
		keyName = self.userInfo["aws"]["keyName"]
		nodeType = self.nodeType
		numNodes = self.awsConf["numNodes"]
		self.createInstance(userTag, nodeType, nodeIdx, keyName)

	def Volume(self, size, disableAws=False):
		if size < 0:
			raise Exception("Size should be positive: size=%d"%size)
		numNodes = self.awsConf["numNodes"]
		for i in range(0, numNodes):
			print ("Updating volume %s%d to %dG" % (self.nodeType, i, size))
			self.updateAwsVolume(i, size, disableAws)
		for i in range(0, numNodes):
			print ("Updating partition size...")
			self.updatePartition(i, size)

	def VolumeById(self, index, size, disableAws=False):
		if size < 0:
			raise Exception("Size should be positive: size=%d"%size)
		self.checkIndex(index)
		self.updateAwsVolume(index, size, disableAws)
		self.updatePartition(index, size)

	def createInstance(self, userTag, nodeType, index, keyName):
		resourceTags = self.userInfo["aws"]["tags"]

		nodeTypeTag, nodeTag, rawNodeTag = self.genTags(userTag, nodeType, index)
		resourceTags.update({
			"Name": nodeTag,
			"NodeType": nodeTypeTag,
			"Node": nodeTag,
			"RawNode": rawNodeTag,
			"ManagedBy": "klaytn-deploy",
		})

		requiredTags = {"User", "Team", "Project", "ManagedBy"}
		if not requiredTags <= resourceTags.keys():
			raise Exception("No required tags; User, Team, Project")

		privateIPs, publicIPs = self.getPrivatePublicIpsById(index)
		if len(privateIPs) != 0 or len(publicIPs) != 0:
			raise Exception("Node name %s is already deployed." % nodeTag)

		awsCredentials = ""
		if "accessKeyID" in self.userInfo["aws"] :
			awsCredentials += "export AWS_ACCESS_KEY_ID={0}\n".format(self.userInfo["aws"]["accessKeyID"])
		if "secretAccessKey" in self.userInfo["aws"] :
			awsCredentials += "export AWS_SECRET_ACCESS_KEY={0}\n".format(self.userInfo["aws"]["secretAccessKey"])

		zone = self.findZone(index)
		imageId = self.findImageId(index)
		subnetId = self.findSubnetId(index)
		securityGroup = self.findSecurityGroups(index)

		ec2Resource = boto3.resource('ec2', region_name=zone[:-1])
		instances = ec2Resource.create_instances(
			ImageId = imageId,
			InstanceType = self.awsConf["instanceType"],
			MinCount = 1,
			MaxCount = 1,
			KeyName = keyName,
			Monitoring = {
				'Enabled': True,
			},
			Placement = {
				'AvailabilityZone': zone,
			},
			UserData = """#!/bin/bash
					systemctl disable kend
					systemctl stop kend
					find /var /data -name nodekey -delete

					mkdir -p {0}/.ssh

					echo "{1}" >> /home/{0}/.bashrc

					echo "KLAYTN_PATH=~/klaytn" >> /home/{0}/.bashrc
					echo 'alias klaytn-attach="$KLAYTN_PATH/bin/ken attach ~/klaytn/data/klay.ipc"' >> /home/{0}/.bashrc
					echo 'alias klaytn-init="rm -rf $KLAYTN_PATH/data; mkdir -p $KLAYTN_PATH/data/klay; cp $KLAYTN_PATH/keys/nodekey $KLAYTN_PATH/data/klay/; cp $KLAYTN_PATH/conf/static-nodes.json $KLAYTN_PATH/data/ ; mv $KLAYTN_PATH/logs/kend.out $KLAYTN_PATH/logs/kend-`date +%d%H%M%S`.out;"' >> /home/{0}/.bashrc
					echo 'alias klaytn-start="$KLAYTN_PATH/bin/kend start"' >> /home/{0}/.bashrc
					echo 'alias klaytn-stop="$KLAYTN_PATH/bin/kend stop"' >> /home/{0}/.bashrc
					echo 'alias klaytn-status="$KLAYTN_PATH/bin/kend status"' >> /home/{0}/.bashrc
					echo 'alias klaytn-blocknumber="$KLAYTN_PATH/bin/ken --exec 'klay.blockNumber' attach $KLAYTN_PATH/data/klay.ipc"' >> /home/{0}/.bashrc
					echo 'alias klaytn-viconf="vi $KLAYTN_PATH/conf/kend.conf"' >> /home/{0}/.bashrc
					echo 'alias klaytn-vilog="vi $KLAYTN_PATH/logs/kend.out"' >> /home/{0}/.bashrc
					echo 'alias klaytn-log="cat $KLAYTN_PATH/logs/k{2}d.out"' >> /home/{0}/.bashrc
					echo 'alias klaytn-taillog="tail -f $KLAYTN_PATH/logs/k{2}d.out"' >> /home/{0}/.bashrc

					echo "net.core.netdev_max_backlog = 20000" >> /etc/sysctl.conf
					echo "net.core.rps_sock_flow_entries = 32768" >> /etc/sysctl.conf
					echo "net.core.rmem_max = 16777216" >> /etc/sysctl.conf
					echo "net.core.rmem_default = 253952" >> /etc/sysctl.conf
					echo "net.core.wmem_max = 16777216" >> /etc/sysctl.conf
					echo "net.core.wmem_default = 253952" >> /etc/sysctl.conf
					echo "net.core.somaxconn = 32768" >> /etc/sysctl.conf
					echo "net.ipv4.ip_local_port_range = 1024    60999" >> /etc/sysctl.conf
					echo "net.ipv4.tcp_rmem=253952 253952 16777216" >> /etc/sysctl.conf
					echo "net.ipv4.tcp_wmem=253952 253952 16777216" >> /etc/sysctl.conf
					echo "net.ipv4.tcp_window_scaling=1" >> /etc/sysctl.conf
					sysctl -p
					""".format(self.awsConf["userName"], awsCredentials, self.nodeType.lower()),
			BlockDeviceMappings=[
				{
					'DeviceName': self.awsConf["storage"]["DeviceName"],
					'VirtualName': '1',
					'Ebs': {
						'Encrypted': False,
						'DeleteOnTermination': True,
						'VolumeType': 'gp2',
						'VolumeSize': self.awsConf["storage"]["VolumeSize"] if "VolumeSize" in self.awsConf["storage"] else 1000, # 1T in default
					}
				}
			],
			NetworkInterfaces = [
				{
					'SubnetId': subnetId,
					'DeleteOnTermination': True,
					'DeviceIndex': 0,
					'AssociatePublicIpAddress':True,
					'Groups': securityGroup,
				}
			],
			TagSpecifications = [
				{
					'ResourceType': 'instance',
					'Tags':[{'Key': k, 'Value': v} for k, v in resourceTags.items()],
				}
			]
		)

		return instances

	def WritePrivatePublicIPs(self):
		userTag = self.userInfo["aws"]["tags"]["User"]
		nodeType = self.nodeType
		numNodes = self.awsConf["numNodes"]
		for i in range(0, numNodes):
			self.WritePrivatePublicIPsById(i)

	def WritePrivatePublicIPsById(self, index):
		self.checkIndex(index)
		userTag = self.userInfo["aws"]["tags"]["User"]
		nodeType = self.nodeType
		nodeTypeTag, nodeTag, rawNodeTag = self.genTags(userTag, nodeType, index)

		# Get an ip address of the instance and store it into upload/RawNode/publicip
		privateIPs, publicIPs = self.getPrivatePublicIpsById(index)
		loopIdx = 1
		while len(privateIPs) == 0 and len(publicIPs) == 0:
			print ("Retrying to receiving IP address of %s" % nodeTag)
			time.sleep(0.5 * loopIdx)
			privateIPs, publicIPs = self.getPrivatePublicIpsById(index)
			loopIdx *= 2

		targetDir = "upload/%s" % rawNodeTag
		# Make sure the target directory exists.
		os.system("rm -rf %s" % targetDir)
		os.system("mkdir -p %s" % targetDir)
		print ("target Dir = %s" % targetDir)

		with open("%s/publicip" % targetDir, "w") as f:
			for p in publicIPs[rawNodeTag]:
				f.write("%s\n" % p)

		with open("%s/privateip" % targetDir, "w") as f:
			for p in privateIPs[rawNodeTag]:
				f.write("%s\n" % p)

	def getPrivatePublicIps(self):
		userTag = self.userInfo["aws"]["tags"]["User"]
		nodeType = self.nodeType
		nodeTypeTag, nodeTag, rawNodeTag = self.genTags(userTag, nodeType, 0)
		publicIPs = {}
		privateIPs = {}

		response = self.gatherInstancesByNodeType(nodeTypeTag)
		for reservation in response["Reservations"]:
			for instance in reservation["Instances"]:
				rawNode = ""
				for tag in instance['Tags']:
					if tag['Key'] == 'RawNode':
						rawNode = tag['Value']
				if rawNode != "":
					if "PublicIpAddress" not in instance:
						return [], []
					if rawNode not in publicIPs:
						publicIPs[rawNode] = []
					publicIPs[rawNode].append(instance["PublicIpAddress"])
					if rawNode not in privateIPs:
						privateIPs[rawNode] = []
					privateIPs[rawNode].append(instance["PrivateIpAddress"])

		return privateIPs, publicIPs

	def getPrivatePublicIpsById(self, index):
		self.checkIndex(index)
		userTag = self.userInfo["aws"]["tags"]["User"]
		nodeType = self.nodeType
		nodeTypeTag, nodeTag, rawNodeTag = self.genTags(userTag, nodeType, index)
		publicIPs = {}
		privateIPs = {}

		response = self.gatherInstancesByNode(nodeTag)
		for reservation in response["Reservations"]:
			for instance in reservation["Instances"]:
				rawNode = ""
				for tag in instance['Tags']:
					if tag['Key'] == 'RawNode':
						rawNode = tag['Value']
				if rawNode != "":
					if "PublicIpAddress" not in instance:
						return [], []
					if rawNode not in publicIPs:
						publicIPs[rawNode] = []
					publicIPs[rawNode].append(instance["PublicIpAddress"])
					if rawNode not in privateIPs:
						privateIPs[rawNode] = []
					privateIPs[rawNode].append(instance["PrivateIpAddress"])

		return privateIPs, publicIPs

	def modifyVolume(self, volumeId, size):
		node = {}
		if "zones" in self.awsConf:
			for zone in self.awsConf["zones"]:
				ec2Client = boto3.client('ec2', region_name=zone[:-1])
				n = ec2Client.modify_volume(
					VolumeId=volumeId,
					Size=size,
				)

		else:
			ec2Client = boto3.client('ec2')
			node = ec2Client.modify_volume(
					VolumeId=volumeId,
					Size=size,
			)

		return node

	def gatherInstancesByNode(self, nodeTag):
		node = {}
		if "zones" in self.awsConf:
			for zone in self.awsConf["zones"]:
				ec2Client = boto3.client('ec2', region_name=zone[:-1])
				n = ec2Client.describe_instances(
					Filters = [
						{
							'Name':'tag:Node',
							'Values': [
								nodeTag,
							],
						},
						{
							'Name':'instance-state-name',
							'Values':[
								'pending',
								'running',
							],
						},
					],
				)
				if "Reservations" in node:
					if len(n["Reservations"]) > 0:
						node["Reservations"] += n["Reservations"]
				else:
					node = n

		else:
			try:
				ec2Client = boto3.client('ec2')
			except NoRegionError as e:
				print("Check out 'aws configure' or region", e)

			node = ec2Client.describe_instances(
				Filters = [
					{
						'Name':'tag:Node',
						'Values': [
							nodeTag,
						],
					},
					{
						'Name':'instance-state-name',
						'Values':[
							'pending',
							'running',
						],
					},
				],
			)

		return node

	def gatherInstancesByNodeType(self, nodeTypeTag):
		node = {}
		if "zones" in self.awsConf:
			for zone in self.awsConf["zones"]:
				ec2Client = boto3.client('ec2', region_name=zone[:-1])
				n = ec2Client.describe_instances(
					Filters = [
						{
							'Name':'tag:NodeType',
							'Values': [
								nodeTypeTag,
							],
						},
						{
							'Name':'instance-state-name',
							'Values':[
								'pending',
								'running',
							],
						},
					],
				)
				if "Reservations" in node:
					if len(n["Reservations"]) > 0:
						node["Reservations"] += n["Reservations"]
				else:
					node = n
		else:
			ec2Client = boto3.client('ec2')
			node = ec2Client.describe_instances(
				Filters = [
					{
						'Name':'tag:NodeType',
						'Values': [
							nodeTypeTag,
						],
					},
					{
						'Name':'instance-state-name',
						'Values':[
							'pending',
							'running',
						],
					},
				],
			)
		return node

	def gatherInstancesByType(self, userTag):
		node = {}
		if "zones" in self.awsConf:
			for zone in self.awsConf["zones"]:
				ec2Client = boto3.client('ec2', region_name=zone[:-1])
				n = ec2Client.describe_instances(
					Filters = [
						{
							'Name':'tag:Type',
							'Values': [
								userTag,
							],
						},
						{
							'Name':'instance-state-name',
							'Values':[
								'pending',
								'running',
							],
						},
					],
				)
				if "Reservations" in node:
					if len(n["Reservations"]) > 0:
						node["Reservations"] += n["Reservations"]
				else:
					node = n
		else:
			ec2Client = boto3.client('ec2')
			node = ec2Client.describe_instances(
				Filters = [
					{
						'Name':'tag:Type',
						'Values': [
							userTag,
						],
					},
					{
						'Name':'instance-state-name',
						'Values':[
							'pending',
							'running',
						],
					},
				],
			)

		return node

	def terminateNodeInstances(self):
		nodeType = self.nodeType
		userTag = self.userInfo["aws"]["tags"]["User"]
		nodeTypeTag, nodeTag, rawNodeTag = self.genTags(userTag, nodeType, 0)
		self.TerminateInstancesByNodeType(nodeTypeTag)

	def terminateNodeInstanceById(self, nodeIdx):
		nodeType = self.nodeType
		userTag = self.userInfo["aws"]["tags"]["User"]
		nodeTypeTag, nodeTag, rawNodeTag = self.genTags(userTag, nodeType, nodeIdx)
		self.TerminateInstancesByNode(nodeTag)

	def TerminateInstancesByNodeType(self, nodeTypeTag):
		filters = [
			{
				'Name': 'tag:NodeType',
				'Values': [
					nodeTypeTag,
				]
			},
			{
				'Name': 'instance-state-name',
				'Values': [
					'pending',
					'running',
					'stopping',
					'stopped'
				]
			}
		]
		commonStr = "Terminating instances by node type %s" % nodeTypeTag
		if "zones" in self.awsConf:
			for zone in self.awsConf["zones"]:
				print ("%s from zone %s..." % (commonStr, zone))
				self.TerminateInstancesByFilter(filters, region_name=zone[:-1])
		else:
			print (commonStr)
			self.TerminateInstancesByFilter(filters)

	def TerminateInstancesByNode(self, value):
		filters = [
			{
				'Name': 'tag:Node',
				'Values': [
					value,
				]
			},
			{
				'Name': 'instance-state-name',
				'Values': [
					'pending',
					'running',
					'stopping',
					'stopped'
				]
			}
		]
		commonStr = "Terminating instances by node tag %s..." % value
		if "zones" in self.awsConf:
			for zone in self.awsConf["zones"]:
				print ("%s from zone %s..." % (commonStr, zone))
				self.TerminateInstancesByFilter(filters, region_name=zone[:-1])
		else:
			print (commonStr)
			self.TerminateInstancesByFilter(filters)

	def TerminateInstancesByUserTag(self, userTag):
		filters = [
			{
				'Name': 'tag:User',
				'Values': [
					userTag,
				]
			},
			{
				'Name': 'instance-state-name',
				'Values': [
					'pending',
					'running',
					'stopping',
					'stopped'
				]
			}
		]
		commonStr = "Terminating instances by user tag %s..." % userTag
		if "zones" in self.awsConf:
			for zone in self.awsConf["zones"]:
				print ("%s from zone %s..." % (commonStr, zone))
				ec2Resource = boto3.resource('ec2', region_name=zone[:-1])
				ec2Resource.instances.filter(Filters=filters).terminate()
		else:
			print (commonStr)
			ec2Resource = boto3.resource('ec2')
			ec2Resource.instances.filter(Filters=filters).terminate()

	def TerminateInstancesByFilter(self, filters, region_name=""):
		ec2Resource = boto3.resource('ec2')
		if region_name != "":
			ec2Resource = boto3.resource('ec2', region_name=region_name)

		# get volumes before terminating ec2
		volumes = [volume for ec2 in ec2Resource.instances.filter(Filters=filters) for volume in ec2.volumes.all()]

		# terminate ec2
		ec2Resource.instances.filter(Filters=filters).terminate()

		# wait until ec2 terminate
		try:
			boto3.client('ec2').get_waiter('instance_terminated').wait(Filters=[filters[0]])
		except WaiterError as e:
			print("failed to wait for terminating ec2 :" + e)
			print("check for status of ", volumes)
			return

		# delete if volumes exist
		for volume in volumes:
			try:
				volume.describe_status()  # check if exists
				if len(volume.tags) == 0:
					volume.delete()
					print("deleting dangling volume : " + volume.id)
				else:
					print("volume with tags are not deleted : " + volume.id)
			except Exception:
				pass  # volume not exists

	def TerminateDynamoDBTable(self, config):
		for nodeIdx in range(self.awsConf["numNodes"]):
			self.TerminateDynamoDBTableById(nodeIdx, config)

	def TerminateDynamoDBTableById(self, nodeIdx, config):
		nodeType = self.nodeType
		userTag = self.userInfo["aws"]["tags"]["User"]
		_, tableName = GetTableName(config, nodeType, nodeIdx)

		DeleteDynamoDB().ByName(tableName, self.userInfo["aws"]["zone"][:-1], False)

	def stopNodeInstances(self):
		nodeType = self.nodeType
		userTag = self.userInfo["aws"]["tags"]["User"]
		nodeTypeTag, nodeTag, rawNodeTag = self.genTags(userTag, nodeType, 0)
		self.StopInstancesByNodeType(nodeTypeTag)

	def stopNodeInstanceById(self, nodeIdx):
		nodeType = self.nodeType
		userTag = self.userInfo["aws"]["tags"]["User"]
		nodeTypeTag, nodeTag, rawNodeTag = self.genTags(userTag, nodeType, nodeIdx)
		self.StopInstancesByNode(nodeTag)

	def StopInstancesByNodeType(self, nodeTypeTag):
		filters = [
			{
				'Name': 'tag:NodeType',
				'Values': [
					nodeTypeTag,
				]
			},
			{
				'Name': 'instance-state-name',
				'Values': [
					'pending',
					'running',
					'stopping',
					'stopped'
				]
			}
		]
		commonStr = "Stopping instances by node type %s..." % nodeTypeTag
		if "zones" in self.awsConf:
			for zone in self.awsConf["zones"]:
				print ("%s from zone %s..." % (commonStr, zone))
				ec2Resource = boto3.resource('ec2', region_name=zone[:-1])
				ec2Resource.instances.filter(Filters=filters).stop()
		else:
			print (commonStr)
			ec2Resource = boto3.resource('ec2')
			ec2Resource.instances.filter(Filters=filters).stop()

	def StopInstancesByNode(self, value):
		filters = [
			{
				'Name': 'tag:Node',
				'Values': [
					value,
				]
			},
			{
				'Name': 'instance-state-name',
				'Values': [
					'pending',
					'running',
					'stopping',
					'stopped'
				]
			}
		]
		commonStr = "Stopping instances by node tag %s..." % value
		if "zones" in self.awsConf:
			for zone in self.awsConf["zones"]:
				print ("%s from zone %s..." % (commonStr, zone))
				ec2Resource = boto3.resource('ec2', region_name=zone[:-1])
				ec2Resource.instances.filter(Filters=filters).stop()
		else:
			print (commonStr)
			ec2Resource = boto3.resource('ec2')
			ec2Resource.instances.filter(Filters=filters).stop()

	def StopInstancesByUserTag(self, userTag):
		filters = [
			{
				'Name': 'tag:User',
				'Values': [
					userTag,
				]
			},
			{
				'Name': 'instance-state-name',
				'Values': [
					'pending',
					'running',
					'stopping',
					'stopped'
				]
			}
		]
		commonStr = "Stopping instances by user tag %s..." % userTag
		if "zones" in self.awsConf:
			for zone in self.awsConf["zones"]:
				print ("%s from zone %s..." % (commonStr, zone))
				ec2Resource = boto3.resource('ec2', region_name=zone[:-1])
				ec2Resource.instances.filter(Filters=filters).stop()
		else:
			print (commonStr)
			ec2Resource = boto3.resource('ec2')
			ec2Resource.instances.filter(Filters=filters).stop()

	def startNodeInstances(self):
		nodeType = self.nodeType
		userTag = self.userInfo["aws"]["tags"]["User"]
		nodeTypeTag, nodeTag, rawNodeTag = self.genTags(userTag, nodeType, 0)
		self.StartInstancesByNodeType(nodeTypeTag)

	def startNodeInstanceById(self, nodeIdx):
		nodeType = self.nodeType
		userTag = self.userInfo["aws"]["tags"]["User"]
		nodeTypeTag, nodeTag, rawNodeTag = self.genTags(userTag, nodeType, nodeIdx)
		self.StartInstancesByNode(nodeTag)

	def updateAwsVolume(self, index, size, disableAws):
		if disableAws == True:
			return

		userTag = self.userInfo["aws"]["tags"]["User"]
		nodeType = self.nodeType
		nodeTypeTag, nodeTag, rawNodeTag = self.genTags(userTag, nodeType, index)
		response = self.gatherInstancesByNode(nodeTag)
		for reservation in response["Reservations"]:
			for instance in reservation["Instances"]:
				rawNode = ""
				for tag in instance['Tags']:
					if tag['Key'] == 'RawNode':
						rawNode = tag['Value']
				if rawNode != "":
					for blk in instance["BlockDeviceMappings"]:
						volumeId = blk['Ebs']['VolumeId']

		print ("volume id = %s" % volumeId)
		if disableAws == False:
			self.modifyVolume(volumeId, size)

	def updatePartition(self, index, size):
		deviceName = self.awsConf["storage"]["DeviceName"]

		print ("wait a moment that volume modification is being updated...")
		time.sleep(1)

		hosts = self.GetPublicIPAddressesById(index)
		response= self.executeWithReturn(hosts, "lsblk --exclude 7 --json --path")
		k = response.keys()[0]
		devInfo = json.loads(response[k])
		diskName = devInfo["blockdevices"][0]["name"]
		partName = devInfo["blockdevices"][0]["children"][0]["name"]

		changed = False
		while changed == False:
			print ("Trying to grow partition...")
			self.execute(hosts, "sudo growpart %s 1" % diskName)
			self.execute(hosts, "sudo resize2fs %s" % partName)
			response = self.executeWithReturn(hosts, "lsblk --exclude 7 --json --path")
			k = response.keys()[0]
			devInfo = json.loads(response[k])
			partSize = devInfo["blockdevices"][0]["children"][0]["size"]
			if partSize == ("%sG" % size):
				changed = True

	def StartInstancesByNodeType(self, nodeTypeTag):
		filters = [
			{
				'Name': 'tag:NodeType',
				'Values': [
					nodeTypeTag,
				]
			},
			{
				'Name': 'instance-state-name',
				'Values': [
					'pending',
					'running',
					'stopping',
					'stopped'
				]
			}
		]
		commonStr = "Starting instances by node type %s" % nodeTypeTag
		if "zones" in self.awsConf:
			for zone in self.awsConf["zones"]:
				print ("%s from zone %s..." % (commonStr, zone))
				ec2Resource = boto3.resource('ec2', region_name=zone[:-1])
				ec2Resource.instances.filter(Filters=filters).start()
		else:
			print (commonStr)
			ec2Resource = boto3.resource('ec2')
			ec2Resource.instances.filter(Filters=filters).start()

	def StartInstancesByNode(self, value):
		filters = [
			{
				'Name': 'tag:Node',
				'Values': [
					value,
				]
			},
			{
				'Name': 'instance-state-name',
				'Values': [
					'pending',
					'running',
					'stopping',
					'stopped'
				]
			}
		]
		commonStr = "Starting instances by node tag %s..." % value
		if "zones" in self.awsConf:
			for zone in self.awsConf["zones"]:
				print ("%s from zone %s..." % (commonStr, zone))
				ec2Resource = boto3.resource('ec2', region_name=zone[:-1])
				ec2Resource.instances.filter(Filters=filters).start()
		else:
			print (commonStr)
			ec2Resource = boto3.resource('ec2')
			ec2Resource.instances.filter(Filters=filters).start()


	def StartInstancesByUserTag(self, userTag):
		filters = [
			{
				'Name': 'tag:User',
				'Values': [
					userTag,
				]
			},
			{
				'Name': 'instance-state-name',
				'Values': [
					'pending',
					'running',
					'stopping',
					'stopped'
				]
			}
		]
		commonStr = "Starting instances by user tag %s..." % userTag
		if "zones" in self.awsConf:
			for zone in self.awsConf["zones"]:
				print ("%s from zone %s..." % (commonStr, zone))
				ec2Resource = boto3.resource('ec2', region_name=zone[:-1])
				ec2Resource.instances.filter(Filters=filters).start()
		else:
			print (commonStr)
			ec2Resource = boto3.resource('ec2')
			ec2Resource.instances.filter(Filters=filters).start()

	def genTags(self, userTag, nodeType, index):
		nodeTypeTag = "%s-%s" % (userTag, nodeType)
		nodeTag = "%s%d" % (nodeTypeTag, index)
		rawNodeTag = "%s%d" % (nodeType, index)
		return nodeTypeTag, nodeTag, rawNodeTag

	def checkIndex(self, nodeIdx):
		numNodes = self.awsConf["numNodes"]
		if nodeIdx < 0 or nodeIdx >= numNodes:
			raise Exception("nodeIdx should be in [%d, %d]" % (0, numNodes-1))

	def installIfNotExist(self, hosts, command):
		if len(hosts) == 0:
			return

		# if the library is already installed, skip the installation
		result = self.executeWithReturn(hosts, command)[hosts[0]].decode('utf-8')
		if "command not found" not in result and "No such file or directory" not in result:
			return

		# if the library is not installed, install the library.
		if "locust" in command:
			target_library = "locust"
			install_cmd = "sudo yum install python3-devel gcc -y > /dev/null \
			&& pip3 install --user web3 locust==1.2.3 > /dev/null"
		elif "prometheus" in command:
			target_library = "prometheus"
			install_cmd = "curl -s https://packagecloud.io/install/repositories/prometheus-rpm/release/script.rpm.sh | sudo bash > /dev/null \
			&& sudo yum install prometheus2 -y > /dev/null"
		elif "grafana" in command:
			target_library = "grafana"
			install_cmd = "wget -q https://dl.grafana.com/enterprise/release/grafana-enterprise-8.4.5-1.x86_64.rpm \
			&& sudo yum install initscripts urw-fonts grafana-enterprise-8.4.5-1.x86_64.rpm -y > /dev/null"

		print("%s: %s is not installed. Installing %s..." % (self.nodeType, target_library, target_library))
		self.execute(hosts, install_cmd)
		print("%s: Installing ended!" % self.nodeType)

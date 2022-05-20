#!/usr/bin/env python3

import json
import requests
import numpy
import datetime
import pymysql
from pytimeparse.timeparse import timeparse
from GrafanaInstanceManager import GrafanaInstanceManager
from KlaytnCommon import LoadConfig

class GrafanaCmd:
	def __init__(self, parsers):
		self.nodeType = "grafana"
		parser = parsers.add_parser(self.nodeType)
		subparsers = parser.add_subparsers(dest="grafanasubparser")

		p = subparsers.add_parser("create", help="Create a Grafana instance.")
		p.set_defaults(func=self.create)

		p = subparsers.add_parser("terminateInstances", help="Terminate the Grafana instance.")
		p.set_defaults(func=self.terminateInstances)

		p = subparsers.add_parser("stopInstances", help="Stop the Grafana instance.")
		p.set_defaults(func=self.stopInstances)

		p = subparsers.add_parser("startInstances", help="Start the Grafana instance.")
		p.set_defaults(func=self.startInstances)

		p = subparsers.add_parser("ssh", help="Connect to the grafana instance via ssh.")
		p.set_defaults(func=self.ssh)

		p = subparsers.add_parser("prepare", help="Prepare files to be uploaded to the Grafana instance.")
		p.set_defaults(func=self.prepare)

		p = subparsers.add_parser("upload", help="Upload files to the Grafana instance.")
		p.set_defaults(func=self.upload)

		p = subparsers.add_parser("download", help="Download files in download/%s* to appropriate instances.")
		p.set_defaults(func=self.download)
		p.add_argument("filename", type=str)

		p = subparsers.add_parser("init", help="Initialize the Grafana instance to get started.")
		p.set_defaults(func=self.init)

		p = subparsers.add_parser("start", help="Start the Grafana instance.")
		p.set_defaults(func=self.start)

		p = subparsers.add_parser("stop", help="Stop the Grafana instance.")
		p.set_defaults(func=self.stop)

		p = subparsers.add_parser("url", help="Print URL of the Grafana website.")
		p.set_defaults(func=self.url)

		p = subparsers.add_parser("upload-perf-test-result", help="Whether to upload performance test result to the designated place.")
		p.set_defaults(func=self.uploadPerfTestResult)

		p = subparsers.add_parser("upload-perf-test-result-path", help="AWS s3 path to upload performance test result.")
		p.set_defaults(func=self.uploadPerfTestResultPath)

		p = subparsers.add_parser("show-perf-test-result", help="Print the performance test result.")
		p.set_defaults(func=self.showPerfTestResult)

	def create(self, args):
		self.loadConfig(args.conf)
		node = GrafanaInstanceManager(self.config, self.config["userInfo"])
		node.CreateInstances()

	def terminateInstances(self, args):
		self.loadConfig(args.conf)
		node = GrafanaInstanceManager(self.config, self.config["userInfo"])
		node.TerminateInstances(self.config)

	def stopInstances(self, args):
		self.loadConfig(args.conf)
		node = GrafanaInstanceManager(self.config, self.config["userInfo"])
		node.StopInstances()

	def startInstances(self, args):
		self.loadConfig(args.conf)
		node = GrafanaInstanceManager(self.config, self.config["userInfo"])
		node.StartInstances()

	def ssh(self, args):
		self.loadConfig(args.conf)
		node = GrafanaInstanceManager(self.config, self.config["userInfo"])
		node.Ssh(0, "")

	def prepare(self, args):
		self.loadConfig(args.conf)
		node = GrafanaInstanceManager(self.config, self.config["userInfo"])
		node.Prepare()

	def upload(self, args):
		self.loadConfig(args.conf)
		node = GrafanaInstanceManager(self.config, self.config["userInfo"])
		node.Upload()

	def download(self, args):
		self.loadConfig(args.conf)
		node = GrafanaInstanceManager(self.config, self.config["userInfo"])
		node.Download(args.filename)

	def init(self, args):
		self.loadConfig(args.conf)
		node = GrafanaInstanceManager(self.config, self.config["userInfo"])
		node.Init()

	def start(self, args):
		self.loadConfig(args.conf)
		node = GrafanaInstanceManager(self.config, self.config["userInfo"])
		node.Start()

	def stop(self, args):
		self.loadConfig(args.conf)
		node = GrafanaInstanceManager(self.config, self.config["userInfo"])
		node.Stop()

	def url(self, args):
		self.loadConfig(args.conf)
		node = GrafanaInstanceManager(self.config, self.config["userInfo"])
		node.PrintUrl()

	def uploadPerfTestResult(self, args):
		jsonConf = LoadConfig(args.conf)
		if jsonConf["deploy"]["locustMaster"]["performanceTest"]["upload"]["enabled"]:
			print (1)
		else:
			print (0)

	def uploadPerfTestResultPath(self, args):
		jsonConf = LoadConfig(args.conf)
		print (jsonConf["deploy"]["locustMaster"]["performanceTest"]["upload"]["s3Path"])

	def showPerfTestResult(self, args):
		self.loadConfig(args.conf)
		node = GrafanaInstanceManager(self.config, self.config["userInfo"])

		# Get and print Prometheus HTTP API endpoint
		node_ip = node.GetPublicIPAddresses()
		prometheus= node_ip[0] + ":9090"
		print ("Prometheus HTTP API endpoint: "  + prometheus)

		# Get and print result collection start and end time
		now = datetime.datetime.utcnow()
		runtime = datetime.timedelta(seconds=timeparse(self.config["deploy"]["locustMaster"]["performanceTest"]["runTime"]))
		result_collection_time = datetime.timedelta(seconds=timeparse(self.config["deploy"]["locustMaster"]["performanceTest"]["resultCollectionTime"]))

		collection_start_delta = result_collection_time + (runtime - result_collection_time) / 2
		collection_end_delta   = (runtime - result_collection_time) / 2
		collection_start = (now - collection_start_delta).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
		collection_end   = (now - collection_end_delta).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

		print ("start time: " + collection_start)
		print ("end time:   " + collection_end)
		step="5s"

		uploadInfo = self.config["deploy"]["locustMaster"]["performanceTest"]["upload"]
		conn = pymysql.connect(host=uploadInfo["dbHost"], port=uploadInfo["dbPort"],
                        user=uploadInfo["dbUser"], passwd=uploadInfo["dbPassword"],
                        db=uploadInfo["db"], charset=uploadInfo["dbCharset"])

		try:
			with conn.cursor() as cursor:
						metrics = self.config["deploy"]["locustMaster"]["performanceTest"]["testResultMetrics"]
						test_gen_sql = 'INSERT INTO tests (date, aws_user_tag, aws_key_name) VALUES (NOW(), %s, %s)'
						cursor.execute(test_gen_sql, (self.config["userInfo"]["aws"]["tags"]["User"], self.config["userInfo"]["aws"]["keyName"]))
						conn.commit()
						test_id = cursor.lastrowid
						for metric in metrics:
							req = "http://%s/api/v1/query_range?query=%s&start=%s&end=%s&step=%s" % (prometheus, metric, collection_start, collection_end, step)
							request_result = requests.get(req)

							json_result=request_result.json()
							result=json_result["data"]["result"]

							for row in result:
								vals=[]
								for (first, last) in row["values"]:
										vals.append(float(last))

								instance = row["metric"]["instance"].split(":")[0]
								avg = str(numpy.mean(vals))
								std = str(numpy.std(vals))
								mx = str(numpy.max(vals))
								mn = str(numpy.min(vals))
								print (metric + ", " + instance + ", avg: " + str(avg) + ", std: " + str(std), ", max: " + str(mx) + ", min: " + str(mn))
								sql = 'INSERT INTO %s (node_type, avg, std, max, min, test_id) VALUES (\"%s\", %s, %s, %s, %s, %s)'
								sql = sql % (metric, instance, avg, std, mx, mn, test_id)
								cursor.execute(sql)
								conn.commit()

		finally:
				conn.close()


	################################################################################
	# Private functions
	################################################################################
	def checkNumNodes(self):
		if self.config["deploy"][self.nodeType]["aws"]["numNodes"] != 1:
			raise Exception("numNodes should be one!")

	def loadConfig(self, confFileName):
		self.config = LoadConfig(confFileName)
		self.checkNumNodes()

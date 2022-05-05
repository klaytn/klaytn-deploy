#!/usr/bin/env python3

import pprint
import boto3
from botocore.exceptions import ClientError
from KlaytnCommon import LoadConfig


# AWSDBCmd handles commands regarding to DynamoDB and S3
# GetDynamoDB, DeleteDynamoDB, GetS3, DeleteS3 inherits this class
class AWSDBCmd:
	def __init__(self, parsers):
		# DynamoDB
		parser = parsers.add_parser("dynamo", help="Execute functions related to AWS DynamoDB.")
		subparsers = parser.add_subparsers(dest="dynamo_subparser")

		p = subparsers.add_parser("get", help="List DynamoDB Tables with provided name or prefix")
		p.add_argument("--name", metavar="TABLE_NAME", type=str, default="",
							help="List DynamoDB Table with the given name")
		p.add_argument("--prefix", type=str, default="",
							help="List DynamoDB Tables that start with the given prefix")
		p.add_argument("--region", type=str, default="",
							help="AWS region where DynamoDB tables reside (e.g. ap-northeast-2)")
		p.set_defaults(func=GetDynamoDB().call)

		p = subparsers.add_parser("delete", help="Delete DynamoDB Table with provided name or prefix")
		p.add_argument("--name", metavar="TABLE_NAME", type=str, default="",
							help="Delete DynamoDB Table and S3 buckets with the given name")
		p.add_argument("--prefix", type=str, default="",
							help="Delete DynamoDB Tables and S3 buckets that start with the given prefix")
		p.add_argument("--region", type=str, default="",
							help="AWS region where DynamoDB tables reside (e.g. ap-northeast-2)")
		p.add_argument("--force", action="store_true",
							help="Remove DynamoDB without asking")
		p.set_defaults(func=DeleteDynamoDB().call)

		# S3
		parser = parsers.add_parser("s3", help="Execute functions related to AWS S3.")
		subparsers = parser.add_subparsers(dest="s3_subparser")

		p = subparsers.add_parser("get", help="List S3 Buckets with provided name or prefix")
		p.add_argument("--name", metavar="BUCKET_NAME", type=str, default="",
							help="List S3 bucket with the given name")
		p.add_argument("--prefix", type=str, default="",
							help="List S3 buckets that start with the given prefix")
		p.add_argument("--region", type=str, default="",
							help="AWS region where S3 buckets reside (e.g. ap-northeast-2)")
		p.set_defaults(func=GetS3().call)

		p = subparsers.add_parser("delete", help="Delete S3 Buckets with provided name or prefix")
		p.add_argument("--name", metavar="BUCKET_NAME", type=str, default="",
							help="Delete S3 bucket with the given name")
		p.add_argument("--prefix", type=str, default="",
							help="Delete S3 buckets that starts with the given prefix")
		p.add_argument("--region", type=str, default="",
							help="AWS region where S3 buckets reside (e.g. ap-northeast-2)")
		p.add_argument("--force", action="store_true",
							help="Remove S3 without asking")
		p.set_defaults(func=DeleteS3().call)

	def call(self, args):
		if (args.name == "" and args.prefix == "") or (args.name != "" and args.prefix != ""):
			print("only one of name or prefix should be provided")
			return

		region = LoadConfig(args.conf)["userInfo"]["aws"]["zone"][:-1]
		if args.region != "":
			region = args.region

		force = False
		if hasattr(args, "force"):
			force = args.force

		if args.name != "":
			self.ByName(args.name, region, force)
		else:
			self.ByPrefix(args.prefix, region, force)

	def ByName(self, name, region, force=False):
		print("wrong call")
		pass

	def ByPrefix(self, prefix, region, force=False):
		print("wrong call")
		pass

	def shouldProceed(self):
		yes = ["y", "Y", "yes", "Yes", "YES"]

		respond = raw_input("Do you want to proceed? [y/n] ")

		if respond in yes:
			return True
		return False

class GetDynamoDB(AWSDBCmd):
	def __init__(self):
		pass

	# Get DynamoDB table by name
	def ByName(self, name, region, force=False):
		client = boto3.client('dynamodb', region_name=region)
		try:
			pp = pprint.PrettyPrinter()
			pp.pprint(client.describe_table(TableName=name))
			print("https://%s.console.aws.amazon.com/dynamodb/home?region=ap-northeast-2#tables:selected=%s;tab=overview" % (region, name))
		except ClientError as e:
			print("Failed to get table by name")

	# Get DynamoDB tables by prefix
	def ByPrefix(self, prefix, region, force=False):
		db = boto3.resource('dynamodb', region_name=region)
		try:
			# get all table names
			tables = list(map(lambda dynamoObj: dynamoObj.name, list(db.tables.all())))
		except ClientError as e:
			print("failed to get tables by prefix")
			return

		resultTables = list(map(str, filter(lambda t: str(t).startswith(prefix), tables)))

		pp = pprint.PrettyPrinter()
		pp.pprint(resultTables)

		return resultTables

class DeleteDynamoDB(AWSDBCmd):
	def __init__(self):
		pass

	# Delete DynamoDB table by Name
	def ByName(self, name, region, force=False):
		client = boto3.client('dynamodb', region_name=region)

		# check if table exists
		try:
			client.describe_table(TableName=name)
		except ClientError as e:
			print("Failed to get table by name")
			return

		# ask before delete
		print(name)
		if not force and not self.shouldProceed():
			return

		# remove table
		try:
			print("deleting table: " + name)
			client.delete_table(TableName=name)
		except ClientError as e:
			print("Failed to remove table by name")

		# remove S3 bucket
		DeleteS3().ByName(name, region, force)

	# Delete DynamoDB tables by prefix
	def ByPrefix(self, prefix, region, force=False):
		tablesByPrefix = GetDynamoDB().ByPrefix(prefix, region, True)

		# ask before delete
		if not force and not self.shouldProceed():
			return

		# remove table
		for table in tablesByPrefix:
			self.ByName(table, region, True)

		# remove S3 bucket
		DeleteS3().ByPrefix(prefix, region, force)

class GetS3(AWSDBCmd):
	def __init__(self):
		pass

	# Get S3 bucket by Name
	def ByName(self, name, region, force=False):
		s3 = boto3.resource('s3', region_name=region)
		try:
			s3.meta.client.head_bucket(Bucket=name)
			pp = pprint.PrettyPrinter()
			pp.pprint(s3.Bucket(name).name)
		except ClientError as e:
			print("failed to get S3 bucket from name")

	# Get S3 buckets by prefix
	def ByPrefix(self, prefix, region, force=False):
		s3 = boto3.resource('s3', region_name=region)
		try:
			allS3 = list(map(lambda S3Obj: S3Obj.name, list(s3.buckets.all())))
			pass
		except ClientError as e:
			print("failed to get S3 bucket from prefix")
			return
		resultS3 = list(map(str, filter(lambda t: str(t).startswith(prefix), allS3)))

		pp = pprint.PrettyPrinter()
		pp.pprint(resultS3)

		return resultS3

class DeleteS3(AWSDBCmd):
	def __init__(self):
		pass

	# Delete S3 bucket by name
	def ByName(self, name, region, force=False):
		s3 = boto3.resource('s3', region_name=region)
		try:
			# check if exist
			s3.meta.client.head_bucket(Bucket=name)

			# ask before delete
			print(name)
			if not force and not self.shouldProceed():
				return

			# delete S3 bucket
			print("deleting bucket: " + name)
			bucket = s3.Bucket(name)
			for key in bucket.objects.all():
				key.delete()  # all keys should be deleted before deleting bucket
			bucket.delete()
		except ClientError as e:
			print("failed to delete S3 bucket from name")

	# Delete S3 buckets by prefix
	def ByPrefix(self, prefix, region, force=False):
		S3ByPrefix = GetS3().ByPrefix(prefix, region, True)

		# ask before delete
		if not force and not self.shouldProceed():
			return

		for bucket in S3ByPrefix:
			self.ByName(bucket, region, True)

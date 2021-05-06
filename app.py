#!/usr/bin/env python3

# MIT No Attribution
# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os

from aws_cdk import core as cdk

from aws_cdk import core

from enginframe_aurora_serverless.vpc import VpcStack
from enginframe_aurora_serverless.aurora_serverless import AuroraServerlessStack
from enginframe_aurora_serverless.efs import EfsStack
from enginframe_aurora_serverless.alb import AlbStack
from enginframe_aurora_serverless.enginframe import EnginFrameStack
from enginframe_aurora_serverless.fsx import FsxStack


CONFIG = {
    "ec2_type_enginframe": "t2.2xlarge",  # EnginFrame instance type
    # ARN of the secret that contains the efadmin password
    "arn_efadmin_password": "<arn_secret>",
    "key_name": "<key_name>",  # SSH key name that you already have in your account
    "ebs_engingframe_size": 50,  # EBS size for EnginFrame,
    "fsx_size": 1200,  # fsx scratch 2 size
    "jdbc_driver_link": "<jdbc_driver_link>", # You can find the download link here: https://dev.mysql.com/downloads/connector/j/ . You need to select the TAR Archive Platform indipended version.
    "pcluster_version": "2.10.3"  # Parallel Cluster version to install
}


env = core.Environment(
    account=os.environ.get("CDK_DEPLOY_ACCOUNT",
                           os.environ["CDK_DEFAULT_ACCOUNT"]),
    region=os.environ.get("CDK_DEPLOY_REGION",
                          os.environ["CDK_DEFAULT_REGION"])
)

app = core.App()
vpc_stack = VpcStack(app, "VPC", env=env)
aurora_stack = AuroraServerlessStack(
    app, "AuroraServerless", vpc=vpc_stack.vpc, env=env)
efs_stack = EfsStack(app, "EFS", vpc=vpc_stack.vpc, env=env)
fsx_stack = FsxStack(app, "FSX", vpc=vpc_stack.vpc, config=CONFIG, env=env)
alb_stack = AlbStack(app, "ALB", vpc=vpc_stack.vpc, env=env)
enginframe_stack = EnginFrameStack(app, "EnginFrame", vpc=vpc_stack.vpc, efs=efs_stack.file_system, aurora=aurora_stack.db,
                                   alb_security_group=alb_stack.alb_security_group,
                                   certificate=alb_stack.certificate, config=CONFIG, lb_enginframe=alb_stack.lb_enginframe, fsx1=fsx_stack.file_system_1, fsx2=fsx_stack.file_system_2, env=env)

app.synth()

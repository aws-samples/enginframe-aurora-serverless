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

from aws_cdk import core as cdk

from aws_cdk import core

from aws_cdk import (
    aws_ec2 as ec2,
    aws_efs as efs,
    core,
)


class EfsStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        security_group = ec2.SecurityGroup(
            self,
            id="SecurityGroup",
            vpc=vpc,
            description="EFS SG",
            allow_all_outbound=True
        )

        security_group.add_ingress_rule(ec2.Peer.ipv4(
            '10.0.0.0/16'), ec2.Port.tcp(2049), "allow nfs")

        self.file_system = efs.FileSystem(self, "EfsFileSystem",
                                          vpc=vpc,
                                          performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                                          file_system_name='EnginFrame Shared Storage',
                                          security_group=security_group,
                                          removal_policy=core.RemovalPolicy.DESTROY
                                          )

        core.CfnOutput(
            self,
            id="EfsID",
            value=self.file_system.file_system_id,
            description="ID of the file system",
            export_name=f"{self.region}:{self.account}:{self.stack_name}:efs-id"
        )

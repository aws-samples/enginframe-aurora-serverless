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
    aws_fsx as fsx,
    core,
)


class FsxStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, vpc, config, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        security_group = ec2.SecurityGroup(
            self,
            id="SecurityGroup",
            vpc=vpc,
            description="FSX SG",
            allow_all_outbound=True
        )

        security_group.add_ingress_rule(ec2.Peer.ipv4(
            '10.0.0.0/16'), ec2.Port.tcp(988), "Allows Lustre traffic")
        security_group.add_ingress_rule(ec2.Peer.ipv4(
            '10.0.0.0/16'), ec2.Port.tcp_range(1021, 1023), "Allows Lustre traffic")

        self.file_system_1 = fsx.LustreFileSystem(self, "FsxLustreFileSystem1",
                                                  lustre_configuration={
                                                      "deployment_type": fsx.LustreDeploymentType.SCRATCH_2},
                                                  storage_capacity_gib=config['fsx_size'],
                                                  removal_policy=core.RemovalPolicy.DESTROY,
                                                  vpc=vpc,
                                                  vpc_subnet=vpc.private_subnets[0],
                                                  security_group=security_group
                                                  )

        self.file_system_2 = fsx.LustreFileSystem(self, "FsxLustreFileSystem2",
                                                  lustre_configuration={
                                                      "deployment_type": fsx.LustreDeploymentType.SCRATCH_2},
                                                  storage_capacity_gib=config['fsx_size'],
                                                  removal_policy=core.RemovalPolicy.DESTROY,
                                                  vpc=vpc,
                                                  vpc_subnet=vpc.private_subnets[1],
                                                  security_group=security_group
                                                  )

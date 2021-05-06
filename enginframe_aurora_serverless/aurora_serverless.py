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
    aws_rds as rds,
    core,
)


class AuroraServerlessStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        subnet_group = rds.SubnetGroup(
            self,
            id="AuroraServerlessSubnetGroup",
            description='Aurora Serverless Subnet Group',
            subnet_group_name='auroraserverlesssubnetgroup',
            vpc=vpc)

        db_cluster_name = "aurora-serverless-db"

        security_group = ec2.SecurityGroup(
            self,
            id="SecurityGroup",
            vpc=vpc,
            description="Aurora SG",
            allow_all_outbound=True
        )

        security_group.add_ingress_rule(ec2.Peer.ipv4(
            vpc.vpc_cidr_block), ec2.Port.tcp(3306), "allow mysql")

        self.db = rds.ServerlessCluster(
            self,
            id="AuroraServerlessDB",
            vpc=vpc,
            engine=rds.DatabaseClusterEngine.AURORA_MYSQL,
            cluster_identifier=db_cluster_name,
            default_database_name="enginframedb",
            security_groups=[security_group],
            subnet_group=subnet_group,
            removal_policy=core.RemovalPolicy.DESTROY
        )

        self.db.node.add_dependency(subnet_group)
        self.db.node.add_dependency(security_group)

        core.CfnOutput(
            self,
            id="StackName",
            value=self.stack_name,
            description="Stack Name",
            export_name=f"{self.region}:{self.account}:{self.stack_name}:stack-name"
        )

        core.CfnOutput(
            self,
            id="DatabaseName",
            value="enginframedb",
            description="Database Name",
            export_name=f"{self.region}:{self.account}:{self.stack_name}:database-name"
        )

        core.CfnOutput(
            self,
            id="DatabaseClusterArn",
            value=self.db.cluster_arn,
            description="Database Cluster Arn",
            export_name=f"{self.region}:{self.account}:{self.stack_name}:database-cluster-arn"
        )

        core.CfnOutput(
            self,
            id="DatabaseSecretArn",
            value=self.db.secret.secret_arn,
            description="Database Secret Arn",
            export_name=f"{self.region}:{self.account}:{self.stack_name}:database-secret-arn"
        )

        core.CfnOutput(
            self,
            id="DatabaseClusterID",
            value=self.db.cluster_identifier,
            description="Database Cluster Id",
            export_name=f"{self.region}:{self.account}:{self.stack_name}:database-cluster-id"
        )

        core.CfnOutput(
            self,
            id="AuroraEndpointAddress",
            value=self.db.cluster_endpoint.hostname,
            description="Aurora Endpoint Address",
            export_name=f"{self.region}:{self.account}:{self.stack_name}:aurora-endpoint-address"
        )

        core.CfnOutput(
            self,
            id="DatabaseMasterUserName",
            value="admin",
            description="Database Master User Name",
            export_name=f"{self.region}:{self.account}:{self.stack_name}:database-master-username"
        )

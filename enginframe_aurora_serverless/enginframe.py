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
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_autoscaling as autoscaling,
    aws_autoscaling_hooktargets as hooktargets,
    aws_lambda as _lambda,
    aws_s3_assets as assets,
    core,
)

from aws_cdk.core import CustomResource


class EnginFrameStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str,
                 vpc, aurora, efs,
                 certificate, config, lb_enginframe, alb_security_group, fsx1, fsx2, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Copy the required files to S3
        post_install = assets.Asset(
            self, "PostInstall", path='scripts/post_install.sh')

        pcluster_config = assets.Asset(
            self, "PclusterConfig", path='scripts/pcluster.config')
            
        enginframe_batch_service = assets.Asset(
            self, "EFBatchService", path='scripts/batch_builtin_job_submission.xml')

        # Userdata of the instances
        data_enginframe = open("userdata/enginframe.sh", "rb").read()

        # Security groups
        ef_security_group = ec2.SecurityGroup(self, "EFSecurityGroup",
                                              vpc=vpc,
                                              description="SecurityGroup for EF ",
                                              security_group_name="EF SecurityGroup",
                                              allow_all_outbound=True,
                                              )

        ef_security_group.add_ingress_rule(
            alb_security_group, ec2.Port.tcp(8443), "allow http access from the vpc")

        ef_security_group.add_ingress_rule(
            ef_security_group, ec2.Port.all_traffic(), "allow local access ")

        pcluster_security_group = ec2.SecurityGroup(self, "PclusterSecurityGroup",
                                                    vpc=vpc,
                                                    description="SecurityGroup for Pcluster ",
                                                    security_group_name="Pcluster SecurityGroup",
                                                    allow_all_outbound=True,
                                                    )
        pcluster_security_group.add_ingress_rule(
            ef_security_group, ec2.Port.all_traffic(), "allow local access ")

        # Change some placeholders inside the userdata of the instances
        data_enginframe_format = str(data_enginframe, 'utf-8').format(arn_secret_password=config['arn_efadmin_password'],
                                                                      StackName=core.Aws.STACK_NAME,
                                                                      RegionName=core.Aws.REGION,
                                                                      key_name=config['key_name'],
                                                                      EFS_ID=efs.file_system_id,
                                                                      db_secret=aurora.secret.secret_arn,
                                                                      vpc_id=vpc.vpc_id,
                                                                      security_group_id=pcluster_security_group.security_group_id,
                                                                      jdbc_driver_link=config['jdbc_driver_link'],
                                                                      pcluster_version=config['pcluster_version'],
                                                                      post_install=post_install.s3_object_url,
                                                                      pcluster_config=pcluster_config.s3_object_url,
                                                                      enginframe_batch_service=enginframe_batch_service.s3_object_url,
                                                                      fsx1_dns_name=fsx1.dns_name,
                                                                      fsx2_dns_name=fsx2.dns_name,
                                                                      fsx1_mount_name=fsx1.mount_name,
                                                                      fsx2_mount_name=fsx2.mount_name)

        # Add the userdata to the instances
        enginframe_userdata = ec2.UserData.for_linux()
        enginframe_userdata.add_commands(data_enginframe_format)

        # Search for the latest AMIs for the instances
        linux_ami_enginframe = ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
                                                    edition=ec2.AmazonLinuxEdition.STANDARD,
                                                    virtualization=ec2.AmazonLinuxVirt.HVM,
                                                    storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
                                                    )
        # Instances Role
        role_ef = iam.Role(
            self, "EF_ROLE", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))
        # Allow console access with SSM
        role_ef.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name(
            "AmazonSSMManagedInstanceCore"))
        # Read information about FSx
        role_ef.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name(
            "AmazonFSxReadOnlyAccess"))

        # Allow to retrieve the efadmin password
        role_ef.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue"
                ],
                resources=[config['arn_efadmin_password'],
                           aurora.secret.secret_arn],
            )
        )
        # Allow to describe the instances
        role_ef.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:DescribeInstances"
                ],
                resources=["*"],
            )
        )

        # Policies required for ParallelCluster

        pcluster_policy_1 = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ec2:DescribeInstances",
                "ec2:DescribeKeyPairs",
                "ec2:DescribeRegions",
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribePlacementGroups",
                "ec2:DescribeImages",
                "ec2:DescribeInstances",
                "ec2:DescribeInstanceStatus",
                "ec2:DescribeInstanceTypes",
                "ec2:DescribeInstanceTypeOfferings",
                "ec2:DescribeSnapshots",
                "ec2:DescribeVolumes",
                "ec2:DescribeVpcAttribute",
                "ec2:DescribeAddresses",
                "ec2:CreateTags",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DescribeAvailabilityZones",
                "ec2:CreateVpc",
                "ec2:ModifyVpcAttribute",
                "ec2:DescribeNatGateways",
                "ec2:CreateNatGateway",
                "ec2:DescribeInternetGateways",
                "ec2:CreateInternetGateway",
                "ec2:AttachInternetGateway",
                "ec2:DescribeRouteTables",
                "ec2:CreateRoute",
                "ec2:CreateRouteTable",
                "ec2:AssociateRouteTable",
                "ec2:CreateSubnet",
                "ec2:ModifySubnetAttribute",
                "ec2:CreateVolume",
                "ec2:RunInstances",
                "ec2:AllocateAddress",
                "ec2:AssociateAddress",
                "ec2:AttachNetworkInterface",
                "ec2:AuthorizeSecurityGroupEgress",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:CreateNetworkInterface",
                "ec2:CreateSecurityGroup",
                "ec2:ModifyVolumeAttribute",
                "ec2:ModifyNetworkInterfaceAttribute",
                "ec2:DeleteNetworkInterface",
                "ec2:DeleteVolume",
                "ec2:TerminateInstances",
                "ec2:DeleteSecurityGroup",
                "ec2:DisassociateAddress",
                "ec2:RevokeSecurityGroupIngress",
                "ec2:RevokeSecurityGroupEgress",
                "ec2:ReleaseAddress",
                "ec2:CreatePlacementGroup",
                "ec2:DeletePlacementGroup",
                "autoscaling:DescribeAutoScalingGroups",
                "autoscaling:DescribeAutoScalingInstances",
                "autoscaling:CreateAutoScalingGroup",
                "ec2:CreateLaunchTemplate",
                "ec2:CreateLaunchTemplateVersion",
                "ec2:ModifyLaunchTemplate",
                "ec2:DeleteLaunchTemplate",
                "ec2:DescribeLaunchTemplates",
                "ec2:DescribeLaunchTemplateVersions",
                "autoscaling:PutNotificationConfiguration",
                "autoscaling:UpdateAutoScalingGroup",
                "autoscaling:PutScalingPolicy",
                "autoscaling:DescribeScalingActivities",
                "autoscaling:DeleteAutoScalingGroup",
                "autoscaling:DeletePolicy",
                "autoscaling:DisableMetricsCollection",
                "autoscaling:EnableMetricsCollection",
                "dynamodb:DescribeTable",
                "dynamodb:ListTagsOfResource",
                "dynamodb:CreateTable",
                "dynamodb:DeleteTable",
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:Query",
                "dynamodb:TagResource",
                "route53:ChangeResourceRecordSets",
                "route53:ChangeTagsForResource",
                "route53:CreateHostedZone",
                "route53:DeleteHostedZone",
                "route53:GetChange",
                "route53:GetHostedZone",
                "route53:ListResourceRecordSets",
                "route53:ListQueryLoggingConfigs",
                "sqs:GetQueueAttributes",
                "sqs:CreateQueue",
                "sqs:SetQueueAttributes",
                "sqs:DeleteQueue",
                "sqs:TagQueue",
                "sns:ListTopics",
                "sns:GetTopicAttributes",
                "sns:CreateTopic",
                "sns:Subscribe",
                "sns:Unsubscribe",
                "sns:DeleteTopic",
                "cloudformation:DescribeStackEvents",
                "cloudformation:DescribeStackResource",
                "cloudformation:DescribeStackResources",
                "cloudformation:DescribeStacks",
                "cloudformation:ListStacks",
                "cloudformation:GetTemplate",
                "cloudformation:CreateStack",
                "cloudformation:DeleteStack",
                "cloudformation:UpdateStack",
                "iam:AddRoleToInstanceProfile",
                "iam:RemoveRoleFromInstanceProfile",
                "iam:GetRolePolicy",
                "iam:GetPolicy",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:PutRolePolicy",
                "iam:DeleteRolePolicy",
                "elasticfilesystem:DescribeMountTargets",
                "elasticfilesystem:DescribeMountTargetSecurityGroups",
                "ec2:DescribeNetworkInterfaceAttribute",
                "ssm:GetParametersByPath",
                "fsx:*",
                "elasticfilesystem:*",
                "logs:DeleteLogGroup",
                "logs:PutRetentionPolicy",
                "logs:DescribeLogGroups",
                "logs:CreateLogGroup",
                "cloudwatch:PutDashboard",
                "cloudwatch:ListDashboards",
                "cloudwatch:DeleteDashboards",
                "cloudwatch:GetDashboard"

            ],
            resources=["*"],
        )

        pcluster_policy_2 = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:*"
            ],
            resources=["arn:aws:s3:::parallelcluster-*"],
        )

        pcluster_policy_3 = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:Get*",
                "s3:List*"
            ],
            resources=["arn:aws:s3:::"+core.Aws.REGION+"-aws-parallelcluster*",
                       "arn:aws:s3:::" + post_install.s3_bucket_name+"*",
                       "arn:aws:s3:::" + pcluster_config.s3_bucket_name+"*",
                       "arn:aws:s3:::" + enginframe_batch_service.s3_bucket_name+"*"],
        )

        pcluster_policy_4 = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "iam:PassRole",
                "iam:CreateRole",
                "iam:CreateServiceLinkedRole",
                "iam:DeleteRole",
                "iam:GetRole",
                "iam:TagRole",
                "iam:SimulatePrincipalPolicy"
            ],
            resources=["arn:aws:iam::"+core.Aws.ACCOUNT_ID+":role/parallelcluster-*",
                       "arn:aws:iam::"+core.Aws.ACCOUNT_ID+":role/aws-service-role/*"],
        )

        pcluster_policy_5 = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "iam:CreateInstanceProfile",
                "iam:DeleteInstanceProfile"
            ],
            resources=["arn:aws:iam::" +
                       core.Aws.ACCOUNT_ID+":instance-profile/*"],
        )

        pcluster_policy_6 = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "lambda:CreateFunction",
                "lambda:DeleteFunction",
                "lambda:GetFunctionConfiguration",
                "lambda:GetFunction",
                "lambda:InvokeFunction",
                "lambda:AddPermission",
                "lambda:RemovePermission"
            ],
            resources=["arn:aws:lambda:"+core.Aws.REGION+":"+core.Aws.ACCOUNT_ID+":function:parallelcluster-*",
                       "arn:aws:lambda:"+core.Aws.REGION+":"+core.Aws.ACCOUNT_ID+":function:pcluster-*"],
        )

        role_ef.add_to_policy(pcluster_policy_1)

        role_ef.add_to_policy(pcluster_policy_2)

        role_ef.add_to_policy(pcluster_policy_3)

        role_ef.add_to_policy(pcluster_policy_4)

        role_ef.add_to_policy(pcluster_policy_5)

        role_ef.add_to_policy(pcluster_policy_6)

        # ASG
        asg_enginframe = autoscaling.AutoScalingGroup(
            self,
            "ASG_EF",
            auto_scaling_group_name="ASG_EF",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE),
            instance_type=ec2.InstanceType(config['ec2_type_enginframe']),
            machine_image=linux_ami_enginframe,
            user_data=enginframe_userdata,
            role=role_ef,
            key_name=config['key_name'],
            desired_capacity=2,
            min_capacity=2,
            max_capacity=2,
            security_group=ef_security_group,
            signals=autoscaling.Signals.wait_for_count(
                2, timeout=core.Duration.minutes(30)),
            block_devices=[
                autoscaling.BlockDevice(
                    device_name="/dev/xvda",
                    volume=autoscaling.BlockDeviceVolume.ebs(
                        volume_type=autoscaling.EbsDeviceVolumeType.GP2,
                        volume_size=config['ebs_engingframe_size'],
                        delete_on_termination=True
                    )
                )]
        )

        # Lambda role
        lambda_role = iam.Role(
            self, id="LambdaRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"))

        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                    "logs:PutLogEvents"
                ],
                resources=["*"],
            )
        )

        lambda_role.add_to_policy(pcluster_policy_1)

        lambda_role.add_to_policy(pcluster_policy_2)

        lambda_role.add_to_policy(pcluster_policy_3)

        lambda_role.add_to_policy(pcluster_policy_4)

        lambda_role.add_to_policy(pcluster_policy_5)

        lambda_role.add_to_policy(pcluster_policy_6)

        # Lambda used to destroy the clusters
        lambda_destroy_pcluster = _lambda.Function(self, "lambda_destroy_pcluster",
                                                   runtime=_lambda.Runtime.PYTHON_3_7,
                                                   handler="destroy.lambda_handler",
                                                   code=_lambda.Code.asset(
                                                       "./lambda_destroy_pcluster"),
                                                   timeout=core.Duration.seconds(
                                                       600),
                                                   role=lambda_role)

        lambda_cs = CustomResource(
            self, "Resource1",
            service_token=lambda_destroy_pcluster.function_arn
        )

        asg_enginframe.node.add_dependency(lambda_role)
        asg_enginframe.node.add_dependency(lambda_destroy_pcluster)

        # ALB listener
        listener_enginframe = lb_enginframe.add_listener(
            "Listener", port=443, certificates=[certificate])
        listener_enginframe.add_targets(
            "Target", port=8443, stickiness_cookie_duration=core.Duration.days(1), targets=[asg_enginframe])
        listener_enginframe.connections.allow_default_port_from_any_ipv4(
            "Open to the world")

        core.CfnOutput(
            self,
            id="EnginFramePortalURL",
            value="https://"+lb_enginframe.load_balancer_dns_name,
            description="Load Balancer address",
        )

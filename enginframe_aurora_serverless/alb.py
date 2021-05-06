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
    aws_lambda as _lambda,
    custom_resources as cr,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_certificatemanager as acm,
    core,
)

from aws_cdk.core import CustomResource


class AlbStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ALB Security group
        self.alb_security_group = ec2.SecurityGroup(self, "ALBSecurityGroup",
                                                    vpc=vpc,
                                                    description="ALB SecurityGroup ",
                                                    security_group_name="ALB SecurityGroup",
                                                    allow_all_outbound=True,
                                                    )

        # Allow 443 access to the ALB
        self.alb_security_group.add_ingress_rule(ec2.Peer.ipv4(
            '0.0.0.0/0'), ec2.Port.tcp(443), "allow https access")

        # Create ALB
        self.lb_enginframe = elbv2.ApplicationLoadBalancer(
            self, "EFLB",
            vpc=vpc,
            internet_facing=True,
            security_group=self.alb_security_group)

        # Lambda role
        lambda_role = iam.Role(
            self, id="LambdaRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"))
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "acm:ImportCertificate",
                    "acm:ListCertificates",
                    "acm:DeleteCertificate",
                    "acm:DescribeCertificate",
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                    "logs:PutLogEvents"
                ],
                resources=["*"],
            )
        )

        # Lambda to create the ALB https certificate
        lambda_cert = _lambda.Function(self, "lambda_create_cert",
                                       runtime=_lambda.Runtime.PYTHON_3_7,
                                       handler="cert.lambda_handler",
                                       code=_lambda.Code.asset(
                                           "./lambda_cert"),
                                       timeout=core.Duration.seconds(600),
                                       role=lambda_role)

        lambda_cs = CustomResource(
            self, "Resource1",
            service_token=lambda_cert.function_arn,
            properties={
                "LoadBalancerDNSName": self.lb_enginframe.load_balancer_dns_name
            }
        )

        # Get the ACM certificate ARM from the lambda function
        certificate_arn = lambda_cs.get_att_string("ACMCertificateArn")
        self.certificate = acm.Certificate.from_certificate_arn(
            self, 'Certificate', certificate_arn)

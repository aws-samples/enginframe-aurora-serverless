Blog post link: https://aws.amazon.com/blogs/hpc/highly-available-hpc-infrastructure-on-aws

# HPC infrastructure with EnginFrame, AWS ParallelCluster, and Amazon Aurora

The solution proposed in this blog post is designed to simplify the process of setting up and running high performance computing applications on on-demand cluster on AWS cloud; it is deployed using the AWS Cloud Developer Kit (AWS CDK), a software development framework for defining cloud infrastructure in code and provisioning it through AWS CloudFormation, hiding the complexity of integration between the components.

The components includes:

[Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_AuroraOverview.html) is a fully managed relational database engine that's compatible with MySQL and PostgreSQL. Aurora can deliver up to five times the throughput of MySQL and up to three times the throughput of PostgreSQL without requiring changes to most of your existing applications. Aurora is used, in this solution, as the backend database for EnginFrame, in Serverless configuration.

[AWS ParallelCluster](https://docs.aws.amazon.com/parallelcluster) is an AWS-supported open source cluster management tool that makes it easy for you to deploy and manage HPC clusters on AWS. AWS ParallelCluster uses a simple text file to model and provision all the resources needed for your HPC applications in an automated and secure manner. It also supports a variety of job schedulers such as AWS Batch, SGE, Torque, and Slurm for easy job submissions.

[EnginFrame](https://download.enginframe.com) is a leading grid-enabled application portal for user-friendly submission, control, and monitoring of HPC jobs and interactive remote sessions. It includes sophisticated data management for all stages of HPC job lifetime and is integrated with most popular job schedulers and middle-ware tools to submit, monitor, and manage jobs. EnginFrame provides a modular system where new functionalities (e.g. application integrations, authentication sources, license monitoring, etc.) can be easily added. It also features a sophisticated web services interface, which can be leveraged to enhance existing applications in addition to developing custom solutions for your own environment.

[Amazon Elastic File System (Amazon EFS)](https://aws.amazon.com/efs) provides a simple, serverless, set-and-forget, elastic file system that lets you share file data without provisioning or managing storage. It can be used with AWS Cloud services and on-premises resources, and is built to scale on- demand to petabytes without disrupting applications. With Amazon EFS, you can grow and shrink your file systems automatically as you add and remove files, eliminating the need to provision and manage capacity to accommodate growth.

[Amazon FSx for Lustre](https://aws.amazon.com/fsx/lustre) is a fully managed service that provides cost-effective, high-performance, scalable storage for compute workloads. Many workloads, such as HPC, depend on compute instances accessing the same set of data through high-performance shared storage.

Creation of the default account password:

The EnginFrame default administrator account, named efadmin, requires a password. To improve the security of the solution, the password must be created by the user and saved in AWS Secrets Manager. The [AWS Secrets Manager tutorial](https://docs.aws.amazon.com/secretsmanager/latest/userguide/tutorials_basic.html) explains how to create your secret.The password must have letters, numbers, and one special character. The ARN of the created secret will be required in the next section.
This example command can be used to create the password from the AWS cli:
```
$ aws secretsmanager create-secret --name efadminPassword --description "EfadminPassword" --secret-string '{"efadminPassword":"test123456!"}' 
```

Inside the repo:

-	app.py contains the configuration variables used to deploy the environment. Before the deployment, you must customize it with the required configurations. <key_name> is your Amazon EC2 key pair. <arn_secret> is the ARN of the secret created in the previous step. 
-	The following additional parameters can also be configured accordingly to your requirements:
    -	ec2_type_enginframe: The EnginFrame instance type.
    -	ebs_engingframe_size: The Amazon Elastic Block Store (EBS) size for the EnginFrame instance.
    -	fsx_size: the size of the FSx for Lustre volume.
    -	jdbc_driver_link: the link used to download the MySQL JDBC driver. The MySQL Community Downloads contains the latest version. The required version is the TAR Archive Platform independent one.
-	pcluster_version: the AWS ParallelCluster version installed in the environment. The solution has been tested with the 2.10.3 version.
-	The enginframe_aurora_serverless directory contains the files of the classes used to deploy the required resources.
-	lambda/cert.py is the Lambda function used to create the Application Load Balancer certificate.
-	lambda_destroy_pcluster/destroy.py is the Lambda function used to destroy the AWS ParallelCluster clusters during the deletion of the stacks.
-	The user data directory contains the script used to configure the HPC environment.
-	scripts/pcluster.config is the AWS ParallelCluster configuration file.
-	scripts/post_install.sh is the AWS ParallelCluster post installation script.

The following commands can be used for the deployment:

```
$ python3 -m venv .venv
$ source .venv/bin/activate
$ python3 -m pip install -r requirements.txt
$ cdk bootstrap aws://<account>/<region>
$ cdk deploy VPC AuroraServerless EFS FSX ALB EnginFrame
```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

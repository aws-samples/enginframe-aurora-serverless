
# HPC infrastracture in high availability using EnginFrame, AWS ParallelCluster and Amazon Aurora Serverless

AWS provides the most elastic and scalable cloud infrastructure to run your HPC applications. With virtually unlimited capacity, engineers, researchers, and HPC system owners can innovate beyond the limitations of on-premises HPC infrastructure.

The engineers are no longer constrained to running their job on the available configuration. Every workload can run on its own on-demand cluster using an optimal set of services for their unique application. This removes the risk of on-premises HPC clusters becoming obsolete or poorly utilized as your needs change over time.

Find on this repo the steps to initialize CDK in your environment and to deploy the solution described on blog post <LINK>.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

The initialization process creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now test the availability of stacks with the command:

```
$ cdk ls
```

To deploy the solution hit the following:
```
$ cdk deploy VPC ALB AuroraServerless EFS FSX EnginFrame
```


## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation
 * `cdk destroy`     destroy the created stack(s)


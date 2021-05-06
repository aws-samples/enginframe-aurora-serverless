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

#Configure default region for the AWS cli
aws configure set region {RegionName} 

#Install required packages
yum install -y amazon-efs-utils nfs-utils jq java-1.8.0-openjdk.x86_64 curl wget python2-pip

#Install lustre client
amazon-linux-extras install -y lustre2.10

file_system_id="{EFS_ID}"
efs_mount_point="/efs"
mkdir -p $efs_mount_point

echo "$file_system_id:/ $efs_mount_point efs defaults,_netdev" >> /etc/fstab


mount -a


#find mac address of the interface
mac_addr=$(ip -o link | awk '$2 != "lo:" {{print $(NF-2)}}')
#find the subnet id of the instance
subnet_id=$(curl -s http://169.254.169.254/latest/meta-data/network/interfaces/macs/$mac_addr/subnet-id)



my_ip=$(ip -o -f inet address | awk '$2 != "lo" {{print $4}}' | awk -F'/' '{{print $1}}')
role_node_1=""
role_node_2=""
cluster_name_1=""
cluster_name_2=""
fsx1_dns_name=""
fsx2_dns_name=""
fsx1_id=""
fsx2_id=""
fsx1_mount_name=""
fsx2_mount_name=""


# Initialise the variables
if [ ! -f $efs_mount_point/node1 ]; then
    echo $my_ip > $efs_mount_point/node1
    role_node_1="node1"
    role_node_2="node2"
    cluster_name_1="cluster1"
    cluster_name_2="cluster2"
else
    echo $my_ip > $efs_mount_point/node2
    role_node_1="node2"
    role_node_2="node1"
    cluster_name_1="cluster2"
    cluster_name_2="cluster1"
fi
echo $cluster_name_1 > $efs_mount_point/$my_ip

#Check what is the local FSX volume
fsx1_dns_name=$(aws fsx describe-file-systems --query "FileSystems[?SubnetIds[0]=='$subnet_id'].DNSName" --output text)
fsx1_mount_name=$(aws fsx describe-file-systems --query "FileSystems[?SubnetIds[0]=='$subnet_id'].LustreConfiguration[].MountName" --output text)
fsx1_id=$(echo $fsx1_dns_name | awk -F'.' '{{print $1}}')

if [ $fsx1_dns_name == {fsx1_dns_name} ]; then
  fsx2_dns_name="{fsx2_dns_name}"
  fsx2_mount_name="{fsx2_mount_name}"
  fsx2_id=$(echo $fsx2_dns_name | awk -F'.' '{{print $1}}')
else
  fsx2_dns_name="{fsx1_dns_name}"
  fsx2_mount_name="{fsx1_mount_name}"
  fsx2_id=$(echo $fsx2_dns_name | awk -F'.' '{{print $1}}')
fi

mkdir -p /fsx_$cluster_name_1
mkdir -p /fsx_$cluster_name_2

#Mount FSX volumes
echo "$fsx1_dns_name@tcp:/$fsx1_mount_name /fsx_$cluster_name_1 lustre defaults,noatime,flock,_netdev 0 0" >> /etc/fstab
echo "$fsx2_dns_name@tcp:/$fsx2_mount_name /fsx_$cluster_name_2 lustre defaults,noatime,flock,_netdev 0 0" >> /etc/fstab
mount -a

export NICE_ROOT="$efs_mount_point/nice"


#Create the EnginFrame service user
adduser efnobody

#Retrieve the efadmin password from secret manager
ec2user_password=$(aws secretsmanager get-secret-value --secret-id {arn_secret_password} --query SecretString | jq -r 'fromjson | first(.[])')

#Configure the password for the efadmin user
printf "$ec2user_password" | passwd ec2-user --stdin


#Install AWS ParallelCluster
pip3 install aws-parallelcluster=={pcluster_version}

#Configure AWS ParallelCluster

amazon-linux-extras install epel -y
yum install munge -y
if [ $role_node_1 == "node1" ]; then
   # Generates munge key in /etc/munge/munge.key
   dd if=/dev/urandom bs=1 count=1024 > /etc/munge/munge.key
   # Enforce correct permission on the key
   chown munge: /etc/munge/munge.key
   chmod 0600 /etc/munge/munge.key
   cp /etc/munge/munge.key $efs_mount_point/.munge.key
else
   #Wait for the munge key
   while [ ! -f $efs_mount_point/.munge.key ]
    do
	  sleep 2 
	done
	#Copy the key to the correct location and set the permissions
    cp $efs_mount_point/.munge.key /etc/munge/munge.key
    chown munge: /etc/munge/munge.key
    chmod 0600 /etc/munge/munge.key
fi
systemctl enable munge
systemctl start munge


#create the pcluster config file
aws s3 cp {pcluster_config} /root/config

sed -i 's/@REGION@/{RegionName}/g' /root/config
sed -i 's/@KEY_NAME@/{key_name}/g' /root/config
sed -i 's|@POST_INSTALL@|{post_install}|g' /root/config
sed -i 's/@VPC_ID@/{vpc_id}/g' /root/config
sed -i "s/@SUBNET_ID@/$subnet_id/g" /root/config
sed -i 's/@SECURITY_GROUP@/{security_group_id}/g' /root/config
sed -i "s/@EFS_ID@/$file_system_id/g" /root/config
sed -i "s/@FSX_ID@/$fsx1_id/g" /root/config
sed -i "s|@FSX_PATH@|/fsx_$cluster_name_1|g" /root/config

# Create the cluster
/usr/local/bin/pcluster create -c /root/config $cluster_name_1
master_private_ip=$(/usr/local/bin/pcluster status -c /root/config $cluster_name_1 | awk '$1 == "MasterPrivateIP:" {{print $2}}')
master_hostname=$(echo "ip-$master_private_ip" | tr . -)
# Save the head node ip
echo "$master_private_ip" > $efs_mount_point/$cluster_name_1
mkdir /opt/slurm_tmp
mount -t nfs $master_private_ip:/opt/slurm /opt/slurm_tmp
cp -a /opt/slurm_tmp /opt/slurm
umount /opt/slurm_tmp
rmdir /opt/slurm_tmp

# Slurm configuration file of the local cluster
cat <<EOF > $efs_mount_point/$cluster_name_1.conf
SlurmctldHost=$master_hostname($master_private_ip)
ClusterName=parallelcluster
SlurmctldPort=6820-6829
SlurmdPort=6818
EOF


if [ $role_node_1 == "node1" ]; then

	#Download URL
	ef_download_url="https://dn3uclhgxk1jt.cloudfront.net/enginframe/packages/enginframe-latest.jar"

	wget "$ef_download_url"

	ef_jar=$(ls *.jar)

	#Java bin Path
	java_bin=$(readlink /etc/alternatives/java | sed 's/\/bin\/java//')

	#Hostname of the node
	ef_hostname=$(hostname -s)

	#Retrieve the db configuration
	db_secret=$(aws secretsmanager get-secret-value --secret-id {db_secret} --query SecretString )
	db_host=$(echo $db_secret | jq -r 'fromjson | ."host"')
	db_password=$(echo $db_secret | jq -r 'fromjson | ."password"')

	while [ ! -f $efs_mount_point/$role_node_2 ]
	do
	  sleep 2 
	done
	
	node_2_ip=$(cat $efs_mount_point/$role_node_2)

	#Create the file used for the EnginFrame unattended installation
	cat <<EOF > efinstall.config
efinstall.config.version = 1.0
ef.accept.eula = true
nice.root.dir.ui = $efs_mount_point/nice
kernel.java.home = $java_bin
ef.spooler.dir = $efs_mount_point/nice/enginframe/spoolers
ef.repository.dir = $efs_mount_point/nice/enginframe/repository
ef.sessions.dir = $efs_mount_point/nice/enginframe/sessions
ef.data.root.dir = $efs_mount_point/nice/enginframe/data
ef.logs.root.dir = $efs_mount_point/nice/enginframe/logs
ef.temp.root.dir = $efs_mount_point/nice/enginframe/tmp
ef.product = ENT
kernel.agent.rmi.port = 9999
kernel.agent.rmi.bind.port = 9998
kernel.ef.admin.user = ec2-user
kernel.server.tomcat.https = true
kernel.ef.tomcat.user = efnobody
kernel.ef.root.context = enginframe
kernel.tomcat.https.port = 8443
kernel.tomcat.shutdown.port = 8005
kernel.server.tomcat.https.ef.hostname = $ef_hostname
kernel.ef.db = other-db
kernel.ef.db.url = jdbc\:mysql\://$db_host\:3306/enginframedb
kernel.ef.db.admin.name = admin
kernel.ef.db.admin.password = $db_password
kernel.ef.enterprise.tcp.servers = $my_ip\:7800,$node_2_ip:7800
kernel.start_enginframe_at_boot = true
demo.install = true
default.auth.mgr = pam
pam.service = system-auth
pam.user = ec2-user
ef.jobmanager = slurm
slurm.binaries.path = /opt/slurm/bin
ef.delegate.dcvsm = false
intro-targets = component_enginframe,component_kernel,component_applets,component_parser,component_http,component_pam,component_ldap,component_activedirectory,component_rss,component_lsf,component_pbs,component_torque,component_sge,component_slurm,component_awsbatch,component_dcvsm,component_demo,component_neutro,component_vdi,component_applications,component_service-manager,component_user-group-manager,component_enginframe_finalizer,
progress-targets = cleanuptarget,
EOF

    # Install EnginFrame
    java -jar "$ef_jar" --text --batch
    
    # Required to download the files from EnginFrame
    echo "ef.download.server.url=https://localhost:8443/enginframe/download" >> $efs_mount_point/nice/enginframe/conf/enginframe/agent.conf

    # Configure Slurm clusters on EnginFrame
    cat <<EOF >>$efs_mount_point/nice/enginframe/conf/plugins/slurm/ef.slurm.conf
SLURM_CLUSTER_IDS="SLURM1,SLURM2"
# First Cluster
SLURM_CLUSTER_SLURM1_LABEL="$cluster_name_1"
SLURM_CLUSTER_SLURM1_CONF="$efs_mount_point/$cluster_name_1.conf"
# Second Cluster
SLURM_CLUSTER_SLURM2_LABEL="$cluster_name_2"
SLURM_CLUSTER_SLURM2_CONF="$efs_mount_point/$cluster_name_2.conf"
EOF

    # Copy the batch service
    aws s3 cp {enginframe_batch_service} $efs_mount_point/nice/enginframe/data/plugins/applications/services/published/batch/
    chown efnobody:efnobody $efs_mount_point/nice/enginframe/data/plugins/applications/services/published/batch/*.xml

    # Download the JDBC driver
	wget {jdbc_driver_link}
	tar zxvf mysql-connector-*
	# Copy the JDBC driver in the EnginFrame directory
	cp mysql-connector-java-*/mysql-connector-java-*.jar $efs_mount_point/nice/enginframe/202*/enginframe/WEBAPP/WEB-INF/lib/
	systemctl start enginframe
	touch $efs_mount_point/nice/ready

else

	while [ ! -f $efs_mount_point/nice/ready ]
	do
	  sleep 2 
	done
	
	# Create the EnginFrame systemd file
	cat <<EOF > /usr/lib/systemd/system/enginframe.service
[Unit]
Description=NICE EnginFrame (http://www.enginframe.com)
After=local-fs.target network.target remote-fs.target

# Uncomment following requirement in case needed, setting custom mount point
# to be checked
#RequiresMountsFor=<mount point for the EF filesystem>

[Service]
Type=forking
TimeoutStartSec=0
TimeoutStopSec=0
ExecStart=$efs_mount_point/nice/enginframe/bin/enginframe --conf $efs_mount_point/nice/enginframe/conf/enginframe.conf start
ExecStop=$efs_mount_point/nice/enginframe/bin/enginframe --conf $efs_mount_point/nice/enginframe/conf/enginframe.conf stop
Restart=on-failure
RestartSec=4s

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl start enginframe

fi


#Retrieve the InstanceID
MyInstID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

#Retrieve the logical ID of the resource
ASGLOGICALID=$(aws ec2 describe-instances --instance-ids $MyInstID --query "Reservations[].Instances[].Tags[?Key=='aws:cloudformation:logical-id'].Value" --output text)


pip install https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.tar.gz

#Send the signal to the Cloudformation Stack
/opt/aws/bin/cfn-signal -e $? --stack {StackName} --resource $ASGLOGICALID --region {RegionName}

import os
import json
import boto3

from botocore.exceptions import WaiterError


def lambda_handler(event, context):
    """
    Lambda function with AMI role to create, and terminate EC2 resources/
    """
    action = event["action"]
    
    if action.lower() == "terminate":
        instancesIds = event["ids"]
        return terminate_instances(instancesIds)
    elif action.lower() == "create":
        scale_out_factor = event["r"]
        return create_instances(scale_out_factor)
    elif action.lower() == "confirm_creation":
        instancesIds = event["ids"]
        return instances_created(instancesIds)
    elif action.lower() == "confirm_termination":
        instancesIds = event["ids"]
        return instances_terminated(instancesIds)
        

def create_instances(scale: int) -> dict:
    """
    Creates instances based on the scale specified by the user.
    The function doesn't wait for instances to be running, it
    returns their ids to check their status when the need
    arises.
    """
    # replacing the placeholder in the loadbalancer config file with the instances dns.
    user_data = """#!/bin/bash
                sudo sed -i "s/SERVER_NAME/$(ec2-metadata --public-hostname | awk '{print $2}')/" /etc/httpd/conf.d/apache.conf"""

    ec2 = boto3.resource('ec2', region_name='us-east-1')
    instances = ec2.create_instances(
        ImageId= os.getenv('IMAGE_ID'),
        InstanceType='t2.micro', 
        MinCount=scale, 
        MaxCount=scale,
        KeyName = os.getenv('KEY_NAME'),
        SecurityGroupIds=[os.getenv('SG_ID')],
        UserData=user_data
    )

    instances_ids = [i.id for i in instances]
    
    return {"instances_ids": instances_ids}
    

def instances_created(ids: list) -> dict:
    """
    Checks whether the instances are running based on their ids.
    """
    ec2_resource = boto3.resource('ec2', region_name='us-east-1')
    ec2 = boto3.client('ec2', region_name='us-east-1')
    instances_dns = []
    waiter = ec2.get_waiter('instance_status_ok')
    try:
        waiter.wait(
            InstanceIds=ids,
            WaiterConfig={
                'Delay': 1,
                'MaxAttempts': 1
            }
        )
    except WaiterError:
        return {"warm": False}

    for instance_id in ids:
        instance = ec2_resource.Instance(instance_id)
        instances_dns.append(instance.public_dns_name)
    return {
        "warm": True,
        "instances_dns": instances_dns,
    }


def terminate_instances(ids: list) -> dict:
    """
    Terminates instances based on their ids. The function doesn't wait
    for the instances to be terminated.
    """
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    ec2.instances.filter(InstanceIds = ids).terminate()
    
    return {"result": "ok"}
    
    
def instances_terminated(ids: list) -> dict:
    """
    Checks whether the instances are terminated based on their ids.
    """
    ec2 = boto3.client('ec2', region_name='us-east-1')
    waiter = ec2.get_waiter('instance_terminated')
    try:
        waiter.wait(
            InstanceIds=ids,
            WaiterConfig={
                'Delay': 1,
                'MaxAttempts': 1
            }
        )
    except WaiterError:
        return {"terminated": False}
    return {"terminated": True}
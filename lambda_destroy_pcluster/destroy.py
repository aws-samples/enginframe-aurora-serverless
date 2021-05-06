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


import boto3
import os
import subprocess
import time
import json
import logging
import urllib.request, urllib.parse

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

#function to send the response to the cloudformation stack
def send_response(event, context, response_status, response_data):
    '''Send a resource manipulation status response to CloudFormation'''
    response_body = json.dumps({
        "Status": response_status,
        "Reason": "See the details in CloudWatch Log Stream: " + context.log_stream_name,
        "PhysicalResourceId": context.log_stream_name,
        "StackId": event['StackId'],
        "RequestId": event['RequestId'],
        "LogicalResourceId": event['LogicalResourceId'],
        "Data": response_data
    })
    
    response_body_bytes = response_body.encode('utf-8')

    LOGGER.info('ResponseURL: %s', event['ResponseURL'])
    LOGGER.info('ResponseBody: %s', response_body)

    opener = urllib.request.build_opener(urllib.request.HTTPHandler)
    request = urllib.request.Request(event['ResponseURL'], data=response_body_bytes)
    request.add_header('Content-Type', 'application/json; charset=utf-8')
    request.add_header('Content-Length', len(response_body_bytes))
    request.get_method = lambda: 'PUT'
    response = opener.open(request)
    LOGGER.info("Status code: %s", response.getcode())
    LOGGER.info("Status message: %s", response.msg)
    
    

def lambda_handler(event, context):
    output = {}
    #Create the cloudformation client
    client_cloudformation = boto3.client('cloudformation')
    #Section related to the creation of the stack
    if event['RequestType'] == 'Create':
      send_response(event, context, "SUCCESS", output)
    #Section related to the deletion of the stack
    elif event['RequestType'] == 'Delete':
      #delete the stacks
      try:
        client_cloudformation.delete_stack(StackName='parallelcluster-cluster1')
        client_cloudformation.delete_stack(StackName='parallelcluster-cluster2')
        LOGGER.info('Deleting stacks')
        send_response(event, context, "SUCCESS", output)
      except Exception as e:
        LOGGER.info('Error: %s', e)
        send_response(event, context, "FAILED", output)
      
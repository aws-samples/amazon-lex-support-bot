from botocore.vendored import requests
from awscli.clidriver import create_clidriver
import boto3
import json
import logging
import os
from boto3.session import Session
import time
import chatbot_utils

SUCCESS = "SUCCESS"
FAILED = "FAILED"
session = Session()
region_name = session.region_name
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

if 'LOG_LEVEL' in os.environ:
    if os.environ['LOG_LEVEL'] == 'DEBUG':
        logger.setLevel(logging.DEBUG)
    if os.environ['LOG_LEVEL'] == 'INFO':
        logger.setLevel(logging.INFO)
    if os.environ['LOG_LEVEL'] == 'WARNING':
        logger.setLevel(logging.WARNING)

region = os.environ['AWS_DEFAULT_REGION']

lex_client = boto3.client('lex-models')

s3_service = boto3.client('s3')


def lambda_handler(event, context):
    response_data = {}

    bot_name = ""
    try:
        logger.debug("Received event: %s", json.dumps(event))
        logger.debug("Event type: %s", event['RequestType'])

        logger.info(event)
        if event['RequestType'] in ['Create', 'Update']:
            if not valid_properties(event, context, ['BucketName', 'LexJsonKey', 'FulfillmentLambdaArn',
                                                     'LexResourcesPrefix','CognitoPoolId','SourceBucket','SourceKey','DestinationBucket','DestinationKey']):
                raise RuntimeError("Missing one of the custom lambda properties..")
            bot_response = create_bot(event)
            bot_name = bot_response['bot_name']
            event['ResourceProperties']['BotName'] = bot_name
            is_processed = copy_webui_code(event)
            if not is_processed:
                raise RuntimeError("Failed To Copy WebUI code")
            if not bot_response['status']:
                logger.debug("bot_response is not status - failing:%s",bot_response)
                response_data['Message'] = "Bot creation failed"
                send(event, context, FAILED, response_data, bot_name)
            else:
                response_data['Message'] = "Bot creation successful"
                response_data['BotName'] = bot_name
                send(event, context, SUCCESS, response_data, bot_name)

        elif event['RequestType'] == 'Delete':
            bot_name = event['PhysicalResourceId']
            response_data['BotName'] = bot_name
            try:
                get_bot_response = lex_client.get_bot(name=bot_name, versionOrAlias='$LATEST')

            except lex_client.exceptions.NotFoundException as ex:
                logger.info("Bot not found, nothing to delete... returning")
                send(event, context, SUCCESS, response_data, bot_name)
                return
            except Exception as ex:
                logger.info("Exception during get bot, failed to delete..." + str(ex))
                send(event, context, SUCCESS, response_data, bot_name)
                return
            delete_bot_response = delete_bot(bot_name)
            is_processed = delete_webui_code(event)
            if not is_processed:
                raise RuntimeError("Failed Delete WebUI code")
            if delete_bot_response:
                status = SUCCESS
                response_data['Message'] = 'Successfully deleted lex bot'
            else:
                status = FAILED
                response_data['Message'] = 'Error deleting lex bot'

            send(event, context, status, response_data, bot_name)
    except Exception as e:
        response_data['Message'] = "Unexpected error: " + str(type(e)) + ": " + str(e.args)
        print(response_data['Message'])
        send(event, context, FAILED, response_data, bot_name)

    return


# Delete Webui code
def delete_webui_code(event):
    is_processed = True
    try:
        logger.info('started deleting s3 data')
        source_code_bucket = event['ResourceProperties']['DestinationBucket']
        s3_resource = boto3.resource('s3')
        bucket = s3_resource.Bucket(source_code_bucket)
        bucket.object_versions.all().delete()
    except Exception as ex:
        logger.error('Exception while trying to delete webui code'+str(ex))
        is_processed = False
    return is_processed


def upload_statichost_config(bot_name,region_name,pool_id,bucket_name,destinationBucketPermission):
    is_processed = False
    try:
        data = {"botAlias": "$LATEST", "botName": bot_name, "region": region_name, "poolId": pool_id}
        response = s3_service.put_object(Body=json.dumps(data), Bucket=bucket_name, Key='config.json',ACL=destinationBucketPermission)
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            is_processed = True
    except Exception as ex:
        logger.error('Exception while trying to upload static hosting config file'+str(ex))
    return is_processed

def upload_lex_ui_load_config(bot_name,region_name,pool_id,bucket_name,destinationBucketPermission):
    is_processed = False
    try:
        data = {"botAlias": "$LATEST", "botName": bot_name, "region": region_name, "poolId": pool_id}

        data = {"cognito": { "poolId": pool_id, "region": region_name }, "lex": { "botName": bot_name, "botAlias": "$LATEST" }, "ui": { "toolbarTitle": bot_name, "enable_login": False, "helpIntent": "help" }, "polly": { "voiceId": "sally"}, "recorder": { "preset": "speech_recognition"}, "region": region_name }
        response = s3_service.put_object(Body=json.dumps(data), Bucket=bucket_name, Key='lex-web-ui-loader-config.json',ACL=destinationBucketPermission)
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            is_processed = True
    except Exception as ex:
        logger.error('Exception while trying to upload static hosting config file'+str(ex))
    return is_processed

def upload_lex_mobile_config(bot_name,region_name,pool_id,bucket_name,destinationBucketPermission):
    is_processed = False
    try:
        constVal = {"botAlias": "$LATEST", "botName": bot_name, "region": region_name, "poolId": pool_id, "description": "Service Support Bot", "bot-template":"", "commands-help" : ["I have a problem", "help me", "my computer is not working"]}
        data = "const aws_bots_config = '["+json.dumps(constVal)+"]';\n"
        data = data + "const aws_cognito_identity_pool_id = '"+pool_id+"';\n"
        data = data + "const aws_cognito_region = '"+region_name+"';\n"

        response = s3_service.put_object(Body=data, Bucket=bucket_name, Key='aws-config.js',ACL=destinationBucketPermission)
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            is_processed = True
    except Exception as ex:
        logger.error('Exception while trying to upload static hosting config file'+str(ex))
    return is_processed

# Copy webui code
def copy_webui_code(event):
    is_processed = True
    try:
        logger.info('started processing s3 data event: '+str(event))
        driver = create_clidriver()
        destinationBucketPermission = event['ResourceProperties']['DestinationBucketPermission']
        copy_command = 's3 cp s3://{source_path}    s3://{destination_path} --recursive --acl {destinationBucketPermission}'
        source_bucket = event['ResourceProperties']['SourceBucket']
        destination_bucket = event['ResourceProperties']['DestinationBucket']
        if not source_bucket.endswith('/'):
            source_bucket = source_bucket + '/'
        if not destination_bucket.endswith('/'):
            destination_bucket = destination_bucket + '/'
        source_path = source_bucket + event['ResourceProperties']['SourceKey']
        destination_path = destination_bucket + event['ResourceProperties']['DestinationKey']
        logger.info('started copy s3 data: source path:%s destination_path:%s',source_path,destination_path)
        formatted_copy_command = copy_command.format(source_path=source_path, destination_path=destination_path, destinationBucketPermission=destinationBucketPermission)
        logger.info('formatted copy command:%s',formatted_copy_command)
        driver.main(formatted_copy_command.split())

        #Fix for index.html content-type
        index_copy_command = 's3 cp s3://{source_path}/index.html s3://{destination_path} --acl {destinationBucketPermission} --metadata-directive REPLACE --content-type text/html'
        formatted_index_copy_command = index_copy_command.format(source_path=source_path, destination_path=destination_path, destinationBucketPermission=destinationBucketPermission)
        logger.info('formatted index copy command:%s',formatted_index_copy_command)
        driver.main(formatted_index_copy_command.split())
        bot_name = event['ResourceProperties']['BotName']
        pool_id = event['ResourceProperties']['CognitoPoolId']
        static_host_bucket = event['ResourceProperties']['DestinationBucket']
        logger.info('upload statichost_config:%s %s %s %s %s',bot_name,region_name,pool_id,static_host_bucket,destinationBucketPermission)
        is_processed = upload_statichost_config(bot_name, region_name, pool_id, static_host_bucket, destinationBucketPermission)
        is_processed = upload_lex_ui_load_config(bot_name, region_name, pool_id, static_host_bucket, destinationBucketPermission)
        is_processed = upload_lex_mobile_config(bot_name, region_name, pool_id, static_host_bucket, destinationBucketPermission)
        logger.info('completed  s3 data processing ')
    except Exception as e:
        logger.error('Failed to copy static web hosting source code'+str(e))
        is_processed = False
    return is_processed

# Create lex bot
def create_bot(event):
    try:
        logger.debug("Creating bot")
        lex_prefix = event['ResourceProperties']['LexResourcesPrefix']
        if lex_prefix and not lex_prefix.endswith('_'):
           lex_prefix = lex_prefix + '_'
        else:
            lex_prefix = ''
        s3 = boto3.resource('s3')
        bucket_name = event['ResourceProperties']['BucketName']
        lex_json_key = event['ResourceProperties']['LexJsonKey']
        fulfillment_lambda_arn = event['ResourceProperties']['FulfillmentLambdaArn']
        fulfillment_lambda_arn2 = event['ResourceProperties']['FulfillmentLambdaArn2']
        fulfillment_lambda_arn3 = event['ResourceProperties']['FulfillmentLambdaArn3']
        fulfillment_lambda_arn4 = event['ResourceProperties']['FulfillmentLambdaArn4']
        fulfillment_lambda_arn5 = event['ResourceProperties']['FulfillmentLambdaArn5']
        fulfillment_lambda_arn6 = event['ResourceProperties']['FulfillmentLambdaArn6']
        fulfillment_lambda_arn7 = event['ResourceProperties']['FulfillmentLambdaArn7']
        bucket = s3.Bucket(bucket_name)
        lex_json_obj = bucket.Object(lex_json_key)
        lex_json = json.loads(lex_json_obj.get()["Body"].read().decode('utf-8'))
        new_lex_json = lex_json.copy()
        logger.debug("processing intents")
        for intent in new_lex_json['resource']['intents']:
            fulfillmentActivityType = intent['fulfillmentActivity']['type']
            logger.debug("intent structure:%s",intent)
            intentName = intent['name']
            if fulfillmentActivityType == 'CodeHook' and intentName.endswith('Check_Ticket_Status'):
                intent['fulfillmentActivity']['codeHook']['uri'] = fulfillment_lambda_arn
            if fulfillmentActivityType == 'CodeHook' and intentName.endswith('Hello_Intent'):
                intent['fulfillmentActivity']['codeHook']['uri'] = fulfillment_lambda_arn2
            if fulfillmentActivityType == 'CodeHook' and intentName.endswith('Manage_Ticket'):
                intent['fulfillmentActivity']['codeHook']['uri'] = fulfillment_lambda_arn3
            if fulfillmentActivityType == 'CodeHook' and intentName.endswith('Open_Support_Case'):
                intent['fulfillmentActivity']['codeHook']['uri'] = fulfillment_lambda_arn5
            if fulfillmentActivityType == 'CodeHook' and intentName.endswith('Thank_you_Intent'):
                intent['fulfillmentActivity']['codeHook']['uri'] = fulfillment_lambda_arn6
            if fulfillmentActivityType == 'CodeHook' and intentName.endswith('FallbackIntent'):
                intent['fulfillmentActivity']['codeHook']['uri'] = fulfillment_lambda_arn7

        logger.debug("Importing chat bot %s",new_lex_json)
        bot_response = chatbot_utils.import_bot(new_lex_json, lex_prefix)
        return bot_response
    except Exception as ex:
        logger.error("Exception while trying to create Lex Bot : " + str(ex))
        return None

def delete_bot(lex_bot_name):
    logger.debug("Deleting lex Bot")
    try:
        get_bot_alias_response = lex_client.get_bot_aliases(botName=lex_bot_name)
        for bot_alias in get_bot_alias_response['BotAliases']:
            lex_client.delete_bot_alias(name=bot_alias['name'], botName=lex_bot_name)
            logger.info('Deleted bot version ' + bot_alias['name'] + ' of bot : ' + lex_bot_name)

        lex_client.delete_bot(
            name=lex_bot_name
        )

    except lex_client.exceptions.ConflictException as e:
        time.sleep(10)
        lex_client.delete_bot(name=lex_bot_name)
    except Exception as e:
        logger.error("Exception while trying to delete bot :: "+str(e))
        return False

    return True

def valid_properties(event, context, mandatory_property_names):
    """Validate the event structure"""
    missing_property_names = []
    response_data = {}
    if not 'ResourceProperties' in event:
        response_data['Message'] = "Malformed CloudFormation request, missing ResourceProperties"
        send(event, context, FAILED, response_data, None)
        return False
    for mandatory_property_name in mandatory_property_names:
        if not mandatory_property_name in event['ResourceProperties']:
            missing_property_names.append(mandatory_property_name)
    if len(missing_property_names) > 0:
        response_data['Message'] = "Missing one or more required properties: {0}".format(missing_property_names)
        send(event, context, FAILED, response_data, None)
        return False
    return True


def send(event, context, response_status, response_data, physical_resource_id):
    responseUrl = event['ResponseURL']
    logger.debug("CF Response URL: " + responseUrl)
    response_body = {}
    response_body['Status'] = response_status
    if response_status == FAILED:
        response_body['Reason'] = response_data['Message']
    else:
        response_body['Reason'] = "completed"
    response_body['PhysicalResourceId'] = physical_resource_id or context.log_stream_name
    response_body['StackId'] = event['StackId']
    response_body['RequestId'] = event['RequestId']
    response_body['LogicalResourceId'] = event['LogicalResourceId']
    response_body['Data'] = response_data
    json_response_body = json.dumps(response_body)
    logger.info("CF Response Body: %s", json.dumps(json_response_body))
    headers = {
        'content-type': '',
        'content-length': str(len(json_response_body))
    }

    try:
        response = requests.put(responseUrl,
                                data=json_response_body,
                                headers=headers)
        logger.info("CF Status code: %s ", response.reason)
    except Exception as e:
        logger.error("send(..) failed executing requests.put(..): %s", str(e))



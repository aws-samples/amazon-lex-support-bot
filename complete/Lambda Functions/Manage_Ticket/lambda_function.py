"""
This Lambda shows how a staff member managing SupportBot would update the status of a given ticket.
"""

import json
import datetime
import time
import os
import dateutil.parser
import logging
import uuid
import boto3
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# --- Main handler ---

def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
        
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    logger.debug('event={}'.format(event))
    
    session_attributes = event['sessionAttributes']
    
    if session_attributes is None:
        session_attributes = {}
    
        
    session_attributes['lastIntent'] = event['currentIntent']['name']
#    session_attributes['submitterName'] = event['currentIntent']['slots']['first_name']
    

    
    #before closing the intent, save the case info to a database table
    record = getFromDB(event['currentIntent']['slots'])
    slots = event['currentIntent']['slots']
    if record is None:
        response_string = "We were unable to locate support case "+ event['currentIntent']['slots']['ticket_id'] + " please your your case id and try again."    
    else:
        updateStatus(slots['ticket_id'],slots['status'])
        response_string = 'We have found and updated your support case. The status is now '+ slots['status'] + ' and was last updated '+ time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(record['LastUpdatedDate'])))    
        
    return close(session_attributes, 'Fulfilled', {'contentType': 'PlainText','content': response_string})


def getFromDB(slots):

    dynamodb = boto3.resource('dynamodb')
    db_table_name = os.environ['DynamoDB_Table_Name']
    table = dynamodb.Table(db_table_name)
    
    logger.debug("looking up key CaseId="+slots['ticket_id'])
   
    response = table.query(KeyConditionExpression=Key('CaseId').eq(slots['ticket_id']))
    logger.debug(str(response)) 

    
    return response['Items'][0]
    
def updateStatus(ticketId,updatedStatus):
    logger.debug("changing status to="+updatedStatus)
    dynamodb = boto3.resource('dynamodb')
    db_table_name = os.environ['DynamoDB_Table_Name']
    table = dynamodb.Table(db_table_name)
    response = table.update_item(
    Key={
        'CaseId': ticketId,
    },
    UpdateExpression="set #st = :r, LastUpdatedDate = :l",
    ExpressionAttributeValues={
        ':r':updatedStatus,
        ':l':str(time.time())
    },
    ExpressionAttributeNames={
        '#st':'Status'
    },
    ReturnValues="UPDATED_NEW")
    
    logger.debug('finished changing status to='+updatedStatus)

    
    
def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }
    
    logger.debug('<<SupportBot>> "Lambda fulfillment function response = \n' + str(response)) 

    return response
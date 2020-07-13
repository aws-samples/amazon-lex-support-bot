"""
This is the completed Lambda function for the Check_Ticket_Status intent. Follow the README.md for a guide
on how to code this, or if you are stuck, check the complete/Lambda Functions/ directory for the completed code.
When complete a user will be able to look up their ticket status with a given ticket ID.
"""

import json
import dateutil.parser
import logging
import os
import time
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
    

    #before closing the intent, save the case info to a database table
    record = getFromDB(event['currentIntent']['slots'])
    

    if record is None:
        response_string = "We were unable to locate support case "+ event['currentIntent']['slots']['ticket_id'] + " please your your case id and try again."    
    else:
        response_string = 'We have found your support case. The status is '+ record['Status'] + ' and was last updated '+ time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(record['LastUpdatedDate'])))    
        session_attributes['submitterName'] = record['Requester First Name']
        
    return close(session_attributes, 'Fulfilled', {'contentType': 'PlainText','content': response_string})


def getFromDB(slots):

    dynamodb = boto3.resource('dynamodb')
    db_table_name = os.environ['DynamoDB_Table_Name']
    table = dynamodb.Table(db_table_name)
    
    logger.debug("looking up key CaseId="+slots['ticket_id'])
    response = table.query(KeyConditionExpression=Key('CaseId').eq(slots['ticket_id']))
    
    logger.debug(str(response)) 
    
    return response['Items'][0]
    

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

"""
This is a complete Lambda function for the Open_Support_Ticket intent. Follow the README.md for a guide
on how to code this, or if you are stuck look here.

"""

import json
import datetime
import time
import os
import dateutil.parser
import logging
import uuid
import boto3
from random import seed
from random import randint

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
    session_attributes['submitterName'] = event['currentIntent']['slots']['first_name']



    #before closing the intent, save the case info to a database table
    item = save_to_db(event['currentIntent']['slots'])

    response_string = 'We will file a case about ' + event['currentIntent']['slots']['problem_title'] + ' your case ID is '+item['CaseId'] + '. You can say check on my case and your case ID to see its status.'
    return close(session_attributes, 'Fulfilled', {'contentType': 'PlainText','content': response_string})


def save_to_db(slots):

    dynamodb = boto3.resource('dynamodb')
    db_table_name = os.environ['DynamoDB_Table_Name']
    table = dynamodb.Table(db_table_name)
    seed(time.time_ns())
    logger.debug('<<SupportBot>> generating random id')
    # do not do this in production make sure you are using uuid or a verified unique ID
    caseId = randint(99, 999999)
    logger.debug('<<SupportBot>> random id:'+str(caseId))
    case = {"CaseId": str(caseId),
              "Case Title": slots['problem_title'],
              'Case Description': slots['problem_desc'],
              'Requester Last Name': slots['last_name'],
              'Requester First Name': slots['first_name'],
              'Drop Off Date': slots['dropoff_date'],
              'LastUpdatedDate': str(time.time()),
              'CreatedDate': str(time.time()),
              'Status': 'Created'
    }
    
    response = table.put_item(Item = case)
    return case


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
#
# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import logging
import json
import pprint
import os


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def lambda_handler(event, context):
    logger.debug('<<SupportBot>> Lex event info = ' + json.dumps(event))

    session_attributes = event['sessionAttributes']

    if session_attributes is None:
        session_attributes = {}

    logger.debug('<<SupportBot>> lambda_handler: session_attributes = ' + json.dumps(session_attributes))

    return hello_intent_handler(event, session_attributes)


def hello_intent_handler(intent_request, session_attributes):
    session_attributes['resetCount'] = '0'
    session_attributes['finishedCount'] = '0'
    # don't alter session_attributes['lastIntent'], let SupportBot remember the last used intent

    askCount = increment_counter(session_attributes, 'greetingCount')
    
    # build response string
    if askCount == 1: response_string = "Hello! How can I help?"
    elif askCount == 2: response_string = "I'm here"
    elif askCount == 3: response_string = "I'm listening"
    elif askCount == 4: response_string = "Yes?"
    elif askCount == 5: response_string = "Really?"
    else: response_string = 'Ok'

    return close(session_attributes, 'Fulfilled', {'contentType': 'PlainText','content': response_string})   
    
def increment_counter(session_attributes, counter):
    counter_value = session_attributes.get(counter, '0')

    if counter_value: count = int(counter_value) + 1
    else: count = 1
    
    session_attributes[counter] = count

    return count
    
def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }
    
    logger.debug('<<SupportBot>> "Lambda fulfillment function response = \n' + pprint.pformat(response, indent=4))

    return response    
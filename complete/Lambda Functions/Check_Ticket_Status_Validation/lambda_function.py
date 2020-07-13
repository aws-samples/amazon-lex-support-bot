"""
When this is complete, This function will demonstrate how to validate a function inputs.
Follow the guide in the README.md on how to build this function. If you get stuck, you can look int the
/complete/Lambda Functions/ directory for the completed code.
"""
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    logger.debug('event={}'.format(event))
    
    inputTranscript = event['inputTranscript']
    session_attributes = event['sessionAttributes']    
    intent_name = event['currentIntent']['name']  

    failed_message = "Please make sure you have a valid ticket ID"
    slots =event['currentIntent']['slots']
    ticket_id = slots['ticket_id']  
    
    
    #if ticket_id not None and input value is a valid ticket_id, it calls delegate() and Lex will take over and move on to the next task. 
    if ticket_id!=None and validate_input(ticket_id): 
        return delegate(session_attributes, slots)
        
    #if ticket_id is None
    if ticket_id==None:  
        return delegate(session_attributes, slots)
    else: #if ticket_id is not None and is not valid id format, close the session as "Failed" status. 
        return close(session_attributes, "Failed", failed_message)

# validates if input is 6 digit number
def validate_input(input):
    logger.debug('***validate_input() has been called***')
    
    return input.isnumeric() and len(input)==6
        

# once input value passes the validation, this function delegates to Lex, and Lex continues to the next task. 
def delegate(session_attributes, slots):
    logger.debug('***delegate() has been called***')
    logger.debug('slots={}'.format(slots))
    
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

# if the input value does not pass the validation, this function is called to close the session    
def close(session_attributes, fulfillment_state, message):
    logger.debug('***close() has been called***')
    
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': {
              "contentType": "PlainText",
              "content": message
            }
        }
    }

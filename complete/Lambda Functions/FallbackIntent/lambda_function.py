"""
This sample demonstrates an implementation of an fulfillment lambda for a fallback intent in Lex.

When this is complete, if Lex is unable to map an intent to a user entry, it will consult the Sagemaker endpoint to
see the probability score of one of the existing intents, and if above the minimum threshold, will self update the sample
utterances for the matched intent, then direct the user to continue going with that intent.

Follow the guide in the README.md on how to build this function. If you get stuck, you can look int the
/complete/Lambda Functions/ directory for the completed code.
"""

import json
import os
import logging
import boto3
import random
import urllib.request


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


# --- Helpers that build all of the responses to Lex ---

def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }

def confirm_intent(session_attributes, intent_name, slots, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
            'message': message
        }
    }

def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response

def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

# --- Intent handler ---

def handle_fallback(intent_request, context):
    """
    Performs fulfillment for the fallback intent after persisting the missed utterance
    in a DynamoDB table.
    """
    logger.debug('event.bot.name={}'.format(intent_request))
    logger.debug("intent request for fallback:%s", json.dumps(intent_request))
    
    payload = { "instances": [intent_request['inputTranscript']], "configuration": {"k":5}}
    logger.debug("payload=%s",payload)
    
    sagemaker_runtime = boto3.client('runtime.sagemaker')

    # endpoint specific on lambda environment variable
    endpointName = os.environ['Sagemaker_endpoint_name']
    response = sagemaker_runtime.invoke_endpoint(EndpointName=endpointName,
                                                ContentType='application/json',
                                                Body=json.dumps(payload))
    logger.debug("response:%s",response)
    result = json.loads(response['Body'].read().decode())
    
    # get prefix if there is one
    botName = intent_request['bot']['name']
    logger.debug("result:%s",result)
    logger.debug("botName:%s",botName)
    
    prefix = ''
    if (botName.endswith('_SupportBot')):
        prefix = botName[:len(intent_request['bot']['name'])-len('SupportBot')]

    logger.debug("prefix=%s",prefix)
    targetIntent = ''
    prob = result[0]['prob'][0]
    logger.debug("prob:%s",prob)
    
    probThreshold = float(os.environ['GoodIntentThreshold'])
    logger.debug("probThreshold:%s",probThreshold)
    if (prob > probThreshold):
        # add missed utterance to intent automagically
        # ellicit slot for the utterance we have some confidence for
        targetIntent = result[0]['label'][0][len('__label__'):]

        logger.debug("targetIntent=%s",targetIntent)

        lex = boto3.client('lex-models')
        intentResponse = lex.get_intent(name=prefix+targetIntent, version='$LATEST')
        logger.debug("intentResponse:%s",intentResponse)
        
        putRequest = intentResponse
        del putRequest['ResponseMetadata']
        del putRequest['lastUpdatedDate']
        del putRequest['createdDate']
        del putRequest['version']

        sampleUtterances = intentResponse['sampleUtterances']
        sampleUtterances.append(intent_request['inputTranscript'])
        putRequest['sampleUtterances'] = sampleUtterances
        slots = {}
        for i in intentResponse['slots']:
            slots[i['name']] = None
        # add new utterance
        checksum = intentResponse['checksum']
        logger.debug("checksum=%s"+checksum)
        logger.debug("putting intent back:%s",putRequest)
        lex.put_intent(**putRequest)


        # need to get the prefix CF makes when deploying, best case is parse this from front of fallback intent
        slotPrompt = intentResponse['slots'][len(intentResponse['slots'])-1]['valueElicitationPrompt']['messages']
        message = {
            'contentType': 'PlainText',
            'content': "I think I know what you mean. "+slotPrompt[0]['content']
        }
        return elicit_slot({}, prefix+targetIntent, slots, intentResponse['slots'][len(intentResponse['slots'])-1]['name'], message)
    message = {
        'contentType': 'PlainText',
        'content': "I'm sorry I do not understand you. Please try again later."
    }

    return close({}, 'Fulfilled', message)


# --- Intents ---

def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return handle_fallback(event,context)

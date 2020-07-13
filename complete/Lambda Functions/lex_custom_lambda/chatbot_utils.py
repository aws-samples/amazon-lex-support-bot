#
# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import boto3
import json
import logging
import os



SUCCESS = "SUCCESS"
FAILED = "FAILED"

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

if 'LOG_LEVEL' in os.environ:
    if os.environ['LOG_LEVEL'] == 'DEBUG':
        logger.setLevel(logging.DEBUG)
    if os.environ['LOG_LEVEL'] == 'INFO':
        logger.setLevel(logging.INFO)
    if os.environ['LOG_LEVEL'] == 'WARNING':
        logger.setLevel(logging.WARNING)

lex_client = boto3.client('lex-models')
s3_client = boto3.client('s3')

current_slots = {}
current_intents = {}
bot_intents = []
def get_slots():
    current_slots.clear()
    try:
        next_token = ''
        while True:
            get_slot_types_response = lex_client.get_slot_types(maxResults=50, nextToken=next_token)
            for slot in get_slot_types_response['slotTypes']:
                slot_name = slot['name']
                current_slots[slot_name] = slot
            if 'nextToken' in get_slot_types_response:
                next_token = get_slot_types_response['nextToken']
            else:
                break

    except Exception as ex:
        logger.error("Exception during get slots lex API call : " + str(ex))
        raise

def get_intents():
    current_intents.clear()
    try:
        next_token = ''
        while True:
            get_intents_response = lex_client.get_intents(maxResults=50, nextToken=next_token)
            for intent in get_intents_response['intents']:
                intent_name = intent['name']
                current_intents[intent_name] = intent
            if 'nextToken' in get_intents_response:
                next_token = get_intents_response['nextToken']
            else:
                break

    except Exception as ex:
        logger.error("Exception during get intents lex API call : " + str(ex))
        raise

def import_bot(lex_bot_definition_json, lex_resources_prefix):
    try:
        bot_name = lex_resources_prefix + lex_bot_definition_json['resource']['name']
        get_slots()
        get_intents()
        if 'slotTypes' in lex_bot_definition_json['resource']:
            create_slots(lex_bot_definition_json['resource']['slotTypes'], lex_resources_prefix)
            logger.debug("Created Slot Types:%s",lex_bot_definition_json['resource']['slotTypes'])
        if 'intents' in lex_bot_definition_json['resource']:
            create_intents(lex_bot_definition_json['resource']['intents'], lex_resources_prefix)
            logger.debug("Created Intents")
        create_bot(lex_bot_definition_json['resource'], lex_resources_prefix)
        return {'bot_name': bot_name, 'status':True}
    except Exception as ex:
        logger.error("Exception during bot creation in import bot : " + str(ex))
        return {'bot_name': bot_name, 'status':False}

def create_slots(slots, lex_resources_prefix):
    for slot in slots:
        if 'version' in slot.keys():
            del slot['version']
        #slot['name'] = lex_resources_prefix + slot['name']
        if slot['name'] in current_slots:
            try:
                get_slot_type_response = lex_client.get_slot_type(name=slot['name'], version='$LATEST')
            except Exception as ex:
                logger.error("Exception during get slot lex API call : " + str(ex))
                raise
            checksum = get_slot_type_response['checksum']

            try:
                put_slot_type_response = lex_client.put_slot_type(checksum=checksum, **slot)
            except Exception as ex:
                logger.error("Exception during put slot lex API call : " + str(ex))
                raise
        else:
            try:
                put_slot_type_response = lex_client.put_slot_type(**slot)
            except Exception as ex:
                logger.error("Exception during put slot lex API call : " + str(ex))
                raise
            
def create_intents(intents, lex_resources_prefix):
    #bot_intents.clear()
    global bot_intents
    bot_intents = []
    for intent in intents:
        intent['name'] = lex_resources_prefix + intent['name']
        bot_intents.append({'intentName': intent['name'], 'intentVersion': '$LATEST'})
        if 'version' in intent.keys():
            del intent['version']
        if intent['name'] in current_intents:
            try:
                get_intent_response = lex_client.get_intent(name=intent['name'], version='$LATEST')
            except Exception as ex:
                logger.error("Exception during get intent lex API call : " + str(ex))
                raise
            checksum = get_intent_response['checksum']

            try:
                logger.debug("Putting intent:%s",intent)
                put_intent_response = lex_client.put_intent(checksum=checksum, **intent)
            except Exception as ex:
                logger.error("Exception during put intent lex API call : " + str(ex))
                raise
        else:
            try:
                logger.debug("Putting intent:%s",intent)
                put_intent_response = lex_client.put_intent(**intent)
            except Exception as ex:
                logger.error("Exception during put intent lex API call : " + str(ex))
                raise

def create_bot(bot, lex_resources_prefix):
    logger.debug("Creating bot in chatbot_utils.py")
    bot_exists = True
    if 'version' in bot.keys():
        del bot['version']
    if 'slotTypes' in bot.keys():
        del bot['slotTypes']

    bot['intents'] = bot_intents
    bot['name'] = lex_resources_prefix + bot['name']
    logger.info("Bot aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:%s",json.dumps(bot))
    #logger.info(json.dumps(bot))
    try:
        get_bot_response = lex_client.get_bot(name=bot['name'], versionOrAlias='$LATEST')
    except lex_client.exceptions.NotFoundException as ex:
        bot_exists = False
        logger.error("Exception during get bot lex API call : " + str(ex))
    except Exception as ex:
        logger.error("Exception during get bot lex API call : " + str(ex))
        raise

    if bot_exists:
        checksum = get_bot_response['checksum']

        try:
            put_bot_response = lex_client.put_bot(checksum=checksum, processBehavior='BUILD', **bot)
            logger.info('PUT BOT Response..............' + json.dumps(put_bot_response))
        except Exception as ex:
            logger.error("Exception during put(update) bot lex API call : %s Body:%s",str(ex),json.dumps(bot))
            raise
    else:
        try:
            #put_bot_response = lex_client.put_bot(processBehavior='BUILD', **bot)
            lex_client.put_bot(processBehavior='BUILD', **bot)
            #logger.info('PUT BOT Response..............' + json.dumps(put_bot_response))
        except Exception as ex:
            logger.error("Exception during put(create) bot lex API call : %s Body:%s",str(ex),json.dumps(bot))
            raise
        
    return bot['name']

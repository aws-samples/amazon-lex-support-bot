import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def lambda_handler(event, context):
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    logger.debug('event={}'.format(event))

    session_attributes = event['sessionAttributes']
    logger.debug('<<SupportBot>> thank_you_intent_handler: session_attributes = ' + json.dumps(session_attributes))



    return close(session_attributes, 'Fulfilled', {'contentType': 'PlainText', 'content': response_string})


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

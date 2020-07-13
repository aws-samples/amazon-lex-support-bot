# Create AWS Lambda Functions for Validation and Fulfillment of Intents

In this section, you will create some of the Lambda functions that will be called by the Lex SupportBot. 

The first Lambda function to create is called by the *Check_Ticket_Status* Intent for input validation. [How the initialization and validation Lambda function](https://docs.aws.amazon.com/lex/latest/dg/programming-model.html) works is that every time user enters the new text (for voice, when user speaks), the function is called to check the input text or slot value.   

## Lambda Function for Initialization and Validation - Check_Ticket_Status Intent 

Go to the Lambda console, and look for the *SupportBotStarter-CheckTicketStatusValidationLambd-xxxxxxx* function (xxxxxxx being ramdomly generated text) that was created by the CloudFormation template. 

The following function *validate_input* needs to be completed by adding one line of code following on *return* caluse.

**Exercise:** Write a line of code that checks *input* is a 6 digit number using python's built-in functions. Hint: treat *input* like a string.   

``` 
# validates if input is 6 digit number
def validate_input(input):
    logger.debug('***validate_input() has been called***')
        
    return
``` 

If you were not able to comeplete the above Exercise, simply replace the code in the function with the following code sample. 

<details><summary><strong>Complete code for Check Ticket Status Validation Lambda function (expand for details)</strong></summary><code>

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
</code></details>

The parts to pay attention are the following 2 sections of the code. The first snippet is the *validate_input()* function that checks if slot value is a 6 digit number. The second snippet checks to see if the *ticket_id* (which is a slot) is in a valid format using the function. If it is validated as a valid ticket_id, it returns delegate() function.

This delegate() function simply returns a json formatted text in the Lex's requirement. By calling *delegate()*, Lex keeps going onto the next task. In this case, it moves on to call the fulfillment function since it is done collecting all slot values.  

```
# validates if input is 6 digit number
def validate_input(input):
    return input.isnumeric() and len(input)==6
```  

```
if ticket_id!=None and validate_input(ticket_id): 
    return delegate(session_attributes, slots)
```



## Lambda Function for Intent FulFillment - Check_Ticket_Status Intent

On the Lambda console, look for *SupportBotStarter-CheckTicketStatusLambda-xxxxxxx* function (xxxxxxx being ramdomly generated text) created by CloudFormation.This Lambda function is called when Lex is done eliciting the slot and collected all of the values. In the case of *Check_Ticket_Status* intent, *ticket_id* is only slot. 

**Exercise:** Write a line of code that adds a record to *session_attributes*. Name the attribute *submitterName* in the main handler function.  


If you were not able to complete and above exercise, copy the following code and paste it into the . 

<details><summary><strong>Complete code for Check Ticket Status Lambda function (expand for details)</strong></summary><code>

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
</code></details>

This Lambda function has an environment variable called *DynamoDB_Table_Name* that holds the name of the DynamoDB table name to get the support ticket information. 

The part of the code that is important for context management is the following. Look at the last line of code. The *Requester First Name* is saved in *session_attribute* as *submitterName*. This is how a value gets passed over to another Intent. In this case, *Check_Ticket_Status* intent saves the name, and *Thank_you* intent uses this information to say "I am glad to be a help. Have a nice day, *Submitter's Name*"

```
    if record is None:
        response_string = "We were unable to locate support case "+ event['currentIntent']['slots']['ticket_id'] + " please check your case id and try again."    
    else:
        response_string = 'We have found your support case. The status is '+ record['Status'] + ' and was last updated '+ time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(record['LastUpdatedDate'])))  
          
        session_attributes['submitterName'] = record['Requester First Name']
```

Another part that is worth mentioning is the following. As you can see at the end of main handler, it returns to close the session as *Fulfilled* status. 

```
    return close(session_attributes, 'Fulfilled', {'contentType': 'PlainText','content': response_string})
```


## Lambda Function for Intent Fulfillment - Thank_you Intent

The next Lambda function you will be working on is *SupportBotStarter-ThankYouIntentLambda-xxxxxxx* function. Look for it from the Lambda console. Then expand the following section, copy and paste the code. 

<details><summary><strong>Complete code for Thank You Intent Lambda function (expand for details)</strong></summary><code>

    import json
    import logging

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    def lambda_handler(event, context):
        
        logger.debug('event.bot.name={}'.format(event['bot']['name']))
        logger.debug('event={}'.format(event))
        
        session_attributes = event['sessionAttributes']
        logger.debug('<<SupportBot>> thank_you_intent_handler: session_attributes = ' + json.dumps(session_attributes))
        
        response_string = "I am glad to be a help. Have a nice day, " + session_attributes['submitterName']
            
        return close(session_attributes, 'Fulfilled', {'contentType': 'PlainText','content': response_string})  

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
</code></details>

The part of this code takes the session_attributes value of *submitterName* that was set in another intent fulfillment function, and is now used for the response message. 

```
    response_string = "I am glad to be a help. Have a nice day, " + session_attributes['submitterName']
```

This is how you can [manage conversation context](https://docs.aws.amazon.com/lex/latest/dg/context-mgmt.html). You pass information between intents using session_attributes.


## Lambda Function for Fallback Intent

The last Lambda function you will be working on is *SupportBotStarter-FallbackIntentLambda-xxxxxxx* function. Look for it from the Lambda console and copy and paste the following code. 

<details><summary><strong>Complete code for Fallback Intent Lambda function (expand for details)</strong></summary><code>

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
</code></details>

There is a lot going on with this function. Basically it consults Amazon Sagemaker to get a score of the user's query that Lex could not understand (map to Intent) and tries to direct the user to the right place, all while updating the sample utterances to make it smarter next time. We'll test this out later in Module 4.

Go to
[**Module 3: Build Text Classification Model for Utterance Management using Amazon SageMaker**](../Module%203%20Build%20SageMaker%20Model)
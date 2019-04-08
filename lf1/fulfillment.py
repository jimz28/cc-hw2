import json
import logging
import boto3
import os
import time 


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

sqs = boto3.resource('sqs')
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/925930642762/dining_q2'
queue = sqs.Queue(QUEUE_URL)

def fulfillment(intent_request):
    try:
        res = queue.send_message(
            MessageBody=json.dumps(intent_request)
        )
        return close(
                intent_request['sessionAttributes'],
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': 'Thank you! We have sent messages to your phone!'
                }
            )
    except Exception as e:
        print(e)
        raise e

def dispatch(intent_request):
    intent_name = intent_request['currentIntent']['name']
    intent_source = intent_request['invocationSource']
    if intent_name == 'DiningSuggestionIntent' and intent_source == 'FulfillmentCodeHook':
        return fulfillment(intent_request)


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



def lambda_handler(event, context):
    return dispatch(event)
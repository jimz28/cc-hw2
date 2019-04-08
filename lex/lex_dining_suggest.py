import math
import dateutil.parser
import datetime
import os
import logging
import time
from botocore.vendored import requests
import traceback


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


FOOD_TYPE = ['japanese', 'chinese', 'american', 'mexican']
LOCATION_TYPE = ['NYC']


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


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


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot
        }
    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def isvalid_time(t):
    try:
        dateutil.parser.parse(t)
        return True
    except ValueError:
        return False


def validate_dining_suggest(food_type, date, location, t, people_number):
    # if food_type is not None:
    #     return build_validation_result(
    #         False,
    #         'Food',
    #         'Sorry we do not have {}, but we have the following: {}'.format(food_type, ', '.join(FOOD_TYPE))
    #     )

    if date is not None:
        if not isvalid_date(date):
            return build_validation_result(
                False,
                'Date',
                'I did not understand that, what date do you want to order?'
            )
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(
                False,
                'Date',
                'You could only order the date from today. What date do you want to go?'
            )

    if t is not None:
        if len(t) != 5:
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'Time', 'Please re-enter your time.')

        hour, minute = t.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'Time', 'Please re-enter your time.')

        # if hour < 10 or hour > 16:
        #     # Outside of business hours
        #     return build_validation_result(
        #         False,
        #         'Time',
        #         'Our business hours are from ten a m. to five p m. Can you specify a time during this range?'
        #     )

    # if location is not None and location not in LOCATION_TYPE:
    #     return build_validation_result(False, 'Location', 'Please re-enter your location.')

    if people_number is not None:
        people_number = parse_int(people_number)
        if math.isnan(people_number):
            return build_validation_result(False, 'PeopleNumber', 'Please re-enter your number.')

    return build_validation_result(True, None, None)


def dining_suggest(intent_request):
    food = get_slots(intent_request)['Food']
    date = get_slots(intent_request)['Date']
    t = get_slots(intent_request)['Time']
    people_number = get_slots(intent_request)['PeopleNumber']
    location = get_slots(intent_request)['Location']
    phone = get_slots(intent_request)['Phone']
    
    
    source = intent_request['invocationSource']
    if source == 'DialogCodeHook':
        slots = get_slots(intent_request)

        validation_result = validate_dining_suggest(
            food, date, location, t, people_number
        )
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                intent_request['sessionAttributes'],
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        output_session_attributes = intent_request['sessionAttributes']\
            if 'sessionAttributes' in intent_request and intent_request['sessionAttributes'] is not None\
            else {}

        return delegate(output_session_attributes, get_slots(intent_request))

    elif source == 'FulfillmentCodeHook':
        try:
            unix_d = dateutil.parser.parse(date)
            hour, minute = t.split(':')
            hour = parse_int(hour)
            minute = parse_int(minute)
            unix_t = datetime.time(hour, minute)
            unix_time = datetime.datetime.combine(unix_d, unix_t)
            auth_header = {
                'Authorization': 'Bearer EbJqrMYt0NYrnmP0NAnOFIQiPWUdFgpMAmicTPpd93cVERJI_2nry20qH6zASymmJH8rGy300jCX5xf-n1kUoutSZrYT34qnzxwL6is8qPowiJMYesTnQGIaA3V8XHYx'
            }
            params = {
                'location': location,
                'term': food,
                'open_at': int(unix_time.timestamp())
            }

            response = requests.get(
                'https://api.yelp.com/v3/businesses/search',
                headers=auth_header,
                params=params
            )
            response = response.json()
            logging.debug(response)
            result_str = yelp_decode(response)

            return close(
                intent_request['sessionAttributes'],
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': result_str
                }
            )

        except Exception as e:
            return close(
                intent_request['sessionAttributes'],
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': str(e)
                }
            )
    else:
        return close(
            intent_request['sessionAttributes'],
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': 'NotImplemented'
            }
        )


def yelp_decode(out):
    if len(out['businesses']) < 1:
        return 'Sorry, we do not find any restaurant meeting your requirements.'

    out = out['businesses'][0]
    name = out['name']
    url = out['url']
    addr = out['location']
    s = 'We recommend {name}. The address is {address}. You can view details at {url}'.format(
        name=name,
        address='{}, {}, {}'.format(addr['address1'], addr['city'], addr['state']),
        url=url
    )
    return s


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))
    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'DiningSuggestionIntent':
        return dining_suggest(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)

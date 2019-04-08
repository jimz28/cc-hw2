import json
import datetime
import boto3
import logging


class Message(object):
    def __init__(self, msg_type, msg_id, text, timestamp):
        self.msg_id = msg_id
        self.msg_type = msg_type
        self.text = text
        self.timestamp = timestamp

    @classmethod
    def create_from_msg(cls, msg):
        unstructured = msg['unstructured']
        msg_type = msg['type']
        msg_id = unstructured['id']
        text = unstructured['text']
        timestamp = unstructured['timestamp']
        return cls(msg_type, msg_id, text, timestamp)

    def make_request(self):
        """
        {
          "currentIntent": {
            "name": "intent-name",
            "slots": {
              "slot name": "value",
              "slot name": "value"
            },
            "slotDetails": {
              "slot name": {
                "resolutions" : [
                  { "value": "resolved value" },
                  { "value": "resolved value" }
                ],
                "originalValue": "original text"
              },
              "slot name": {
                "resolutions" : [
                  { "value": "resolved value" },
                  { "value": "resolved value" }
                ],
                "originalValue": "original text"
              }
            },
            "confirmationStatus": "None, Confirmed, or Denied (intent confirmation, if configured)"
          },
          "bot": {
            "name": "bot name",
            "alias": "bot alias",
            "version": "bot version"
          },
          "userId": "User ID specified in the POST request to Amazon Lex.",
          "inputTranscript": "Text used to process the request",
          "invocationSource": "FulfillmentCodeHook or DialogCodeHook",
          "outputDialogMode": "Text or Voice, based on ContentType request header in runtime API request",
          "messageVersion": "1.0",
          "sessionAttributes": {
             "key": "value",
             "key": "value"
          },
          "requestAttributes": {
             "key": "value",
             "key": "value"
          }
        }


        Returns
        -------

        """


def error_response(code):
    return {
        'code': str(code),
        'message': 'Oops, an error'
    }


def response(_type, _id, message, timestamp):
    return {
        'type': _type,
        'unstructured': {
            'id': _id,
            'text': message,
            'timestamp': timestamp
        }
    }


def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        {
            "resource": "Resource path",
            "path": "Path parameter",
            "httpMethod": "Incoming request's method name"
            "headers": {Incoming request headers}
            "queryStringParameters": {query string parameters }
            "pathParameters":  {path parameters}
            "stageVariables": {Applicable stage variables}
            "requestContext": {Request context, including authorizer-returned key-value pairs}
            "body": "A JSON string of the request payload."
            "isBase64Encoded": "A boolean flag to indicate if the applicable request payload is Base64-encode"
        }

        https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

    Attributes
    ----------

    context.aws_request_id: str
         Lambda request ID
    context.client_context: object
         Additional context when invoked through AWS Mobile SDK
    context.function_name: str
         Lambda function name
    context.function_version: str
         Function version identifier
    context.get_remaining_time_in_millis: function
         Time in milliseconds before function times out
    context.identity:
         Cognito identity provider context when invoked through AWS Mobile SDK
    context.invoked_function_arn: str
         Function ARN
    context.log_group_name: str
         Cloudwatch Log group name
    context.log_stream_name: str
         Cloudwatch Log stream name
    context.memory_limit_in_mb: int
        Function memory

        https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict
        'statusCode' and 'body' are required

        {
            "isBase64Encoded": true | false,
            "statusCode": httpStatusCode,
            "headers": {"headerName": "headerValue", ...},
            "body": "..."
        }

        # api-gateway-simple-proxy-for-lambda-output-format
        https: // docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """
    client = boto3.client('lex-runtime')
    try:
        msg = Message.create_from_msg(event['messages'][0])
    except ValueError as e:
        print(str(e))
        return error_response(500)
    
    try:
        lex_output = client.post_text(
            botName='Dining',
            botAlias='greeting',
            userId=msg.msg_id,
            sessionAttributes={},
            requestAttributes={},
            inputText=msg.text
        )
    except Exception as e:
        print(str(e))
        return error_response(500)
    
    return response(
        msg.msg_type,
        msg.msg_id,
        lex_output['message'],
        str(datetime.datetime.now().timestamp())
    )

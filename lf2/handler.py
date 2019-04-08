import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from boto3.dynamodb.conditions import Key, Attr
import json
import random


def test3(event, context):
    # parse sqs msg
    slots = event["Records"][0]["body"]
    slots = json.loads(slots)
    slots = slots["currentIntent"]["slots"]
    cusineType = slots["Food"]
    numPeople = slots["PeopleNumber"]
    time = slots["Time"]
    date = slots["Date"]
    phoneNo = slots["Phone"]

    # elastic serach for index here:
    host = 'search-restaurant-dsml3l3mkfdulkzyecaw4u6aty.us-east-1.es.amazonaws.com' 
    region = 'us-east-1'
    service = 'es'

    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key, 
        credentials.secret_key, 
        region, 
        service,
        session_token=credentials.token
    )

    es = Elasticsearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )

    query = {
        'size':100,
        'query': {
            "match": {
                'category' : cusineType
            }
        }
    }

    res = es.search(index='restaurants', doc_type='restaurant', body=json.dumps(query))
    # print(res)

    print("%d documents found" % res['hits']['total'])
    rids = []
    for doc in res['hits']['hits']:
        rids.append(doc['_source']['id'])
        print("%s %s" % (doc['_source']['id'], doc['_source']['category']))
    rids = random.choices(rids, k=3)

    # create an STS client object that represents a live connection to the 
    # STS service
    # boto3.setup_default_session(profile_name='zz')
    sts_client = boto3.client('sts')

    # Call the assume_role method of the STSConnection object and pass the role
    # ARN and a role session name.
    assumed_role_object=sts_client.assume_role(
        RoleArn="arn:aws:iam::370740074467:role/cloud-hw2-zhengzhi-role",
        RoleSessionName="AssumeRoleSession1"
    )

    # From the response that contains the assumed role, get the temporary 
    # credentials that can be used to make subsequent API calls
    credentials=assumed_role_object['Credentials']

    # db search here:
    db = boto3.resource(
        'dynamodb', 
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
        region_name='us-east-1'
    )

    table = db.Table('restaurant')

    # rids = ['XipQLDbyTl5tsLlyzAWzug'] # test purpose only
    restaurants = ""
    for i in range(len(rids)):
        response = table.query(
            KeyConditionExpression=Key('id').eq(rids[i])
        )

        restaurants = restaurants + "{seq}. {name}, located at {address}, ".format(
            seq=i + 1,
            name=response['Items'][0]['name'], 
            address=response['Items'][0]['address']
        )
    
    restaurants = restaurants[:-2]
    message = ("Hello! Here are my {cusineType} restaurant suggestions for {numPeople} people, " +
    "for {date} at {time}: {restaurants}. Enjoy your meal!").format(
        cusineType=cusineType,
        numPeople=numPeople,
        date=date,
        time=time,
        restaurants=restaurants
    )


    

    # SNS message handling
    client = boto3.client('sns', region_name='us-east-1')
    response = client.publish(
        PhoneNumber=phoneNo,
        Message=json.dumps(message),
        Subject='test message from sdk',
        MessageStructure='text'
    )

    body = {
        "message": json.dumps(event),
        "input": event
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response
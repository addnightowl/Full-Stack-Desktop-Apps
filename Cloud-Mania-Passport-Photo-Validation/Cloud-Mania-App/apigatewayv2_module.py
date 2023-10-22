'''
I created this module to store the functions that interact with the AWS API Gateway service.

Functions in this module:
- list_http_apis: Returns a list of all HTTP APIs in the AWS API Gateway service.
- get_api_details: Returns the details of a specific API in the AWS API Gateway service.
- get_api_stages: Returns a list of stages for a specific API in the AWS API Gateway service.
- construct_invoke_url: Constructs the invoke URL for a specific API, region, and stage.
- datetime_serializer: Serializes datetime objects to ISO 8601 format strings.
- display_apis_and_get_user_choice: Displays a list of APIs and prompts the user to choose one.
'''

# Import the boto3 library for interacting with AWS services.
import boto3
# Import the datetime module to work with dates and times.
from datetime import datetime

# Initialize the AWS API Gateway client using boto3.
client = boto3.client('apigatewayv2')

def list_http_apis():
    # Make a request to AWS API Gateway to list all APIs.
    response = client.get_apis()
    # Filter out only the HTTP APIs from the response.
    http_apis = [api for api in response['Items'] if api['ProtocolType'] == 'HTTP']
    # Return the list of HTTP APIs.
    return http_apis

def get_api_details(api_id):
    # Make a request to AWS API Gateway to get the details of a specific API using its ID.
    response = client.get_api(ApiId=api_id)
    # Return the details of the specified API.
    return response

def get_api_stages(api_id):
    # Make a request to AWS API Gateway to get the stages of a specific API using its ID.
    response = client.get_stages(ApiId=api_id)
    # Return the list of stages for the specified API.
    return response['Items']

def construct_invoke_url(api_id, region, stage_name):
    # Construct the invoke URL for a specific API, region, and stage.
    invoke_url = f'https://{api_id}.execute-api.{region}.amazonaws.com/{stage_name}'
    # Return the constructed invoke URL.
    return invoke_url

def datetime_serializer(obj):
    # Check if the object is an instance of the datetime class.
    if isinstance(obj, datetime):
        # If it's a datetime object, convert it to ISO 8601 format string.
        return obj.isoformat()
    # If the object is not a datetime object, raise a TypeError.
    raise TypeError("Type not serializable")

def display_apis_and_get_user_choice(apis):
    # Loop through the list of APIs and print each one with its index.
    for idx, api in enumerate(apis, start=1):
        print(f"{idx}. {api['Name']} (API ID: {api['ApiId']})")
    # Prompt the user to enter the number corresponding to the API they want to use.
    user_choice = input("Enter the number of the API you want to use: ")
    # Convert the user's choice to a zero-indexed integer and return it.
    return int(user_choice) - 1  # Convert to 0-indexed

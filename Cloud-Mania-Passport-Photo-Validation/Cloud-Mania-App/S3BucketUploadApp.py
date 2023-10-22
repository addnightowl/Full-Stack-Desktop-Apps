'''
Tkinter GUI application that allows users to upload images to our Cloud Mania S3 Bucket for passport validation
and view the results of that image.
'''

# Importing necessary modules for the GUI, file dialog, AWS connection, and other utilities.
import tkinter as tk
# Importing the file dialog module from tkinter.
from tkinter import filedialog
# Importing the boto3 library for interacting with AWS services.
import boto3
# Importing the NoCredentialsError and PartialCredentialsError exceptions from the botocore library.
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
# Importing the os module to work with the operating system.
import os
# Importing the load_dotenv function from the dotenv library.
from dotenv import load_dotenv
# Importing the Image and ImageTk modules from the PIL library.
from PIL import Image, ImageTk
# Importing the requests library to make HTTP requests.
import requests
# Importing the API Gateway module from the apigatewayv2_module.py file.
import apigatewayv2_module as apigw
# Importing the time module to sleep for a few seconds.
import time

'''
You will  need to create a .env file in the root directory of the project and add the following environment variables:
# Full path to the .env file that contains the AWS credentials.
AWS_ENV_PATH="/full/path/to/.env"

# AWS Access Key ID.
AWS_ACCESS_KEY="Access Key ID for the IAM User"

# AWS Secret Access Key.
AWS_SECRET_KEY="Secret Access Key for the IAM User"

# AWS Region.
AWS_REGION="us-east-1"

# Name of AWS API Gateway that you created.
API_NAME="ExampleAPIGateway-Name"
'''
# Load the environment variables for AWS credentials from the specified path.
load_dotenv(os.environ.get("AWS_ENV_PATH"))

# Setting up AWS credentials to access S3.
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION")
API_NAME = os.environ.get("API_NAME")

# List of allowed extensions for images.
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Initialize the S3 client with the provided credentials and region.
s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

# Initialize the CloudFormation client with the provided credentials and region.
cf = boto3.client(
    'cloudformation',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

# Global variable to track the completion status of the check_stack_status function
stack_status_complete = False

# Function to check the status of the stack.
def check_stack_status(stack_name, desired_status):
    # Using the global variable to track the completion status of the check_stack_status function
    global stack_status_complete
    # Check if the stack exists.
    try:
        # Get the stack status.
        response = cf.describe_stacks(StackName=stack_name)
        current_status = response['Stacks'][0]['StackStatus']
        # Check if the stack status is the desired status.
        if current_status == desired_status:
            message_label.config(text=f"Stack {stack_name} is {desired_status}", fg="green")
            stack_status_complete = True
            return True
        # Check if the stack status is in progress.
        elif current_status in ["ROLLBACK_COMPLETE", "UPDATE_ROLLBACK_COMPLETE", "DELETE_FAILED"]:
            message_label.config(text="Stack update failed and was rolled back", fg="red")
            stack_status_complete = True
            return False
        # Check if the stack status is in progress.
        elif current_status == "DELETE_COMPLETE":
            message_label.config(text=f"Stack {stack_name} has been deleted", fg="green")
            stack_status_complete = True
            return True
        # Check if the stack status is in progress.
        else:
            message_label.config(text=f"Waiting for stack {stack_name} to reach status {desired_status}...", fg="blue")
            root.after(5000, check_stack_status, stack_name, desired_status)
    # If the stack does not exist, show a message in the GUI.
    except cf.exceptions.ClientError as e:
        message_label.config(text=f"Failed to get stack status: {e}", fg="red")
        stack_status_complete = True
        return False

# Function to create the infrastructure.
def create_infra():
    """
    This function creates and updates the AWS CloudFormation stack with various templates.
    It takes the stack name from the GUI entry and checks if the stack name is provided.
    If the stack exists, it shows a message in the GUI.
    If the stack creation fails, it shows a message in the GUI.
    If the stack creation is successful, it shows a message in the GUI.
    It updates the stack with each template and checks the status of the stack.
    If the stack update fails, it shows a message in the GUI.
    If the stack update is successful, it shows a message in the GUI.
    After the infrastructure has been created and updated successfully, it:
        - disables the:
            - stack_name_entry
            - create_button
        - enables the:
            - bucket_entry
            - upload_button
            - destroy_checkbox
    """
    global stack_status_complete
    stack_name = stack_name_entry.get()
    if not stack_name:
        message_label.config(text="Please provide a stack name.", fg="red")
        return
    try:
        cf.create_stack(
            StackName=stack_name,
            TemplateBody=open("/full/path/to/01-cloud-mania-s3-template.yaml", 'r').read(),
            Capabilities=["CAPABILITY_NAMED_IAM"]
        )
        stack_status_complete = False
        check_stack_status(stack_name, "CREATE_COMPLETE")
        while not stack_status_complete:
            root.update_idletasks()
            root.update()
        if not stack_status_complete:
            message_label.config(text="Failed to create stack")
            return
        else:
            message_label.config(text="Successfully created stack with initial template.", fg="green")
        templates = [
            "02-cloud-mania-add-s3-notification.yaml",
            "03-cloud-mania-add-sns-topic.yaml",
            "04-cloud-mania-add-lambda-destination.yaml",
            "05-cloud-mania-add-image-request-function.yaml",
            "06-cloud-mania-add-api-gateway-endpoint.yaml",
            "07-cloud-mania-add-s3-deletion-function.yaml"
        ]
        for template in templates:
            template_path = f"/full/path/to/AWS-CF-Templates-Cloud-Mania-Passport-Photo-Screening/{template}"
            cf.update_stack(
                StackName=stack_name,
                TemplateBody=open(template_path, 'r').read(),
                Capabilities=["CAPABILITY_NAMED_IAM"]
            )
            stack_status_complete = False
            check_stack_status(stack_name, "UPDATE_COMPLETE")
            while not stack_status_complete:
                root.update_idletasks()
                root.update()
            if not stack_status_complete:
                message_label.config(text=f"Failed to update stack with template: {template}", fg="red")
                return
            else:
                message_label.config(text=f"Successfully updated stack with template: {template}", fg="green")
        message_label.config(text="Infrastructure created and updated successfully!\n Please, upload Passport Photo for validation.", fg="green")
        stack_name_entry.config(state=tk.DISABLED)
        create_button.config(state=tk.DISABLED)
        bucket_entry.config(state=tk.NORMAL)
        upload_button.config(state=tk.NORMAL)
        destroy_checkbox.config(state=tk.NORMAL)
    except cf.exceptions.ClientError as e:
        message_label.config(text=f"Failed to create or update stack: {e}", fg="red")

# Function to destroy the infrastructure.
def destroy_infra():
    # Refresh the GUI when the destroy button is clicked.
    refresh_gui()
    # Enable the stack_name_entry when the destroy button is clicked
    stack_name = stack_name_entry.get()  # Get the stack name from the GUI entry
    # Check if the stack name is provided.
    if not stack_name:
        message_label.config(text="Please provide a stack name.", fg="red")
        return
    # Check if the stack exists.
    try:
        cf.delete_stack(StackName=stack_name)
        check_stack_status(stack_name, "DELETE_COMPLETE")
    # If the stack does not exist, show a message in the GUI.
    except cf.exceptions.ClientError as e:
        message_label.config(text=f"Failed to initiate infrastructure destruction: {e}", fg="red")

# Function to check if the file is an image.
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to show a preview of the selected image in the GUI.
def show_preview(file_path):
    # Check if the file is an allowed image
    if allowed_file(file_path):
        image = Image.open(file_path)
        image.thumbnail((100, 100))
        photo = ImageTk.PhotoImage(image)
        preview_label.config(image=photo)
        preview_label.image = photo
    # If the file is not an image, show a message in the GUI.
    else:
        preview_label.config(text="Preview not available for non-image files.", fg="gray")

# Function to upload a file to the specified S3 bucket.
def upload_file(file_path, bucket_name):
    # Check if the bucket name is provided.
    file_name = os.path.basename(file_path)
    # Check if the file name is provided.
    try:
        # Upload the file to the specified bucket.
        s3.upload_file(file_path, bucket_name, file_name)
        # Show a message in the GUI.
        upload_message = f'Successfully uploaded to {bucket_name}/{file_name}'
        message_label.config(text=upload_message, fg="green")
        # Check if the file is an allowed image
        if allowed_file(file_name):
            get_validation_result(file_name)
    # If the bucket name is not provided, show a message in the GUI.
    except (NoCredentialsError, PartialCredentialsError):
        message_label.config(text='No credentials found.', fg="red")
    # If the file name is not provided, show a message in the GUI.
    except Exception as e:
        message_label.config(text=f'An error occurred: {e}', fg="red")

# Function to get API information and to return the 'invoke_url'.
def get_invoke_url(api_name):
    # Get all the HTTP APIs in the account
    http_apis = apigw.list_http_apis()
    for api in http_apis:
        if api['Name'] == api_name:
            api_id = api['ApiId']
            break
    # Check if the API exists
    else:
        message_label.config(text=f"No API found with name {api_name}", fg="red")
        return None

    # Get all the stages for the API
    api_stages = apigw.get_api_stages(api_id)
    if not api_stages:
        message_label.config(text=f"No stages found for API ID: {api_id}", fg="red")
        return None

    # Assuming you're interested in the first stage of the API
    stage_name = api_stages[0]['StageName']
    # Get the current region
    region = boto3.session.Session().region_name  # Get current region
    # Construct the invoke URL
    invoke_url = apigw.construct_invoke_url(api_id, region, stage_name)

    return invoke_url

# Function to get validation result for the uploaded image.
def get_validation_result(image_name):
    invoke_url = get_invoke_url(API_NAME)  # Get the invoke URL dynamically 
    # Sleep for 5 seconds to allow the API to be deployed.
    time.sleep(5)
    # Check if the invoke URL is available.
    if not invoke_url:
        message_label.config(text='Failed to get the invoke URL.', fg="red")
        return
    # Construct the URL to make a GET request to the API endpoint.
    url = f'{invoke_url}/images?imageName={image_name}'
    # Make a GET request to the API endpoint.
    response = requests.get(url)
    # Check if the response is successful.
    if response.status_code == 200:
        # Get the response JSON.
        response_json = response.json()
        # Get the validation result from the response.
        validation_result = response_json.get("ValidationResult")
        # Check if the validation result is FAIL.
        if validation_result == "FAIL":
            failure_reasons = response_json.get("FailureReasons")
            message = f'Validation Result: {validation_result}\nFailure Reasons: {failure_reasons}'
            results_label.config(text=message, fg="red")
        # Check if the validation result is PASS.
        else:
            validation_message = f'Validation Result: {validation_result}'
            results_label.config(text=validation_message, fg="blue")

# Function to refresh the GUI.
def refresh_gui():
    # Resetting the preview label.
    preview_label.config(image=None, text="")
    # Resetting the message label.
    message_label.config(text="")
    # Resetting the results label.
    results_label.config(text="")
        
# Function to open file dialog and get the selected file path.
def open_file_dialog():
    # Refresh the GUI each time a new file dialog is opened.
    refresh_gui()
    file_path = filedialog.askopenfilename()
    bucket_name = bucket_entry.get()
    # Check if the file is an allowed image
    if file_path and bucket_name and allowed_file(file_path):
        # Disable the bucket_entry after the file dialog has been used
        bucket_entry.config(state=tk.DISABLED)
        # Show a preview of the selected image in the GUI.
        show_preview(file_path)
        # Upload the file to the specified bucket.
        upload_file(file_path, bucket_name)
        
# Callback function to enable or disable the create_button based on the stack_name_entry content.
def on_entry_change(*args):
    # Check if the stack_name_entry is empty.
    if stack_name_var.get():
        create_button.config(state=tk.NORMAL)
    # If the stack_name_entry is empty, disable the create_button.
    else:
        create_button.config(state=tk.DISABLED)
        
# Checkbox to control the state of the destroy_button
def toggle_destroy_button():
    # Check if the destroy_check_var is checked.
    if destroy_check_var.get():
        # Enable the destroy_button if the destroy_check_var is checked.
        destroy_button.config(state=tk.NORMAL)
        # Disable the create_button, stack_name_entry, and bucket_entry if the destroy_check_var is checked.
        create_button.config(state=tk.DISABLED)
        stack_name_entry.config(state=tk.DISABLED)
        bucket_entry.config(state=tk.DISABLED)
        upload_button.config(state=tk.DISABLED)
    # If the destroy_check_var is not checked, disable the destroy_button.
    else:
        # Disable the destroy_button if the destroy_check_var is not checked.
        destroy_button.config(state=tk.DISABLED)
    
# Creating the main GUI window.
root = tk.Tk()
# Setting the title of the GUI window.
root.title("Cloud Mania Passport Photo Validation App")
# Setting the size of the GUI window.
root.geometry("500x650")

# Creating and placing the 'Stack Name' label and entry field on the GUI.
stack_name_label = tk.Label(root, text="Stack Name (Required for Infra operations):")
# Placing the Stack Name Label on the GUI.
stack_name_label.pack(pady=5)

# Using a StringVar to monitor changes in the entry widget
stack_name_var = tk.StringVar()
# Setting the initial value of the StringVar to an empty string
stack_name_var.trace_add("write", on_entry_change)

# Creating the Stack Name Entry field on the GUI.
stack_name_entry = tk.Entry(root, textvariable=stack_name_var)
# Placing the Stack Name Entry field on the GUI.
stack_name_entry.pack(pady=5)

# Creating and placing the 'Create Infra' button on the GUI.
create_button = tk.Button(root, text="Create Infra", command=create_infra, state=tk.DISABLED)  # Initially disabled
# Placing the Create Infra Button on the GUI.
create_button.pack(pady=10)

# Creating and placing the 'Destroy Infra' button on the GUI.
destroy_check_var = tk.IntVar()
# Setting the initial value of the IntVar to 0
destroy_checkbox = tk.Checkbutton(root, text="Confirm Destruction", variable=destroy_check_var, command=toggle_destroy_button, state=tk.DISABLED)
# Placing the Destroy Infra Button on the GUI.
destroy_checkbox.pack(pady=5)

# Creating and placing the 'Destroy Infra' button on the GUI.
destroy_button = tk.Button(root, text="Destroy Infra", command=destroy_infra, state=tk.DISABLED)  # Initially disabled
# Placing the Destroy Infra Button on the GUI.
destroy_button.pack(pady=10)

# Creating and placing the 'Bucket Name' label and entry field on the GUI.
bucket_label = tk.Label(root, text="Bucket Name (Required):")
# Placing the Bucket Name Label on the GUI.
bucket_label.pack(pady=5)
# Creating the Bucket Name Entry field on the GUI.
bucket_entry = tk.Entry(root)
# Placing the Bucket Name Entry field on the GUI.
bucket_entry.pack(pady=5)
# Initially disable the bucket_entry
bucket_entry.config(state=tk.DISABLED)

# Creating a frame for the message label within the main GUI window
message_frame = tk.Frame(root, bd=2, relief="ridge")
# Placing the message frame in the GUI.
message_frame.pack(pady=10, padx=10, fill="x")
# Creating and placing the message label to display messages on the GUI.
message_label = tk.Label(message_frame, text="", wraplength=350)
# Placing the message label in the frame.
message_label.pack(pady=5)

# Creating a frame for the image preview within the main GUI window
# Setting the width and height to match the thumbnail size
preview_frame = tk.Frame(root, bd=2, relief="ridge", width=100, height=100)
# Placing the preview frame in the GUI.
preview_frame.pack(pady=10, padx=10)
# Ensure the frame doesn't shrink. If you want it to expand to fit the image, you can omit this.
preview_frame.pack_propagate(False)
# Creating and placing the label to display the image preview on the GUI.
preview_label = tk.Label(preview_frame, image=None)
# Placing the image preview label in the frame.
preview_label.pack(pady=10)

# Creating a frame for the results label within the main GUI window
results_frame = tk.Frame(root, bd=2, relief="ridge")
# Placing the results frame in the GUI.
results_frame.pack(pady=10, padx=10, fill="x")
# Creating and placing the results label to display validation results on the GUI.
results_label = tk.Label(results_frame, text="", wraplength=350)
# Placing the results label in the frame.
results_label.pack(pady=5)

# Creating and placing the 'Upload File' button on the GUI.
upload_button = tk.Button(root, text="Upload File", command=open_file_dialog,  state=tk.DISABLED)  # Initially disabled
# Placing the Upload File Button on the GUI.
upload_button.pack(pady=10)

# Start the Tkinter event loop to run the GUI.
root.mainloop()

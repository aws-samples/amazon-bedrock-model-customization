import boto3
import os
import json
from botocore.exceptions import ClientError
from bert_score import score

s3 = boto3.client('s3')
ses = boto3.client('ses')

def get_inferences(bucket, key):
    return json.loads(s3.get_object(Bucket=bucket, Key=key)['Body'].read().decode('utf-8'))

def compute_bert_score(hypotheses, references):
    P, R, F1 = score(hypotheses, references, model_type="distilbert-base-uncased")
    return P.mean().item(), R.mean().item(), F1.mean().item()  

def send_email(subject, body):
    try:
        response = ses.send_email(
            Source=os.environ['SENDER_EMAIL'],
            Destination={
                'ToAddresses': [os.environ['RECIPIENT_EMAIL']]
            },
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
        return response
    except ClientError as e:
        print(e)
        raise Exception("Error sending email")
        
def lambda_handler(event, context):

    reference_hypotheses = get_inferences(os.environ['S3_BUCKET_VALIDATION'], os.environ['REFERENCE_INFERENCE']) 
    base_model_hypotheses = get_inferences(os.environ['S3_BUCKET_INFERENCE'], os.environ['BASE_MODEL_INFERENCE'])
    custom_model_hypotheses = get_inferences(os.environ['S3_BUCKET_INFERENCE'], os.environ['CUSTOM_MODEL_INFERENCE'])

    base_P, base_R, base_F1 = compute_bert_score(base_model_hypotheses, reference_hypotheses)
    custom_P, custom_R, custom_F1 = compute_bert_score(custom_model_hypotheses, reference_hypotheses)

    if custom_F1 > base_F1:
        delete_provisioned_throughput = False
        subject = "Amazon Bedrock model customization completed!"
        body = generate_success_email_body(base_F1, custom_F1)
    else:
        delete_provisioned_throughput = True
        subject = "Amazon Bedrock model customization completed!" 
        body = generate_failure_email_body(base_F1, custom_F1)

    send_email(subject, body)
        
    return {
        'statusCode': 200,
        'deleteProvisionedThroughput': delete_provisioned_throughput
    }

def generate_success_email_body(base_F1, custom_F1):
    return f"Dear Amazon Web Services Customer, \n\n Amazon Bedrock model customization has been completed. Based on the validation data the customized model outperformed the base model. Please note the evaluation outcome: \n\n Base model average F1: {base_F1} \n\n Custom model average F1: {custom_F1}  \n\n Sincerely, \nThe Amazon Web Services Team."
def generate_failure_email_body(base_F1, custom_F1):
    return f"Dear Amazon Web Services Customer, \n\n Amazon Bedrock model customization has been completed. Based on the validation data the customized model underperformed the base model. Please customize the base model again by changing training data or hyper-parameters. Please note the evaluation outcome: \n\n Base model average F1: {base_F1} \n\n Custom model average F1: {custom_F1}  \n\n Sincerely, \nThe Amazon Web Services Team."

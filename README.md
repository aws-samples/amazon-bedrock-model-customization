# Automating model customization in Amazon Bedrock with AWS Step Functions workflow

The AWS Step Functions Workflow can be started using the AWS CLI or from another service (e.g. Amazon API Gateway).

The SAM template deploys an AWS Step Functions workflow that creates custom model by fine tuning a foundation model. It then creates a provisioned throughput with that custom model. Next it evaluates the performance of the custom model with respect to the base model. Text summarization using Amazon Bedrock Cohere Command Light model is taken as an use case. However, the framework can be extended to fine tune other models. The SAM template contains the required resources with IAM permission to run the application.

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [AWS Serverless Application Model](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) (AWS SAM) installed
* [Docker](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-docker.html) must be installed and running.
* You must enable the Amazon Bedrock Cohere Command Light Model access in the Amazon Bedrock console in the region where you are going to run the SAM template.
* You must enable the Cohere Command Light Model access in the Amazon Bedrock console in the AWS Region where you’re going to run the AWS SAM template. We will customize the model in this demonstration. However, the workflow can be extended with minor model-specific changes to support customization of other supported models. See the Amazon Bedrock [user guide](https://docs.aws.amazon.com/bedrock/latest/userguide/custom-models.html) for the full list of supported models for customization. 
* You must have no commitment model units reserved for the model to run this demo.


## Deployment Instructions

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/amazon-bedrock-model-customization.git
    ```

2. Change directory to the pattern directory:
    ```
    cd amazon-bedrock-model-customization
    ```

3. Run the `build.sh` to create the container image.
    ```
    bash build.sh
    ```

4. When asked enter the parameter values. Here are the sample values:
    ```
    image_name=model-evaluation
    repo_name=bedrock-model-customization
    aws_account={your-AWS-account-id}
    aws_region={your-region e.g. us-east-1}
    ```

5. From the command line, use AWS SAM to deploy the AWS resources for the pattern as specified in the `template.yml` file:
    ```
    sam deploy --guided
    ```

6. Provide the below inputs when prompted::
    * Enter a stack name
    * Enter `us-east-1` AWS Region or any other region where Amazon Bedrock and the required foundation model is available.
    * Enter `SenderEmailId` - Once the model customization is complete email will come from this email id. You need to have access to this mail id to verify the ownership.
    * Enter `RecipientEmailId` - User will be notified to this email id.
    * Enter `ContainerImageURI` - ContainerImageURI is available from the output of the `bash build.sh` step.
    * Keep default values for the remaining fields.

7. Note the outputs from the SAM deployment process. These contain the resource names and/or ARNs which are used for testing.

## How it works

* Upload the training data in JSON Line format into the Amazon S3 training data bucket.
* Upload the validation data and reference inference in JSON Line format into the Amazon S3 validation data bucket.
* Start the AWS Step Functions Workflow using the `start-execution` api command with the input payload in JSON format. 
* The workflow invokes Amazon Bedrock's `CreateModelCustomizationJob` API synchronously to fine tune the base model with the training data from the Amazon S3 bucket and the passed in hyperparameters.
* After the custom model is created successfully, the workflow invokes Amazon Bedrock's `CreateProvisionedModelThroughput` API to create a Provisioned Throughput with no commitment.
* The state machine calls the child statemachine to evaluate the performance of the custom model with respect to the base model. 
* The child state machine invokes the base model and the customized model provisioned throughput with the same validation data from the Amazon S3 validation bucket and stores the inference into inference bucket.
* An AWS Lambda function is called to evaluate the quality of the summarization done by custom model and the base model based on BERT score. If the custom model performs worse than the base model, the provisioned throughput is deleted.
* A notification email is sent with the outcome. 

Refer to the architecture diagram below:

![End to End Architecture](image/architecture.png)


## Testing

1. Upload the provided training data files to the Amazon S3 bucket using the following command. Replace `TrainingDataBucket` with the value from the `sam deploy --guided` output. Update `your-region` with the region that you provided while running the SAM template.

   ```bash
   aws s3 cp training-data.jsonl s3://{TrainingDataBucket}/training-data.jsonl --region {your-region}
   ```

2. Upload the `validation-data.json` file to the Amazon S3 bucket using the following command. Replace `ValidationDataBucket` with the value from the `sam deploy --guided` output. Update `your-region` with the region that you provided while running the SAM template.

   ```bash
   aws s3 cp validation-data.json s3://{ValidationDataBucket}/validation-data.json --region {your-region}
   ```

3. Upload the `reference-inference.json` file to the Amazon S3 bucket using the following command. Replace `ValidationDataBucket` with the value from the `sam deploy --guided` output. Update `your-region` with the region that you provided while running the SAM template.

   ```bash
   aws s3 cp reference-inference.json s3://{ValidationDataBucket}/reference-inference.json --region {your-region}
   ```

4. You should have also received an email for verification of the sender email ID. Verify the email ID following instruction given on the email.

![Sender email id verification](image/EmailAddressVerificationRequest.png)


5. Run the following AWS CLI command to start the Step Functions workflow. Replace `StateMachineCustomizeBedrockModelArn` and `TrainingDataBucket` with the values from the `sam deploy --guided` output. Replace `UniqueModelName`, `UniqueJobName` with unique values. Change the values of the hyperparameters based on the selected model. Update `your-region` with the region that you provided while running the SAM template.

    ```bash
    aws stepfunctions start-execution --state-machine-arn "{StateMachineCustomizeBedrockModelArn}" --input "{\"BaseModelIdentifier\": \"cohere.command-light-text-v14:7:4k\",\"CustomModelName\": \"{UniqueModelName}\",\"JobName\": \"{UniqueJobName}\",   \"HyperParameters\": {\"evalPercentage\": \"20.0\", \"epochCount\": \"1\", \"batchSize\": \"8\", \"earlyStoppingPatience\": \"6\", \"earlyStoppingThreshold\": \"0.01\", \"learningRate\": \"0.00001\"},\"TrainingDataFileName\": \"training-data.jsonl\"}" --region {your-region}
    ```

    #### Example output:

    ```bash
    {
        "executionArn": "arn:aws:states:{your-region}:123456789012:execution:{stack-name}-wcq9oavUCuDH:2827xxxx-xxxx-xxxx-xxxx-xxxx6e369948",
        "startDate": "2024-01-28T08:00:26.030000+05:30"
    }
    ```
    
    The foundation model customization and evaluation might take 1 hour to 1.5 hours to complete! You will get a notification email after the customization is done.

5. Run the following AWS CLI command to check the Step Functions workflow status or Log into [AWS Step Functions Cosole](https://console.aws.amazon.com/states/home) to check the execution status. Wait until the workflow completes successfully. Replace the `executionArn` from previous step output and update `your-region`.
    ```bash
    aws stepfunctions describe-execution --execution-arn {executionArn} --query status --region {your-region}
    ```

6. After the AWS Step Functions workflow completes successfully, you will receive an email with the outcome of the quality of the customized model. If the customized model is not performing better than the base model, the provisioned throughput will be deleted. 

![Model customization completed in Amazon Bedrock](image/ModelCustomizationComplete.png)


7. If the quality of the inference response is not satisfactory, you will need to retrain the base model based on the updated training data or hyperparameters.

8. See the `ModelInferenceBucket` for the inferences generated from both the base foundation model and custom model.

## Cleanup
 
1. Delete the Amazon Bedrock provisioned throughput of the custom mode. *Ensure* that the correct `ProvisionedModelArn` is provided to avoid accidental unwanted delete. Also update `your-region`:
   ```bash
   aws bedrock delete-provisioned-model-throughput --provisioned-model-id {ProvisionedModelArn} --region {your-region}
   ``` 

2. Delete the Amazon Bedrock custom model. *Ensure* that the correct `CustomModelName` is provided to avoid accidental unwanted delete. Also update `your-region`:
   ```bash
   aws bedrock delete-custom-model --model-identifier {CustomModelName} --region {your-region}
   ``` 

3. Delete the content in the Amazon S3 bucket using the following command. *Ensure* that the correct bucket name is provided to avoid accidental data loss. Also update `your-region`:
   ```bash
   aws s3 rm s3://{TrainingDataBucket} --recursive --region {your-region}
   aws s3 rm s3://{CustomizationOutputBucket} --recursive --region {your-region}
   aws s3 rm s3://{ValidationDataBucket} --recursive --region {your-region}
   aws s3 rm s3://{ModelInferenceBucket} --recursive --region {your-region}
   ```

4. To delete the resources deployed to your AWS account via AWS SAM, run the following command:
   ```bash
   sam delete
   ```

## License

This library is licensed under the MIT-0 License. See the LICENSE file.


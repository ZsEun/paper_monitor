"""CDK stack for the Academic Journal Monitor application."""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Tags,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_secretsmanager as secretsmanager,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_integrations,
    aws_events as events,
    aws_events_targets as targets,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
)
from constructs import Construct


class JournalMonitorStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Tag all resources
        Tags.of(self).add("Application", "AcademicJournalMonitor")

        # --- Task 8.2: DynamoDB Tables ---
        users_table = dynamodb.Table(
            self, "UsersTable",
            table_name="AcademicJournalMonitor-Users",
            partition_key=dynamodb.Attribute(
                name="email", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        journals_table = dynamodb.Table(
            self, "JournalsTable",
            table_name="AcademicJournalMonitor-Journals",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        digests_table = dynamodb.Table(
            self, "DigestsTable",
            table_name="AcademicJournalMonitor-Digests",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        topics_table = dynamodb.Table(
            self, "InterestTopicsTable",
            table_name="AcademicJournalMonitor-InterestTopics",
            partition_key=dynamodb.Attribute(
                name="userId", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        credentials_table = dynamodb.Table(
            self, "CredentialsTable",
            table_name="AcademicJournalMonitor-Credentials",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        tables = [users_table, journals_table, digests_table, topics_table, credentials_table]

        # --- Task 8.3: Secrets Manager secret for JWT key ---
        jwt_secret = secretsmanager.Secret(
            self, "JwtSecret",
            secret_name="AcademicJournalMonitor/JwtSecret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True,
                password_length=64,
            ),
        )

        # --- Task 8.6: S3 bucket and CloudFront distribution ---
        # (Created before Lambdas so we can reference the CloudFront domain in CORS)
        frontend_bucket = s3.Bucket(
            self, "FrontendBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        distribution = cloudfront.Distribution(
            self, "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(frontend_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
        )

        # --- Lambda Layer for Python dependencies ---
        # Pre-built with: pip3 install -r requirements.txt --platform manylinux2014_x86_64
        #   --target lambda_layer/python --only-binary=:all: --python-version 3.11
        deps_layer = _lambda.LayerVersion(
            self, "DepsLayer",
            code=_lambda.Code.from_asset("../backend/lambda_layer"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="Python dependencies for Academic Journal Monitor",
        )

        # Backend code asset (exclude non-essential files)
        backend_code = _lambda.Code.from_asset(
            "../backend",
            exclude=[
                "lambda_layer",
                "lambda_deps",
                "data",
                "__pycache__",
                "*.pyc",
                ".pytest_cache",
                "venv",
                ".venv",
            ],
        )

        # --- Task 8.4: API Lambda function and API Gateway ---
        cors_origins = cdk.Fn.join("", ["https://", distribution.distribution_domain_name])

        api_lambda = _lambda.Function(
            self, "ApiLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_handler.handler",
            code=backend_code,
            layers=[deps_layer],
            memory_size=512,
            timeout=Duration.seconds(60),
            environment={
                "STORAGE_BACKEND": "dynamodb",
                "DYNAMODB_USERS_TABLE": users_table.table_name,
                "DYNAMODB_JOURNALS_TABLE": journals_table.table_name,
                "DYNAMODB_DIGESTS_TABLE": digests_table.table_name,
                "DYNAMODB_TOPICS_TABLE": topics_table.table_name,
                "DYNAMODB_CREDENTIALS_TABLE": credentials_table.table_name,
                "JWT_SECRET_ARN": jwt_secret.secret_arn,
                "CORS_ALLOWED_ORIGINS": cors_origins,
                "AWS_REGION_NAME": Stack.of(self).region,
            },
        )

        # Grant API Lambda permissions
        for table in tables:
            table.grant_read_write_data(api_lambda)
        jwt_secret.grant_read(api_lambda)
        api_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )

        # HTTP API Gateway with Lambda integration
        api_integration = apigwv2_integrations.HttpLambdaIntegration(
            "ApiIntegration", api_lambda
        )

        http_api = apigwv2.HttpApi(
            self, "HttpApi",
            api_name="AcademicJournalMonitorApi",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[apigwv2.CorsHttpMethod.ANY],
                allow_headers=["*"],
            ),
            default_integration=api_integration,
        )

        # --- Task 8.5: Scraper Lambda function and EventBridge rule ---
        scraper_lambda = _lambda.Function(
            self, "ScraperLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="scraper_handler.handler",
            code=backend_code,
            layers=[deps_layer],
            memory_size=512,
            timeout=Duration.seconds(300),
            environment={
                "STORAGE_BACKEND": "dynamodb",
                "DYNAMODB_USERS_TABLE": users_table.table_name,
                "DYNAMODB_JOURNALS_TABLE": journals_table.table_name,
                "DYNAMODB_DIGESTS_TABLE": digests_table.table_name,
                "DYNAMODB_TOPICS_TABLE": topics_table.table_name,
                "DYNAMODB_CREDENTIALS_TABLE": credentials_table.table_name,
                "AWS_REGION_NAME": Stack.of(self).region,
            },
        )

        # Grant Scraper Lambda permissions
        for table in tables:
            table.grant_read_write_data(scraper_lambda)
        scraper_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )

        # EventBridge rule: weekly schedule
        events.Rule(
            self, "WeeklyScraperRule",
            schedule=events.Schedule.rate(Duration.days(7)),
            targets=[targets.LambdaFunction(scraper_lambda)],
        )

        # --- Task 8.7: CDK stack outputs ---
        CfnOutput(
            self, "CloudFrontURL",
            value=cdk.Fn.join("", ["https://", distribution.distribution_domain_name]),
            description="CloudFront distribution URL for the frontend",
        )

        CfnOutput(
            self, "ApiGatewayURL",
            value=http_api.api_endpoint,
            description="API Gateway endpoint URL",
        )

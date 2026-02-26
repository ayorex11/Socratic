import os
import sys
import django
import boto3

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Config.settings')
django.setup()

from django.conf import settings

client = boto3.client(
    's3',
    endpoint_url=settings.AWS_S3_ENDPOINT_URL,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)

cors_configuration = {
    'CORSRules': [{
        'AllowedHeaders': ['*'],
        'AllowedMethods': ['GET', 'HEAD', 'PUT', 'POST'],
        'AllowedOrigins': ['*'],
        'ExposeHeaders': ['ETag'],
        'MaxAgeSeconds': 3000
    }]
}

try:
    response = client.put_bucket_cors(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        CORSConfiguration=cors_configuration
    )
    print("Successfully updated CORS policy:", response)
except Exception as e:
    print("Failed to update CORS policy:", str(e))

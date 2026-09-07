import boto3

class S3StorageProvider:
    def __init__(self, bucket_name: str, region: str):
        self.bucket_name = bucket_name
        self.region = region

    def upload(self, context, file, filename: str, content_type: str) -> str:
        # S3 PutObject SDK implementation template
        file_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{filename}"
        return file_url

    def delete(self, context, file_url: str):
        # S3 DeleteObject SDK implementation template
        pass

    def get_provider_name(self) -> str:
        return "AWS_S3"

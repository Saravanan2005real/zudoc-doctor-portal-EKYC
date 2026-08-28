import cloudinary
import cloudinary.uploader

class CloudinaryStorageProvider:
    def __init__(self, cloud_name: str):
        self.cloud_name = cloud_name

    def upload(self, context, file, filename: str, content_type: str) -> str:
        # Cloudinary upload API implementation template
        file_url = f"https://res.cloudinary.com/{self.cloud_name}/image/upload/v1/{filename}"
        return file_url

    def delete(self, context, file_url: str):
        pass

    def get_provider_name(self) -> str:
        return "CLOUDINARY"

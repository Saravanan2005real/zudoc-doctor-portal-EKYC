import os


class LocalStorageProvider:
    def __init__(self, base_dir: str = "", base_url: str = ""):
        self.base_dir = os.path.abspath(base_dir or "./uploads")
        self.base_url = (base_url or "/uploads").rstrip("/")
        os.makedirs(self.base_dir, exist_ok=True)

    def upload(self, context, file, filename: str, content_type: str) -> str:
        relative = filename.replace("\\", "/").lstrip("/")
        full_path = os.path.join(self.base_dir, relative.replace("/", os.sep))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        data = file.read() if hasattr(file, "read") else file
        with open(full_path, "wb") as out:
            out.write(data)

        return f"{self.base_url}/{relative}"

    def delete(self, context, file_url: str):
        url = (file_url or "").replace("\\", "/")
        prefix = self.base_url + "/"
        if url.startswith(prefix):
            relative = url[len(prefix):]
        elif url.startswith("/uploads/"):
            relative = url[len("/uploads/"):]
        else:
            relative = url.lstrip("/")

        full_path = os.path.join(self.base_dir, relative.replace("/", os.sep))
        if os.path.exists(full_path):
            os.remove(full_path)

    def get_provider_name(self) -> str:
        return "LOCAL"

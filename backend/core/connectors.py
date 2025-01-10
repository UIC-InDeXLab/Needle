import requests


class ImageGeneratorConnector:
    def __init__(self, base_url):
        self.base_url = base_url

    def list_engines(self):
        response = requests.get(f"{self.base_url}/engines")
        response.raise_for_status()
        return response.json()

    def generate_images(self, generation_config ):
        response = requests.post(f"{self.base_url}/generate", json=generation_config)
        response.raise_for_status()
        return response.json()

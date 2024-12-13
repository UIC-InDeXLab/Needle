import requests


class ImageGeneratorConnector:
    def __init__(self, base_url):
        self.base_url = base_url

    def list_engines(self):
        response = requests.get(f"{self.base_url}/engines")
        response.raise_for_status()
        return response.json()

    def generate_images(self, prompt: str, engines: dict):
        """
        Send a request to generate images with the image generator microservice.
        Args:
            prompt: The input text prompt for image generation.
            engines: A dictionary where keys are engine names and values are dictionaries
                     with `k` and `image_size`.
        """
        payload = {
            "prompt": prompt,
            "engines": engines
        }
        response = requests.post(f"{self.base_url}/generate", json=payload)
        response.raise_for_status()
        return response.json()

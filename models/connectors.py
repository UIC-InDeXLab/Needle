import os

import requests

from models.singleton import Singleton


class Connector:
    def __init__(self, base_url):
        self.base_url = base_url

    def get_binary_data(self, url):
        r = requests.get(self.base_url + url)
        return r.content

    def post_files(self, url, files, params=None):
        r = requests.post(self.base_url + url, files=files, headers={'accept': 'application/json'}, params=params)
        return r.content

    def get_json_data(self, url, params=None):
        r = requests.get(self.base_url + url, params=params)
        return r.json()

    def post_form_data(self, url, params):
        r = requests.post(self.base_url + url, params=params,
                          headers={'accept': 'application/json',
                                   'content-type': 'application/x-www-form-urlencoded'})
        return r.json()

    def post_form_data_get_binary(self, url, params):
        r = requests.post(self.base_url + url, params=params,
                          headers={'accept': 'application/json',
                                   'content-type': 'application/x-www-form-urlencoded'})
        return r.content

    def post_json_data(self, url, json):
        r = requests.post(self.base_url + url, json=json, headers={'accept': 'application/json',
                                                                   'content-type': 'application/json'})
        return r.json()


class DALLEConnector(Connector):
    def __init__(self):
        super().__init__(os.getenv("IMAGE_EDITOR_BASE_URL"))

    def edit_image(self, base_image, mask, prompt, size="256x256", n=1):
        files = {
            'image': base_image,
            'mask': mask,
        }
        params = {
            'prompt': prompt,
            'n': str(n),
            'size': size,
        }
        return self.post_files("/v1/images/edits", files=files, params=params)

    def generate_image(self, prompt: str, size="256x256", n=1):
        params = {
            'prompt': prompt,
            'n': str(n),
            'size': size
        }
        return self.post_form_data("/v1/images/generations", params=params)


class LocalStableDiffusionConnector(Connector):
    def __init__(self):
        super().__init__(os.getenv("SD_BASE_URL"))

    def generate_image(self, prompt: str, size=512):
        params = {
            'prompt': prompt,
            'size': size
        }
        return self.post_form_data_get_binary("/generate", params=params)



from abc import ABC, abstractmethod

import requests

from settings import settings


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

    @abstractmethod
    def generate_image(self, *args, **kwargs):
        pass


class DALLEConnector(Connector):
    def __init__(self):
        super().__init__(settings.engines.dalle_url)

    def generate_image(self, prompt: str, size="256x256", n=1):
        params = {
            'prompt': prompt,
            'n': str(n),
            'size': size
        }
        return self.post_form_data("/v1/images/generations", params=params)


class ReplicateConnector(Connector):
    def __init__(self):
        super().__init__(settings.engines.replicate_url)

    def generate_image(self, prompt: str, k=1):
        params = {
            'prompt': prompt,
            'k': k,
        }
        return self.post_form_data("/generate", params=params)


class LocalStableDiffusionConnector(Connector, ABC):
    def generate_image(self, prompt: str, size=512):
        params = {
            'prompt': prompt,
            'size': size
        }
        return self.post_form_data_get_binary("/generate", params=params)


class SDXLTurboConnector(LocalStableDiffusionConnector):
    def __init__(self):
        super().__init__(settings.engines.sdxl_url)


class RunwayMLConnector(LocalStableDiffusionConnector):
    def __init__(self):
        super().__init__(settings.engines.runwayml_url)

import json
import os

import requests


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

    def post_json_data(self, url, params, data):
        for key in data:
            if type(data[key]) is bool:
                data[key] = str(data[key]).lower()

        r = requests.post(self.base_url + url, data=json.dumps(data), params=params,
                          headers={'accept': 'application/json',
                                   'content-type': 'application/json'})
        return r.json()


class NeedleConnector(Connector):
    def __init__(self):
        super().__init__(os.getenv("NEEDLE_URL"))

    def search(self, qid: int, generator_engines, n: int = 20, k: int = 4, image_size: int = 512):
        params = {
            "n": n,
            "k": k,
            "image_size": image_size,
            "generator_engines": generator_engines
        }
        return self.get_json_data(f"/search/{qid}", params=params)

    def create_query(self, query: str):
        params = {
            "q": query
        }

        return self.post_form_data("/query", params=params)

    def submit_feedback(self, feedback: dict, qid: int, eta: float = 0.05):
        params = {
            "eta": eta
        }

        return self.post_json_data(f"/search/{qid}/", params=params, data=feedback)


class CLIPConnector(Connector):
    def __init__(self):
        super().__init__(os.getenv("CLIP_URL"))

    def search(self, query: str, n: int = 20):
        params = {
            "query": query,
            "n": n,
        }
        return self.get_json_data("/search", params=params)

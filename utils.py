import requests


def get_image_from_url(url):
    return requests.get(url).content

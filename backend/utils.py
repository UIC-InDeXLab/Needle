import base64
from io import BytesIO

from PIL import Image

import time
from collections import defaultdict


class Timer:
    """A context manager to time blocks of code."""

    def __init__(self, name: str, timings_dict: dict, aggregate: bool = False):
        self.name = name
        self.timings = timings_dict
        self.aggregate = aggregate
        self._start = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        duration = time.perf_counter() - self._start
        if self.aggregate:
            # If called multiple times (in a loop), aggregate the times
            if not isinstance(self.timings.get(self.name), list):
                self.timings[self.name] = []
            self.timings[self.name].append(duration)
        else:
            self.timings[self.name] = duration


def aggregate_rankings(rankers_results, weights, k):
    scores = {}
    for i, R_i in enumerate(rankers_results):
        for j, result in enumerate(R_i):
            if result not in scores:
                scores[result] = 0
            scores[result] += weights[i] * (1 / (j + 1))

    ranked_results = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    return ranked_results[:k]


def decode_base64_image(data: str) -> Image.Image:
    img_data = base64.b64decode(data)
    return Image.open(BytesIO(img_data)).convert("RGB")


def pil_image_to_base64(img: Image.Image) -> str:
    """
    Convert a PIL image to a base64-encoded PNG data URL.
    """
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    buffered.seek(0)
    img_bytes = buffered.read()
    b64_img = 'data:image/png;base64,' + base64.b64encode(img_bytes).decode('utf-8')
    return b64_img

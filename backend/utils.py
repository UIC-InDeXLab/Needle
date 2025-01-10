import base64
from io import BytesIO

from PIL import Image


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

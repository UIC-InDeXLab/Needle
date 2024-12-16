import json

import timm

data = json.load(open('config.json'))
for emb in data['image_embedders']:
    timm.create_model(emb['model_name'], pretrained=True)

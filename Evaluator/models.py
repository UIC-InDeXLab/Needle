import pandas as pd


class Dataset:
    def __init__(self, name, resource_path, metadata_path):
        self.name = name
        self.resource_path = resource_path
        self.metadata_path = metadata_path
        self.metadata = pd.read_csv(metadata_path)


def load_datasets(config_path: str):
    import json
    with open(config_path) as f:
        config = json.load(f)
    datasets = {}
    for dataset_config in config['datasets']:
        dataset = Dataset(
            name=dataset_config['name'],
            resource_path=dataset_config['resource_path'],
            metadata_path=dataset_config['metadata_path']
        )
        datasets[dataset.name] = dataset
    return datasets

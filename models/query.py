from typing import Optional

from models.singleton import Singleton


class Query:
    _id_counter = 0

    def __init__(self, q):
        self._q = q
        self._embedders_results = {}
        self._generated_images = []
        self._id = Query._generate_id()

    @classmethod
    def _generate_id(cls):
        cls._id_counter += 1
        return cls._id_counter

    @property
    def id(self):
        return self._id

    @property
    def query(self):
        return self._q

    @property
    def generated_images(self):
        return self._generated_images

    @property
    def embedder_results(self):
        return self._embedders_results

    def get_embedder_result_by_name(self, name: str):
        return self._embedders_results.get(name, None)

    def add_embedder_results(self, embedder_name: str, results):
        self._embedders_results[embedder_name] = results


@Singleton
class QueryManager:
    def __init__(self):
        self._queries = {}

    def add_query(self, q: Query):
        self._queries[q.id] = q
        return q.id

    def get_query(self, id: int) -> Optional[Query]:
        return self._queries.get(id, None)

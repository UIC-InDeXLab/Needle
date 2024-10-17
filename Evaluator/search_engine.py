from abc import ABC, abstractmethod

from connectors import NeedleConnector, CLIPConnector


class SearchEngine(ABC):
    @abstractmethod
    def search(self, query, n, *args, **kwargs):
        pass

    @abstractmethod
    def submit_feedback(self, feedback, qid):
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def is_feedback_required(self):
        pass


class NeedleEngine(SearchEngine):
    @property
    def name(self):
        return "needle"

    def search(self, query, n, *args, **kwargs):
        c = NeedleConnector()
        image_size = kwargs.get("image_size", 512)
        k = kwargs.get("k", 4)
        generator_engines = kwargs.get("generator_engines")
        qid = int(c.create_query(query)["qid"])
        res = c.search(qid, n=n, k=k, image_size=image_size, generator_engines=generator_engines)
        return res["results"], res["qid"]

    def get_qid_results(self, qid, n, *args, **kwargs):
        c = NeedleConnector()
        res = c.search(qid, n=n, generator_engines=[])
        return res["results"]

    def submit_feedback(self, feedback, qid):
        c = NeedleConnector()
        return c.submit_feedback(feedback, qid=qid)

    @property
    def is_feedback_required(self):
        return True


class CLIPEngine(SearchEngine):
    @property
    def name(self):
        return "clip"

    def search(self, query, n, *args, **kwargs):
        c = CLIPConnector()
        return c.search(query, n=n)["results"], None

    @property
    def is_feedback_required(self):
        return False

    def submit_feedback(self, feedback, qid):
        raise NotImplementedError()

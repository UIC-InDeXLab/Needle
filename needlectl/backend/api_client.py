# api_client.py
import time
from typing import Any, Dict, Optional

import requests


class BackendClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, params=params)
        return self._handle_response(response)

    def _post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = requests.post(url, json=data)
        return self._handle_response(response)

    def _delete(self, endpoint: str, json: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = requests.delete(url, json=json)
        return self._handle_response(response)

    def _handle_response(self, response):
        if not response.ok:
            try:
                error_msg = response.json().get("detail", response.text)
            except Exception:
                error_msg = response.text
            raise requests.HTTPError(f"HTTP {response.status_code}: {error_msg}")
        return response.json()

    # -------------------------------------------------------------------------
    # Directory endpoints
    # -------------------------------------------------------------------------
    def add_directory(self, path: str) -> Any:
        """
        POST /directory
        Body: { "path": "<directory_path>" }
        """
        return self._post("/directory", data={"path": path})

    def remove_directory(self, path: str) -> Any:
        """
        DELETE /directory
        Body: { "path": "<directory_path>" }
        """
        return self._delete("/directory", json={"path": path})

    def list_directories(self) -> Any:
        """
        GET /directory
        Returns a list of directories (DirectoryListResponse).
        """
        return self._get("/directory")

    def describe_directory(self, did: int) -> Any:
        """
        GET /directory/{did}
        Returns DirectoryDetailResponse with directory info, image paths, indexing ratio, etc.
        """
        return self._get(f"/directory/{did}")

    # -------------------------------------------------------------------------
    # Generators
    # -------------------------------------------------------------------------
    def list_generators(self) -> Any:
        """
        GET /generator
        Returns a list of available generator engines (List[GeneratorInfo]).
        """
        return self._get("/generator")

    # -------------------------------------------------------------------------
    # Searching
    # -------------------------------------------------------------------------
    def run_search(
            self,
            prompt: str,
            engine_configs: list,
            num_images_to_retrieve: Optional[int] = None,
            include_base_images: Optional[bool] = None,
            num_engines_to_use: Optional[int] = None,
            num_images_per_engine: Optional[int] = None,
            image_size: Optional[int] = None,
            use_fallback: Optional[bool] = None
    ) -> Any:
        """
        1) Create a query via POST /query
           Body: { "q": "<prompt>" }
        2) Run the search via POST /search
           Body: SearchRequest, including:
                {
                    "qid": <query_id>,
                    "num_images_to_retrieve": ...,
                    "include_base_images_in_preview": ...,
                    "generation_config": {
                        "engines": [
                            { "name": "...", "params": {...} },
                            ...
                        ],
                        "num_engines_to_use": ...,
                        "num_images": ...,
                        "image_size": ...,
                        "use_fallback": ...
                    }
                }
        """
        qres = self._post("/query", data={"q": prompt})
        qid = qres["qid"]

        generation_config = {
            "engines": engine_configs,
        }

        generation_optionals = {"num_images_per_engine": num_images_per_engine,
                                "num_engines_to_use": num_engines_to_use,
                                "image_size": image_size, "use_fallback": use_fallback}

        for optional, value in generation_optionals.items():
            if value is not None:
                generation_config[optional] = value

        search_request_body = {
            "qid": qid,
            "generation_config": generation_config
        }

        search_optionals = {"num_images_to_retrieve": num_images_to_retrieve,
                            "include_base_images_in_preview": include_base_images}

        for optional, value in search_optionals.items():
            if value is not None:
                search_request_body[optional] = value

        return self._post("/search", data=search_request_body)

    def get_search_logs(self) -> Any:
        """
        GET /search/logs
        Returns SearchLogsResponse (list of query logs).
        """
        return self._get("/search/logs")

    # -------------------------------------------------------------------------
    # Service
    # -------------------------------------------------------------------------
    def get_service_status(self) -> Any:
        """
        GET /service/status
        Returns ServiceStatusResponse (e.g. { "status": "running" }).
        """
        return self._get("/service/status")

    def get_service_log(self) -> Any:
        """
        GET /service/log
        Returns ServiceLogResponse.
        """
        return self._get("/service/log")

    def healthcheck(self) -> Any:
        """
        GET /health
        Returns HealthCheckResponse (e.g. { "status": "running" }).
        """
        return self._get("/health")

    def wait_for_api(self, timeout: int = 120) -> Any:
        """
        Wait for the API to respond with a 'running' status (health check).
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.healthcheck()
                if response.get("status") == "running":
                    return response
            except requests.RequestException:
                # Optionally log the exception or handle retries here
                pass
            time.sleep(2)  # Poll every 2 seconds
        raise TimeoutError(f"The API did not become healthy within {timeout} seconds.")

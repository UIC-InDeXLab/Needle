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

    def _delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = requests.delete(url, params=params)
        return self._handle_response(response)

    def _handle_response(self, response):
        if not response.ok:
            try:
                error_msg = response.json().get("detail", response.text)
            except Exception:
                error_msg = response.text
            raise requests.HTTPError(f"HTTP {response.status_code}: {error_msg}")
        return response.json()

    # Directory endpoints
    def add_directory(self, path: str) -> Any:
        return self._post("/directory", data={"path": path})

    def remove_directory(self, path: str) -> Any:
        return self._delete("/directory", params={"path": path})

    def list_directories(self) -> Any:
        return self._get("/directory")

    def describe_directory(self, did: int) -> Any:
        return self._get(f"/directory/{did}")

    # Generators
    def list_generators(self) -> Any:
        return self._get("/generators")

    def describe_generator(self, name: str) -> Any:
        return self._get(f"/generator/{name}")

    # Search
    def run_search(self, prompt: str, n: int, k: int, image_size: int, include_base_images: bool) -> Any:
        # First create a query:
        qres = self._post("/query", data={"q": prompt})
        qid = qres["qid"]
        # Then run search
        return self._get(f"/search/{qid}", params={
            "n": n,
            "k": k,
            "image_size": image_size,
            "include_base_images": include_base_images
        })

    def get_search_logs(self) -> Any:
        return self._get("/search/logs")

    # Service
    def get_service_status(self) -> Any:
        return self._get("/service/status")

    def get_service_log(self) -> Any:
        return self._get("/service/log")

    def healthcheck(self) -> Any:
        return self._get("/health")

    def wait_for_api(self, timeout: int = 120) -> Any:
        """
        Waits for the health API to return a 200 status code and status == "running" in the JSON response.

        Args:
            timeout (int): The maximum number of seconds to wait for the API to be healthy.

        Returns:
            Any: The JSON response from the health API when it becomes healthy.

        Raises:
            TimeoutError: If the API does not become healthy within the timeout period.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.healthcheck()
                if response.get("status") == "running":
                    return response
            except requests.RequestException as e:
                # Optionally log the exception or handle retries here
                pass
            time.sleep(2)  # Poll every 2 seconds
        raise TimeoutError(f"The API did not become healthy within {timeout} seconds.")

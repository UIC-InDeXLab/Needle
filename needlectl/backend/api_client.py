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

    def _put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = requests.put(url, json=data)
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

    def update_directory(self, did: int, is_enabled: bool):
        return self._put(f"/directory/{did}", data={"is_enabled": is_enabled})

    # -------------------------------------------------------------------------
    # Generators
    # -------------------------------------------------------------------------
    def list_generators(self) -> Any:
        """
        GET /generator
        Returns a list of available generator engines (List[GeneratorInfo]).
        """
        return self._get("/generator")

    def get_generator_preferences(self) -> Any:
        """Which engines are enabled, their order and the fallback flag.

        Stored by the backend and shared with the desktop app.
        """
        return self._get("/generator/preferences")

    def set_generator_preferences(self, engines: list, fallback: bool) -> Any:
        return self._put("/generator/preferences",
                         data={"engines": engines, "fallback": fallback})

    def set_generator_credentials(self, name: str, params: Dict[str, str]) -> Any:
        return self._post(f"/generator/{name}/credentials", data={"params": params})

    def test_generator(self, name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._post(f"/generator/{name}/test", data={"params": params or {}})

    # -------------------------------------------------------------------------
    # On-device generation
    # -------------------------------------------------------------------------
    def get_generate_models(self) -> Any:
        return self._get("/generate/models")

    def get_generate_state(self) -> Any:
        return self._get("/generate/state")

    def load_generate_model(self, model: str) -> Any:
        return self._post("/generate/load", data={"model": model})

    # -------------------------------------------------------------------------
    # Setup / onboarding
    # -------------------------------------------------------------------------
    def get_setup_status(self) -> Any:
        return self._get("/setup/status")

    def get_setup_options(self) -> Any:
        return self._get("/setup/options")

    def configure_setup(self, profile: str, use_gpu: bool) -> Any:
        return self._post("/setup/configure", data={"profile": profile, "use_gpu": use_gpu})

    def set_gpu(self, use_gpu: bool) -> Any:
        return self._post("/setup/gpu", data={"use_gpu": use_gpu})

    def get_system_info(self) -> Any:
        return self._get("/system/info")

    # -------------------------------------------------------------------------
    # Searching
    # -------------------------------------------------------------------------
    def run_search(
            self,
            prompt: str,
            num_images_to_retrieve: Optional[int] = None,
            include_base_images: Optional[bool] = None,
            num_images_per_engine: Optional[int] = None,
            image_size: Optional[str] = None,
    ) -> Any:
        """Create a query, then run the search for it.

        Engines are deliberately not sent: the backend applies the shared
        generator preferences, so the CLI and the desktop app resolve a search
        exactly the same way.
        """
        qres = self._post("/query", data={"q": prompt})
        qid = qres["qid"]

        generation_config = {}
        generation_optionals = {
            "num_images_per_engine": num_images_per_engine,
            "image_size": image_size,
        }
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

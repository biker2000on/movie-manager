"""
Radarr API client module with retry logic and error handling.
"""
import time
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import ConnectionError, Timeout


class RadarrAPIError(Exception):
    """Custom exception for Radarr API errors."""

    def __init__(self, status_code: int, message: str, endpoint: str):
        """
        Initialize RadarrAPIError.

        Args:
            status_code: HTTP status code from the API response
            message: Error message describing what went wrong
            endpoint: The API endpoint that was called
        """
        self.status_code = status_code
        self.message = message
        self.endpoint = endpoint
        super().__init__(f"Radarr API Error {status_code} at {endpoint}: {message}")


class RadarrClient:
    """Client for interacting with Radarr API."""

    def __init__(self, url: str, api_key: str):
        """
        Initialize the Radarr API client.

        Args:
            url: Base URL of the Radarr instance (e.g., "http://localhost:7878")
            api_key: API key for authentication
        """
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.headers = {"X-Api-Key": api_key}
        self.max_retries = 3
        self.retry_delays = [1, 2, 4]  # Exponential backoff in seconds

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Make an HTTP request to the Radarr API with retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path (e.g., "/api/v3/system/status")
            params: Optional query parameters
            json_data: Optional JSON payload for POST/PUT requests

        Returns:
            Response data (JSON parsed)

        Raises:
            RadarrAPIError: When the API returns an error or max retries exceeded
        """
        url = f"{self.url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json_data,
                    timeout=30
                )

                # Check for successful response
                if response.status_code < 400:
                    # Handle empty responses (like DELETE operations)
                    if response.status_code == 204 or not response.content:
                        return None
                    return response.json()

                # Handle 4xx errors (don't retry)
                if 400 <= response.status_code < 500:
                    error_message = response.text
                    try:
                        error_data = response.json()
                        error_message = error_data.get('message', error_message)
                    except ValueError:
                        pass
                    raise RadarrAPIError(response.status_code, error_message, endpoint)

                # Handle 5xx errors (retry)
                if response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delays[attempt])
                        continue
                    raise RadarrAPIError(
                        response.status_code,
                        f"Server error after {self.max_retries} retries: {response.text}",
                        endpoint
                    )

            except (ConnectionError, Timeout) as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delays[attempt])
                    continue
                raise RadarrAPIError(
                    0,
                    f"Connection error after {self.max_retries} retries: {str(e)}",
                    endpoint
                )

        # Should not reach here, but just in case
        raise RadarrAPIError(0, "Unknown error occurred", endpoint)

    def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to Radarr by fetching system status.

        Returns:
            System status information

        Raises:
            RadarrAPIError: If connection fails or authentication is invalid
        """
        return self._request("GET", "/api/v3/system/status")

    def get_movies(self) -> List[Dict[str, Any]]:
        """
        Get all movies from Radarr.

        Returns:
            List of movie dictionaries

        Raises:
            RadarrAPIError: If the API request fails
        """
        return self._request("GET", "/api/v3/movie")

    def delete_movie(
        self,
        movie_id: int,
        delete_files: bool = True,
        add_exclusion: bool = True
    ) -> None:
        """
        Delete a movie from Radarr.

        Args:
            movie_id: The ID of the movie to delete
            delete_files: Whether to delete the movie files from disk
            add_exclusion: Whether to add the movie to the exclusion list

        Raises:
            RadarrAPIError: If the API request fails
        """
        params = {
            "deleteFiles": str(delete_files).lower(),
            "addImportExclusion": str(add_exclusion).lower()
        }
        self._request("DELETE", f"/api/v3/movie/{movie_id}", params=params)

    def get_exclusions(self) -> List[Dict[str, Any]]:
        """
        Get all import exclusions from Radarr.

        Returns:
            List of exclusion dictionaries

        Raises:
            RadarrAPIError: If the API request fails
        """
        return self._request("GET", "/api/v3/exclusions")

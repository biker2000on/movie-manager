"""
Comprehensive unit tests for the Radarr horror filter tool.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from filter import GenreFilter
from deleter import MovieDeleter
from radarr_client import RadarrClient, RadarrAPIError
import time


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_movies():
    """Sample movie data for testing."""
    return [
        {
            "id": 1,
            "title": "Saw",
            "year": 2004,
            "genres": ["Horror", "Thriller"],
            "hasFile": True,
            "sizeOnDisk": 2000000000
        },
        {
            "id": 2,
            "title": "Avengers",
            "year": 2012,
            "genres": ["Action", "Sci-Fi"],
            "hasFile": True,
            "sizeOnDisk": 3000000000
        },
        {
            "id": 3,
            "title": "The Conjuring",
            "year": 2013,
            "genres": ["Horror"],
            "hasFile": True,
            "sizeOnDisk": 1500000000
        },
    ]


@pytest.fixture
def mock_radarr_client():
    """Mock RadarrClient for testing."""
    return Mock(spec=RadarrClient)


# ============================================================================
# GENREFILTER TESTS
# ============================================================================

class TestGenreFilter:
    """Tests for the GenreFilter class."""

    def test_filters_horror_movies(self, sample_movies):
        """Test basic horror movie filtering."""
        filter_obj = GenreFilter("Horror")
        result = filter_obj.filter(sample_movies)

        assert len(result) == 2
        assert result[0]["title"] == "Saw"
        assert result[1]["title"] == "The Conjuring"

    def test_case_insensitive_matching(self, sample_movies):
        """Test that HORROR, horror, Horror all match correctly."""
        test_cases = ["HORROR", "horror", "Horror", "HoRrOr"]

        for genre_case in test_cases:
            filter_obj = GenreFilter(genre_case)
            result = filter_obj.filter(sample_movies)

            assert len(result) == 2, f"Failed for genre: {genre_case}"
            assert result[0]["title"] == "Saw"
            assert result[1]["title"] == "The Conjuring"

    def test_empty_movie_list(self):
        """Test that filtering an empty list returns empty list."""
        filter_obj = GenreFilter("Horror")
        result = filter_obj.filter([])

        assert result == []
        assert isinstance(result, list)

    def test_movies_with_no_genres(self):
        """Test handling of movies with missing or empty genres."""
        movies_no_genres = [
            {"id": 1, "title": "Movie1", "genres": []},
            {"id": 2, "title": "Movie2"},  # Missing 'genres' key
            {"id": 3, "title": "Movie3", "genres": ["Horror"]},
            {"id": 4, "title": "Movie4", "genres": None},
        ]

        filter_obj = GenreFilter("Horror")
        result = filter_obj.filter(movies_no_genres)

        # Only Movie3 should be returned
        assert len(result) == 1
        assert result[0]["title"] == "Movie3"

    def test_custom_genre(self, sample_movies):
        """Test filtering for a different genre like Thriller."""
        filter_obj = GenreFilter("Thriller")
        result = filter_obj.filter(sample_movies)

        # Only Saw has Thriller genre
        assert len(result) == 1
        assert result[0]["title"] == "Saw"

    def test_genre_not_found(self, sample_movies):
        """Test filtering when no movies match the genre."""
        filter_obj = GenreFilter("Documentary")
        result = filter_obj.filter(sample_movies)

        assert result == []

    def test_get_statistics(self, sample_movies):
        """Test statistics calculation."""
        filter_obj = GenreFilter("Horror")
        filtered = filter_obj.filter(sample_movies)
        stats = filter_obj.get_statistics(sample_movies, filtered)

        assert stats["total_count"] == 3
        assert stats["filtered_count"] == 2
        assert stats["total_size_bytes"] == 6500000000  # 2GB + 3GB + 1.5GB
        assert stats["filtered_size_bytes"] == 3500000000  # 2GB + 1.5GB


# ============================================================================
# MOVIEDELETER TESTS
# ============================================================================

class TestMovieDeleter:
    """Tests for the MovieDeleter class."""

    @patch("deleter.Progress")
    def test_dry_run_makes_no_api_calls(self, mock_progress, sample_movies, mock_radarr_client):
        """Verify that dry run mode makes no API calls."""
        deleter = MovieDeleter(mock_radarr_client)

        # Run in dry-run mode
        with patch("deleter.console"):  # Suppress console output
            result = deleter.delete_movies(sample_movies, dry_run=True)

        # Verify no API calls were made
        mock_radarr_client.delete_movie.assert_not_called()

        # Verify all movies are marked as deleted (simulated)
        assert len(result["deleted"]) == 3
        assert len(result["failed"]) == 0
        assert len(result["skipped"]) == 0

    @patch("deleter.Progress")
    def test_delete_files_by_default(self, mock_progress, sample_movies, mock_radarr_client):
        """Verify delete_files=True when keep_files=False (default)."""
        deleter = MovieDeleter(mock_radarr_client)

        with patch("deleter.console"):
            deleter.delete_movies(sample_movies, keep_files=False)

        # Check that delete_movie was called with delete_files=True
        assert mock_radarr_client.delete_movie.call_count == 3
        for call in mock_radarr_client.delete_movie.call_args_list:
            kwargs = call.kwargs
            assert kwargs["delete_files"] is True
            assert kwargs["add_exclusion"] is True

    @patch("deleter.Progress")
    def test_keep_files_when_flag_set(self, mock_progress, sample_movies, mock_radarr_client):
        """Verify delete_files=False when keep_files=True."""
        deleter = MovieDeleter(mock_radarr_client)

        with patch("deleter.console"):
            deleter.delete_movies(sample_movies, keep_files=True)

        # Check that delete_movie was called with delete_files=False
        assert mock_radarr_client.delete_movie.call_count == 3
        for call in mock_radarr_client.delete_movie.call_args_list:
            kwargs = call.kwargs
            assert kwargs["delete_files"] is False
            assert kwargs["add_exclusion"] is True

    @patch("deleter.Progress")
    def test_returns_correct_structure(self, mock_progress, sample_movies, mock_radarr_client):
        """Check that the result has deleted/failed/skipped dict structure."""
        deleter = MovieDeleter(mock_radarr_client)

        with patch("deleter.console"):
            result = deleter.delete_movies(sample_movies)

        # Verify structure
        assert "deleted" in result
        assert "failed" in result
        assert "skipped" in result

        # Verify all are lists
        assert isinstance(result["deleted"], list)
        assert isinstance(result["failed"], list)
        assert isinstance(result["skipped"], list)

        # All movies should be successfully deleted
        assert len(result["deleted"]) == 3
        assert len(result["failed"]) == 0
        assert len(result["skipped"]) == 0

    @patch("deleter.Progress")
    def test_handles_api_errors(self, mock_progress, sample_movies, mock_radarr_client):
        """Test that deletion continues on error and tracks failures."""
        deleter = MovieDeleter(mock_radarr_client)

        # Make the second movie fail
        def side_effect(movie_id, **kwargs):
            if movie_id == 2:
                raise RadarrAPIError(500, "Server error", "/api/v3/movie/2")

        mock_radarr_client.delete_movie.side_effect = side_effect

        with patch("deleter.console"):
            result = deleter.delete_movies(sample_movies)

        # Verify that 2 succeeded and 1 failed
        assert len(result["deleted"]) == 2
        assert len(result["failed"]) == 1
        assert "Avengers" in result["failed"]
        assert "Saw" in result["deleted"]
        assert "The Conjuring" in result["deleted"]

    @patch("deleter.Progress")
    def test_handles_missing_movie_id(self, mock_progress, mock_radarr_client):
        """Test handling of movies without an ID."""
        movies_missing_id = [
            {"title": "Movie1", "genres": ["Horror"]},  # Missing 'id'
            {"id": 2, "title": "Movie2", "genres": ["Horror"]},
        ]

        deleter = MovieDeleter(mock_radarr_client)

        with patch("deleter.console"):
            result = deleter.delete_movies(movies_missing_id)

        # First movie should fail, second should succeed
        assert len(result["failed"]) == 1
        assert len(result["deleted"]) == 1
        assert "Movie1" in result["failed"]
        assert "Movie2" in result["deleted"]

    def test_empty_movie_list(self, mock_radarr_client):
        """Test handling of empty movie list."""
        deleter = MovieDeleter(mock_radarr_client)

        with patch("deleter.console"):
            result = deleter.delete_movies([])

        # Should return empty results
        assert result["deleted"] == []
        assert result["failed"] == []
        assert result["skipped"] == []

        # No API calls should be made
        mock_radarr_client.delete_movie.assert_not_called()


# ============================================================================
# RADARRCLIENT TESTS
# ============================================================================

class TestRadarrClient:
    """Tests for the RadarrClient class."""

    def test_test_connection_success(self):
        """Test that test_connection returns True on 200 response."""
        with patch("radarr_client.requests.request") as mock_request:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"version": "4.0.0"}
            mock_request.return_value = mock_response

            client = RadarrClient("http://localhost:7878", "test-api-key")
            result = client.test_connection()

            # Verify the request was made correctly
            mock_request.assert_called_once()
            assert result == {"version": "4.0.0"}

    def test_test_connection_failure(self):
        """Test that test_connection raises RadarrAPIError on failure."""
        with patch("radarr_client.requests.request") as mock_request:
            # Mock failed response (401 Unauthorized)
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.json.side_effect = ValueError("No JSON")
            mock_request.return_value = mock_response

            client = RadarrClient("http://localhost:7878", "bad-api-key")

            with pytest.raises(RadarrAPIError) as exc_info:
                client.test_connection()

            # Verify error details
            assert exc_info.value.status_code == 401
            assert "Unauthorized" in str(exc_info.value.message)

    def test_retry_on_server_error(self):
        """Test that the client retries on 5xx errors with exponential backoff."""
        with patch("radarr_client.requests.request") as mock_request, \
             patch("radarr_client.time.sleep") as mock_sleep:

            # First two attempts return 500, third succeeds
            mock_response_fail = Mock()
            mock_response_fail.status_code = 500
            mock_response_fail.text = "Internal Server Error"

            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"status": "ok"}

            mock_request.side_effect = [
                mock_response_fail,
                mock_response_fail,
                mock_response_success
            ]

            client = RadarrClient("http://localhost:7878", "test-api-key")
            result = client.test_connection()

            # Verify it retried 3 times total
            assert mock_request.call_count == 3

            # Verify exponential backoff was used (1s, 2s)
            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(1)
            mock_sleep.assert_any_call(2)

            # Verify eventual success
            assert result == {"status": "ok"}

    def test_max_retries_exceeded(self):
        """Test that RadarrAPIError is raised after max retries."""
        with patch("radarr_client.requests.request") as mock_request, \
             patch("radarr_client.time.sleep"):

            # All attempts return 500
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_request.return_value = mock_response

            client = RadarrClient("http://localhost:7878", "test-api-key")

            with pytest.raises(RadarrAPIError) as exc_info:
                client.test_connection()

            # Verify max retries (3) were attempted
            assert mock_request.call_count == 3

            # Verify error message mentions retries
            assert "retries" in str(exc_info.value).lower()

    def test_handles_connection_error(self):
        """Test that connection errors are retried and eventually raise."""
        with patch("radarr_client.requests.request") as mock_request, \
             patch("radarr_client.time.sleep"):

            # Simulate connection error
            from requests.exceptions import ConnectionError
            mock_request.side_effect = ConnectionError("Connection refused")

            client = RadarrClient("http://localhost:7878", "test-api-key")

            with pytest.raises(RadarrAPIError) as exc_info:
                client.test_connection()

            # Verify retries occurred
            assert mock_request.call_count == 3

            # Verify error message
            assert "Connection error" in str(exc_info.value)

    def test_delete_movie_parameters(self):
        """Test that delete_movie sends correct parameters."""
        with patch("radarr_client.requests.request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b""  # Empty response for DELETE
            mock_request.return_value = mock_response

            client = RadarrClient("http://localhost:7878", "test-api-key")
            client.delete_movie(movie_id=123, delete_files=True, add_exclusion=False)

            # Verify request was made with correct parameters
            call_args = mock_request.call_args
            assert call_args.kwargs["method"] == "DELETE"
            assert "/api/v3/movie/123" in call_args.kwargs["url"]
            assert call_args.kwargs["params"] == {
                "deleteFiles": "true",
                "addImportExclusion": "false"
            }

    def test_get_movies_returns_list(self):
        """Test that get_movies returns a list of movies."""
        with patch("radarr_client.requests.request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"id": 1, "title": "Movie1"},
                {"id": 2, "title": "Movie2"}
            ]
            mock_request.return_value = mock_response

            client = RadarrClient("http://localhost:7878", "test-api-key")
            movies = client.get_movies()

            assert len(movies) == 2
            assert movies[0]["title"] == "Movie1"
            assert movies[1]["title"] == "Movie2"

    def test_url_trailing_slash_handling(self):
        """Test that trailing slashes in URL are handled correctly."""
        with patch("radarr_client.requests.request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"version": "4.0.0"}
            mock_request.return_value = mock_response

            # Create client with trailing slash
            client = RadarrClient("http://localhost:7878/", "test-api-key")
            client.test_connection()

            # Verify URL doesn't have double slashes
            call_args = mock_request.call_args
            url = call_args.kwargs["url"]
            assert "//" not in url.replace("http://", "")

    def test_handles_204_no_content(self):
        """Test that 204 No Content responses are handled correctly."""
        with patch("radarr_client.requests.request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 204
            mock_response.content = b""
            mock_request.return_value = mock_response

            client = RadarrClient("http://localhost:7878", "test-api-key")
            result = client.delete_movie(movie_id=1)

            # Should return None for 204 responses
            assert result is None

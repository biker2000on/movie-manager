"""
Comprehensive unit tests for the KeepListManager class.
"""
import pytest
import json
from datetime import datetime
from keep_list import KeepListManager


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def keep_list(tmp_path):
    """Create a KeepListManager with a temporary file path."""
    file_path = tmp_path / ".keep-list.json"
    return KeepListManager(str(file_path))


@pytest.fixture
def sample_movies():
    """Sample movie data for testing."""
    return [
        {"id": 1, "title": "The Exorcist", "genres": ["Horror"]},
        {"id": 2, "title": "Hereditary", "genres": ["Horror"]},
        {"id": 3, "title": "Avengers", "genres": ["Action"]},
    ]


# ============================================================================
# KEEPLISTMANAGER TESTS
# ============================================================================

class TestKeepListManager:
    """Tests for the KeepListManager class."""

    def test_init_creates_empty_list_if_no_file(self, tmp_path):
        """Test that a new KeepListManager creates an empty list when file doesn't exist."""
        file_path = tmp_path / ".keep-list.json"
        manager = KeepListManager(str(file_path))

        assert manager.movies == []
        assert manager.file_path.name == ".keep-list.json"

    def test_init_loads_existing_file(self, tmp_path):
        """Test that existing JSON file is loaded correctly on initialization."""
        file_path = tmp_path / ".keep-list.json"

        # Create a pre-existing file
        existing_data = {
            "version": 1,
            "movies": [
                {"id": 1, "title": "The Exorcist", "added_at": "2024-01-01T12:00:00Z"},
                {"id": 2, "title": "Hereditary", "added_at": "2024-01-02T12:00:00Z"},
            ]
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f)

        # Load it
        manager = KeepListManager(str(file_path))

        assert len(manager.movies) == 2
        assert manager.movies[0]["title"] == "The Exorcist"
        assert manager.movies[1]["title"] == "Hereditary"

    def test_add_movie(self, keep_list):
        """Test adding a movie to the keep list."""
        keep_list.add(1, "The Exorcist")

        assert len(keep_list.movies) == 1
        assert keep_list.movies[0]["id"] == 1
        assert keep_list.movies[0]["title"] == "The Exorcist"
        assert "added_at" in keep_list.movies[0]

        # Verify timestamp format (ISO 8601 with Z suffix)
        added_at = keep_list.movies[0]["added_at"]
        assert added_at.endswith("Z")
        # Should be parseable as datetime
        datetime.fromisoformat(added_at.replace("Z", ""))

    def test_add_prevents_duplicates(self, keep_list):
        """Test that adding the same movie ID twice is prevented."""
        keep_list.add(1, "The Exorcist")
        keep_list.add(1, "The Exorcist")  # Try to add again

        # Should still only have one entry
        assert len(keep_list.movies) == 1

        # Adding same ID with different title should also be prevented
        keep_list.add(1, "Different Title")
        assert len(keep_list.movies) == 1
        assert keep_list.movies[0]["title"] == "The Exorcist"  # Original title

    def test_remove_by_id(self, keep_list):
        """Test removing a movie by ID."""
        keep_list.add(1, "The Exorcist")
        keep_list.add(2, "Hereditary")

        # Remove by ID
        result = keep_list.remove(movie_id=1)

        assert result is True
        assert len(keep_list.movies) == 1
        assert keep_list.movies[0]["title"] == "Hereditary"

    def test_remove_by_title(self, keep_list):
        """Test removing a movie by title (case-insensitive)."""
        keep_list.add(1, "The Exorcist")
        keep_list.add(2, "Hereditary")

        # Remove by title (case-insensitive)
        result = keep_list.remove(title="the exorcist")

        assert result is True
        assert len(keep_list.movies) == 1
        assert keep_list.movies[0]["title"] == "Hereditary"

    def test_remove_nonexistent_returns_false(self, keep_list):
        """Test that removing a non-existent movie returns False."""
        keep_list.add(1, "The Exorcist")

        # Try to remove non-existent ID
        result = keep_list.remove(movie_id=999)
        assert result is False
        assert len(keep_list.movies) == 1

        # Try to remove non-existent title
        result = keep_list.remove(title="Nonexistent Movie")
        assert result is False
        assert len(keep_list.movies) == 1

    def test_list_all_empty(self, keep_list):
        """Test that list_all returns empty list when no movies are kept."""
        result = keep_list.list_all()

        assert result == []
        assert isinstance(result, list)

    def test_list_all_with_movies(self, keep_list):
        """Test that list_all returns all kept movies."""
        keep_list.add(1, "The Exorcist")
        keep_list.add(2, "Hereditary")
        keep_list.add(3, "Avengers")

        result = keep_list.list_all()

        assert len(result) == 3
        assert result[0]["title"] == "The Exorcist"
        assert result[1]["title"] == "Hereditary"
        assert result[2]["title"] == "Avengers"

        # Verify it's a copy (modifications don't affect original)
        result.append({"id": 999, "title": "Test"})
        assert len(keep_list.movies) == 3

    def test_clear(self, keep_list):
        """Test that clear removes all entries from the keep list."""
        keep_list.add(1, "The Exorcist")
        keep_list.add(2, "Hereditary")
        keep_list.add(3, "Avengers")

        assert len(keep_list.movies) == 3

        keep_list.clear()

        assert len(keep_list.movies) == 0
        assert keep_list.list_all() == []

    def test_is_kept_by_id(self, keep_list):
        """Test checking if a movie is kept by ID."""
        keep_list.add(1, "The Exorcist")
        keep_list.add(2, "Hereditary")

        assert keep_list.is_kept(movie_id=1) is True
        assert keep_list.is_kept(movie_id=2) is True
        assert keep_list.is_kept(movie_id=999) is False

    def test_is_kept_by_title_case_insensitive(self, keep_list):
        """Test that title matching is case-insensitive."""
        keep_list.add(1, "The Exorcist")

        # All case variations should match
        assert keep_list.is_kept(title="The Exorcist") is True
        assert keep_list.is_kept(title="the exorcist") is True
        assert keep_list.is_kept(title="THE EXORCIST") is True
        assert keep_list.is_kept(title="tHe ExOrCiSt") is True

    def test_is_kept_returns_false_for_unknown(self, keep_list):
        """Test that is_kept returns False for unknown movies."""
        keep_list.add(1, "The Exorcist")

        # Unknown ID
        assert keep_list.is_kept(movie_id=999) is False

        # Unknown title
        assert keep_list.is_kept(title="Unknown Movie") is False

        # No parameters provided
        assert keep_list.is_kept() is False

    def test_filter_kept_removes_kept_movies(self, keep_list, sample_movies):
        """Test that filter_kept removes movies that are in the keep list."""
        # Add two movies to keep list
        keep_list.add(1, "The Exorcist")
        keep_list.add(2, "Hereditary")

        # Filter the sample movies
        result = keep_list.filter_kept(sample_movies)

        # Only Avengers (id=3) should remain
        assert len(result) == 1
        assert result[0]["title"] == "Avengers"
        assert result[0]["id"] == 3

    def test_filter_kept_with_empty_keep_list(self, keep_list, sample_movies):
        """Test that filter_kept returns all movies when keep list is empty."""
        result = keep_list.filter_kept(sample_movies)

        assert len(result) == 3
        assert result == sample_movies

    def test_filter_kept_with_empty_movie_list(self, keep_list):
        """Test that filter_kept handles empty movie list."""
        keep_list.add(1, "The Exorcist")

        result = keep_list.filter_kept([])

        assert result == []

    def test_save_load_round_trip(self, tmp_path):
        """Test that data persists correctly through save and load."""
        file_path = tmp_path / ".keep-list.json"

        # Create manager and add movies
        manager1 = KeepListManager(str(file_path))
        manager1.add(1, "The Exorcist")
        manager1.add(2, "Hereditary")
        manager1.add(3, "Avengers")

        # Create new manager instance (should load from file)
        manager2 = KeepListManager(str(file_path))

        # Verify all data was loaded
        assert len(manager2.movies) == 3
        assert manager2.movies[0]["title"] == "The Exorcist"
        assert manager2.movies[1]["title"] == "Hereditary"
        assert manager2.movies[2]["title"] == "Avengers"

        # Verify file format
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data["version"] == 1
            assert len(data["movies"]) == 3

    def test_handles_corrupted_json(self, tmp_path):
        """Test that corrupted JSON is handled gracefully."""
        file_path = tmp_path / ".keep-list.json"

        # Write invalid JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("{ this is not valid JSON }")

        # Should not crash, should return empty list
        manager = KeepListManager(str(file_path))

        assert manager.movies == []

    def test_handles_missing_movies_key(self, tmp_path):
        """Test handling of JSON without 'movies' key."""
        file_path = tmp_path / ".keep-list.json"

        # Write JSON without 'movies' key
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"version": 1}, f)

        manager = KeepListManager(str(file_path))

        assert manager.movies == []

    def test_save_creates_pretty_formatted_json(self, tmp_path):
        """Test that saved JSON is pretty-formatted with indentation."""
        file_path = tmp_path / ".keep-list.json"

        manager = KeepListManager(str(file_path))
        manager.add(1, "The Exorcist")

        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should have newlines and indentation (not single-line)
        assert '\n' in content
        assert '  ' in content  # 2-space indent

        # Should be valid JSON
        data = json.loads(content)
        assert data["version"] == 1
        assert len(data["movies"]) == 1

    def test_remove_with_no_parameters(self, keep_list):
        """Test that remove returns False when no parameters provided."""
        keep_list.add(1, "The Exorcist")

        result = keep_list.remove()

        assert result is False
        assert len(keep_list.movies) == 1

    def test_filter_kept_handles_movies_without_id(self, keep_list):
        """Test that filter_kept handles movies without 'id' field."""
        keep_list.add(1, "The Exorcist")

        movies_missing_id = [
            {"id": 1, "title": "The Exorcist"},
            {"title": "Movie Without ID"},  # Missing 'id' field
            {"id": 2, "title": "Hereditary"},
        ]

        result = keep_list.filter_kept(movies_missing_id)

        # Movie with id=1 should be filtered out
        # Movie without id should remain (not in kept_ids set)
        # Movie with id=2 should remain
        assert len(result) == 2
        assert result[0]["title"] == "Movie Without ID"
        assert result[1]["title"] == "Hereditary"

    def test_unicode_handling(self, keep_list):
        """Test that unicode characters in titles are handled correctly."""
        keep_list.add(1, "Amélie")
        keep_list.add(2, "十三號星期五")  # Chinese characters
        keep_list.add(3, "Москва")  # Cyrillic

        # Check they were saved correctly
        assert keep_list.is_kept(title="Amélie") is True
        assert keep_list.is_kept(title="十三號星期五") is True
        assert keep_list.is_kept(title="Москва") is True

        # Verify persistence
        movies = keep_list.list_all()
        assert movies[0]["title"] == "Amélie"
        assert movies[1]["title"] == "十三號星期五"
        assert movies[2]["title"] == "Москва"

    def test_multiple_removes(self, keep_list):
        """Test that multiple removes work correctly."""
        keep_list.add(1, "The Exorcist")
        keep_list.add(2, "Hereditary")
        keep_list.add(3, "Avengers")

        # Remove by ID
        assert keep_list.remove(movie_id=1) is True
        assert len(keep_list.movies) == 2

        # Remove by title
        assert keep_list.remove(title="Hereditary") is True
        assert len(keep_list.movies) == 1

        # Remove last one by ID
        assert keep_list.remove(movie_id=3) is True
        assert len(keep_list.movies) == 0

        # Try to remove from empty list
        assert keep_list.remove(movie_id=1) is False

    def test_case_sensitive_title_storage(self, keep_list):
        """Test that titles are stored with their original casing."""
        keep_list.add(1, "The Exorcist")

        movies = keep_list.list_all()
        # Original casing should be preserved
        assert movies[0]["title"] == "The Exorcist"

        # But matching should be case-insensitive
        assert keep_list.remove(title="the exorcist") is True

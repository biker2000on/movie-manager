import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class KeepListManager:
    """Manages a keep list of movies that should not be deleted."""

    def __init__(self, file_path: Optional[str] = None):
        """
        Initialize the KeepListManager.

        Args:
            file_path: Path to the JSON file storing the keep list.
                       If None, uses KEEP_LIST_PATH env var or defaults to ".keep-list.json"
        """
        if file_path is None:
            file_path = os.environ.get('KEEP_LIST_PATH', '.keep-list.json')
        self.file_path = Path(file_path)
        self.movies = []
        self.load()

    def load(self):
        """
        Load the keep list from the JSON file.
        Returns an empty list if the file doesn't exist or is corrupted.
        """
        if not self.file_path.exists():
            self.movies = []
            return

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.movies = data.get('movies', [])
        except (json.JSONDecodeError, IOError):
            # Handle corrupted JSON or read errors gracefully
            self.movies = []

    def save(self):
        """Write the current keep list to the JSON file with pretty formatting."""
        data = {
            'version': 1,
            'movies': self.movies
        }

        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add(self, movie_id: int, title: str):
        """
        Add a movie to the keep list.
        Prevents duplicates by ID and stores added_at timestamp.

        Args:
            movie_id: The movie ID
            title: The movie title
        """
        # Prevent duplicates by ID
        if any(movie['id'] == movie_id for movie in self.movies):
            return

        movie_entry = {
            'id': movie_id,
            'title': title,
            'added_at': datetime.now().isoformat() + 'Z'
        }
        self.movies.append(movie_entry)
        self.save()

    def remove(self, movie_id: Optional[int] = None, title: Optional[str] = None) -> bool:
        """
        Remove a movie from the keep list by ID or title.

        Args:
            movie_id: The movie ID to remove (optional)
            title: The movie title to remove (case-insensitive, optional)

        Returns:
            True if a movie was removed, False otherwise
        """
        initial_length = len(self.movies)

        if movie_id is not None:
            self.movies = [m for m in self.movies if m['id'] != movie_id]
        elif title is not None:
            title_lower = title.lower()
            self.movies = [m for m in self.movies if m['title'].lower() != title_lower]

        if len(self.movies) < initial_length:
            self.save()
            return True

        return False

    def list_all(self) -> List[Dict]:
        """
        Return a list of all kept movies.

        Returns:
            List of movie dictionaries with id, title, and added_at fields
        """
        return self.movies.copy()

    def clear(self):
        """Remove all entries from the keep list."""
        self.movies = []
        self.save()

    def is_kept(self, movie_id: Optional[int] = None, title: Optional[str] = None) -> bool:
        """
        Check if a movie is in the keep list.

        Args:
            movie_id: The movie ID to check (optional)
            title: The movie title to check (case-insensitive, optional)

        Returns:
            True if the movie is in the keep list, False otherwise
        """
        if movie_id is not None:
            return any(movie['id'] == movie_id for movie in self.movies)

        if title is not None:
            title_lower = title.lower()
            return any(movie['title'].lower() == title_lower for movie in self.movies)

        return False

    def filter_kept(self, movies: List[Dict]) -> List[Dict]:
        """
        Filter out kept movies from a list of movies.

        Args:
            movies: List of movie dictionaries (must have 'id' field)

        Returns:
            List of movies that are NOT in the keep list
        """
        kept_ids = {movie['id'] for movie in self.movies}
        return [movie for movie in movies if movie.get('id') not in kept_ids]

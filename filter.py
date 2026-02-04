"""Genre-based movie filtering module."""


class GenreFilter:
    """Filter movies by genre with case-insensitive matching."""

    def __init__(self, genre="Horror"):
        """
        Initialize the genre filter.

        Args:
            genre: The genre to filter by (default: "Horror")
        """
        self.genre = genre.lower()

    def filter(self, movies):
        """
        Filter movies by the target genre.

        Args:
            movies: List of movie dictionaries with 'genres' field

        Returns:
            List of movies containing the target genre
        """
        filtered = []
        for movie in movies:
            # Handle missing or empty genres
            genres = movie.get('genres', [])
            if not genres:
                continue

            # Case-insensitive genre matching
            movie_genres = [g.lower() for g in genres]
            if self.genre in movie_genres:
                filtered.append(movie)

        return filtered

    def get_statistics(self, movies, filtered_movies):
        """
        Calculate statistics for total and filtered movies.

        Args:
            movies: List of all movies
            filtered_movies: List of filtered movies

        Returns:
            Dictionary with counts and sizes:
            - total_count: Total number of movies
            - filtered_count: Number of filtered movies
            - total_size_bytes: Total size of all movies
            - filtered_size_bytes: Total size of filtered movies
        """
        total_size = sum(movie.get('sizeOnDisk', 0) for movie in movies)
        filtered_size = sum(movie.get('sizeOnDisk', 0) for movie in filtered_movies)

        return {
            'total_count': len(movies),
            'filtered_count': len(filtered_movies),
            'total_size_bytes': total_size,
            'filtered_size_bytes': filtered_size
        }

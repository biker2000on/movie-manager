"""Movie scanner module for scanning Radarr library."""

from typing import List, Dict, Any
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from radarr_client import RadarrClient


class MovieScanner:
    """Scans and processes movies from Radarr library."""

    def __init__(self, client: RadarrClient):
        """Initialize scanner with Radarr client.

        Args:
            client: RadarrClient instance for API communication
        """
        self.client = client

    def scan(self) -> List[Dict[str, Any]]:
        """Scan Radarr library and return structured movie data.

        Returns:
            List of movie dictionaries with keys:
                - id: Movie ID
                - title: Movie title
                - year: Release year
                - genres: List of genre strings
                - hasFile: Boolean indicating if movie file exists
                - sizeOnDisk: Size in bytes (0 if no file)
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Scanning Radarr library...", total=None)

            # Fetch movies from Radarr
            raw_movies = self.client.get_movies()

            if not raw_movies:
                progress.update(task, description="[yellow]No movies found in library")
                return []

            # Update progress with actual count
            progress.update(task, total=len(raw_movies), completed=0)
            progress.update(task, description=f"[cyan]Processing {len(raw_movies)} movies...")

            # Parse movies into structured format
            movies = []
            for raw_movie in raw_movies:
                movie = {
                    'id': raw_movie.get('id'),
                    'title': raw_movie.get('title', 'Unknown'),
                    'year': raw_movie.get('year', 0),
                    'genres': raw_movie.get('genres', []),
                    'hasFile': raw_movie.get('hasFile', False),
                    'sizeOnDisk': raw_movie.get('sizeOnDisk', 0)
                }
                movies.append(movie)
                progress.advance(task)

            progress.update(task, description=f"[green]Successfully scanned {len(movies)} movies")

        return movies

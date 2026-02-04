"""
Movie deletion module with file deletion as default behavior.
"""
from typing import Dict, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from radarr_client import RadarrClient, RadarrAPIError

console = Console()


class MovieDeleter:
    """Handles movie deletion with progress tracking and error handling."""

    def __init__(self, client: RadarrClient):
        """
        Initialize the MovieDeleter.

        Args:
            client: RadarrClient instance for API interactions
        """
        self.client = client

    def delete_movies(
        self,
        movies: List[Dict],
        keep_files: bool = False,
        dry_run: bool = False
    ) -> Dict[str, List[str]]:
        """
        Delete movies from Radarr with progress tracking.

        IMPORTANT: Files are deleted by default (keep_files=False).

        Args:
            movies: List of movie dictionaries to delete
            keep_files: If False (default), delete files from disk. If True, keep files.
            dry_run: If True, only log what would be deleted without making API calls

        Returns:
            Dictionary with keys:
                - deleted: List of successfully deleted movie titles
                - failed: List of movie titles that failed to delete
                - skipped: List of skipped movie titles (reserved for future use)
        """
        results = {
            "deleted": [],
            "failed": [],
            "skipped": []
        }

        if not movies:
            console.print("[yellow]No movies to delete[/yellow]")
            return results

        # Determine delete_files parameter (opposite of keep_files)
        delete_files = not keep_files

        # Show deletion mode
        if dry_run:
            console.print("[yellow]DRY RUN MODE - No actual deletions will occur[/yellow]")

        file_action = "KEEPING files on disk" if keep_files else "DELETING files from disk"
        console.print(f"[cyan]Deletion mode: {file_action}[/cyan]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                f"[cyan]{'Simulating deletion of' if dry_run else 'Deleting'} {len(movies)} movies...",
                total=len(movies)
            )

            for movie in movies:
                movie_title = movie.get('title', 'Unknown Title')
                movie_id = movie.get('id')

                if not movie_id:
                    console.print(f"[red]✗ {movie_title}: Missing movie ID[/red]")
                    results["failed"].append(movie_title)
                    progress.advance(task)
                    continue

                try:
                    if dry_run:
                        # Dry run: just log what would happen
                        action = "delete files and add exclusion" if delete_files else "remove from library (keep files) and add exclusion"
                        console.print(f"[blue]Would {action} for: {movie_title} (ID: {movie_id})[/blue]")
                        results["deleted"].append(movie_title)
                    else:
                        # Actually delete the movie
                        self.client.delete_movie(
                            movie_id=movie_id,
                            delete_files=delete_files,
                            add_exclusion=True
                        )
                        console.print(f"[green]✓ Deleted: {movie_title}[/green]")
                        results["deleted"].append(movie_title)

                except RadarrAPIError as e:
                    console.print(f"[red]✗ Failed to delete {movie_title}: {e.message}[/red]")
                    results["failed"].append(movie_title)
                except Exception as e:
                    console.print(f"[red]✗ Unexpected error deleting {movie_title}: {str(e)}[/red]")
                    results["failed"].append(movie_title)

                progress.advance(task)

        # Print summary
        console.print()
        console.print("[bold]Deletion Summary:[/bold]")
        console.print(f"  [green]Deleted: {len(results['deleted'])}[/green]")
        console.print(f"  [red]Failed: {len(results['failed'])}[/red]")
        console.print(f"  [yellow]Skipped: {len(results['skipped'])}[/yellow]")

        return results

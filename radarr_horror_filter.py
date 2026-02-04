#!/usr/bin/env python3
"""
Radarr Horror Filter - Main CLI interface for managing horror movies in Radarr.
"""
import argparse
import os
import sys
from typing import List, Dict, Any

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from radarr_client import RadarrClient, RadarrAPIError
from scanner import MovieScanner
from filter import GenreFilter
from deleter import MovieDeleter
from keep_list import KeepListManager

# Optional dependency for interactive selection
try:
    import questionary
    from questionary import Choice
    QUESTIONARY_AVAILABLE = True
except ImportError:
    questionary = None  # type: ignore
    Choice = None  # type: ignore
    QUESTIONARY_AVAILABLE = False

console = Console()


def bytes_to_gb(size_bytes: int) -> str:
    """
    Convert bytes to GB with 2 decimal places.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "12.34 GB")
    """
    gb = size_bytes / (1024 ** 3)
    return f"{gb:.2f} GB"


def display_movies_table(movies: List[Dict[str, Any]], verbose: bool = False, keep_list: KeepListManager = None) -> None:
    """
    Display movies in a formatted table.

    Args:
        movies: List of movie dictionaries
        verbose: Whether to show detailed output
        keep_list: Optional KeepListManager to show keep status
    """
    if not movies:
        console.print("[yellow]No movies found[/yellow]")
        return

    table = Table(title="Movies Found")
    table.add_column("Title", style="cyan", no_wrap=False)
    table.add_column("Year", style="magenta", justify="center")
    table.add_column("Size", style="green", justify="right")
    table.add_column("Genres", style="blue", no_wrap=False)
    if keep_list:
        table.add_column("Kept", style="yellow", justify="center")

    for movie in movies:
        title = movie.get('title', 'Unknown')
        year = str(movie.get('year', 'N/A'))
        size = bytes_to_gb(movie.get('sizeOnDisk', 0))
        genres = ', '.join(movie.get('genres', []))

        if keep_list:
            kept = "Y" if keep_list.is_kept(movie.get('id')) else ""
            table.add_row(title, year, size, genres, kept)
        else:
            table.add_row(title, year, size, genres)

    console.print(table)

    if verbose:
        total_size = sum(movie.get('sizeOnDisk', 0) for movie in movies)
        console.print(f"\n[bold]Total: {len(movies)} movies, {bytes_to_gb(total_size)}[/bold]")


def interactive_keep_selection(
    movies: List[Dict[str, Any]],
    keep_list: KeepListManager
) -> List[Dict[str, Any]]:
    """
    Display interactive checkbox for selecting movies to keep.

    Args:
        movies: List of movie dictionaries from Radarr
        keep_list: KeepListManager instance

    Returns:
        List of newly selected movies (excludes already-kept)

    Raises:
        RuntimeError: If questionary is not installed
    """
    if not QUESTIONARY_AVAILABLE:
        raise RuntimeError(
            "Interactive selection requires the 'questionary' package. "
            "Install it with: pip install questionary"
        )

    if not movies:
        return []

    choices = []
    for movie in movies:
        movie_id = movie.get('id')
        title = movie.get('title', 'Unknown')
        year = movie.get('year', 'N/A')
        is_already_kept = keep_list.is_kept(movie_id)

        display = f"{title} ({year})"
        if is_already_kept:
            display = f"{title} ({year}) [already kept]"

        choices.append(Choice(
            title=display,
            value=movie,
            checked=is_already_kept
        ))

    console.print("\n[bold cyan]Select movies to add to keep list:[/bold cyan]")
    console.print("[dim]Use arrow keys to navigate, Space to select, Enter to confirm[/dim]\n")

    selected = questionary.checkbox(
        "",
        choices=choices,
        instruction="(Space to toggle, Enter to confirm)"
    ).ask()

    # User cancelled (Ctrl+C)
    if selected is None:
        return []

    # Filter out movies that were already kept
    newly_selected = [
        m for m in selected
        if not keep_list.is_kept(m.get('id'))
    ]

    return newly_selected


def get_confirmation(
    movie_count: int,
    total_size_bytes: int,
    keep_files: bool,
    yes_flag: bool
) -> bool:
    """
    Get user confirmation for deletion with appropriate warning message.

    Args:
        movie_count: Number of movies to delete
        total_size_bytes: Total size of movies in bytes
        keep_files: Whether files will be kept on disk
        yes_flag: Skip confirmation if True

    Returns:
        True if user confirms, False otherwise
    """
    if yes_flag:
        return True

    size_gb = bytes_to_gb(total_size_bytes)

    if keep_files:
        # Files will be preserved
        console.print(f"\n[yellow]This will remove {movie_count} movies ({size_gb}) from Radarr.[/yellow]")
        console.print("[yellow]Files will be preserved on disk.[/yellow]\n")
    else:
        # Files will be deleted - show strong warning
        console.print(f"\n[bold red]WARNING: This will permanently delete {movie_count} movies ({size_gb}) from your server.[/bold red]")
        console.print("[bold red]Files will be removed from disk and cannot be recovered.[/bold red]\n")

    return Confirm.ask("Continue?", default=False)


def cmd_scan(args: argparse.Namespace) -> int:
    """
    Execute the scan command to find movies by genre.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Initialize client
        client = RadarrClient(args.url, args.api_key)

        # Test connection
        if args.verbose:
            console.print("[cyan]Testing connection to Radarr...[/cyan]")
        status = client.test_connection()
        if args.verbose:
            console.print(f"[green]Connected to Radarr version {status.get('version', 'unknown')}[/green]\n")

        # Scan library
        scanner = MovieScanner(client)
        all_movies = scanner.scan()

        if not all_movies:
            console.print("[yellow]No movies found in library[/yellow]")
            return 0

        # Filter by genre
        genre_filter = GenreFilter(args.genre)
        filtered_movies = genre_filter.filter(all_movies)

        # Display results
        console.print(f"\n[bold]Movies with genre: {args.genre}[/bold]\n")
        keep_list = KeepListManager()
        display_movies_table(filtered_movies, verbose=args.verbose, keep_list=keep_list)

        # Show keep list summary
        kept_count = sum(1 for m in filtered_movies if keep_list.is_kept(m.get('id')))
        if kept_count > 0:
            console.print(f"[yellow]{kept_count} movies in keep list[/yellow]")

        # Interactive keep selection
        if args.interactive:
            try:
                newly_kept = interactive_keep_selection(filtered_movies, keep_list)

                if newly_kept:
                    for movie in newly_kept:
                        keep_list.add(movie['id'], movie['title'])
                        console.print(f"[green]Added to keep list: {movie['title']}[/green]")
                    console.print(f"\n[bold green]Added {len(newly_kept)} movies to keep list[/bold green]")
                else:
                    console.print("[yellow]No new movies selected[/yellow]")
            except RuntimeError as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
                return 1

        # Show statistics
        stats = genre_filter.get_statistics(all_movies, filtered_movies)
        console.print(f"\n[bold cyan]Summary:[/bold cyan]")
        console.print(f"  Found {stats['filtered_count']} {args.genre} movies out of {stats['total_count']} total")
        console.print(f"  {args.genre} movies use {bytes_to_gb(stats['filtered_size_bytes'])} of {bytes_to_gb(stats['total_size_bytes'])} total storage")

        return 0

    except RadarrAPIError as e:
        console.print(f"[bold red]Radarr API Error:[/bold red] {e.message}")
        if args.verbose:
            console.print(f"[dim]Status Code: {e.status_code}[/dim]")
            console.print(f"[dim]Endpoint: {e.endpoint}[/dim]")
        return 1
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        if args.verbose:
            import traceback
            console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
        return 1


def cmd_delete(args: argparse.Namespace) -> int:
    """
    Execute the delete command to remove movies by genre.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Initialize client
        client = RadarrClient(args.url, args.api_key)

        # Test connection
        if args.verbose:
            console.print("[cyan]Testing connection to Radarr...[/cyan]")
        status = client.test_connection()
        if args.verbose:
            console.print(f"[green]Connected to Radarr version {status.get('version', 'unknown')}[/green]\n")

        # Scan library
        scanner = MovieScanner(client)
        all_movies = scanner.scan()

        if not all_movies:
            console.print("[yellow]No movies found in library[/yellow]")
            return 0

        # Filter by genre
        genre_filter = GenreFilter(args.genre)
        filtered_movies = genre_filter.filter(all_movies)

        if not filtered_movies:
            console.print(f"[yellow]No {args.genre} movies found[/yellow]")
            return 0

        # Filter out kept movies (unless --ignore-keep-list)
        kept_movies = []
        if not args.ignore_keep_list:
            keep_list = KeepListManager()
            kept_movies = [m for m in filtered_movies if keep_list.is_kept(m.get('id'))]
            filtered_movies = keep_list.filter_kept(filtered_movies)

            if kept_movies:
                console.print(f"\n[yellow]Skipped (keep list): {len(kept_movies)} movies[/yellow]")
                for m in kept_movies:
                    console.print(f"  [dim]- {m.get('title')}[/dim]")

        if not filtered_movies:
            console.print(f"[yellow]No {args.genre} movies to delete (all are in keep list)[/yellow]")
            return 0

        # Show what will be deleted
        console.print(f"\n[bold]Movies to be deleted (genre: {args.genre}):[/bold]\n")
        display_movies_table(filtered_movies, verbose=args.verbose)

        # Calculate totals
        total_size = sum(movie.get('sizeOnDisk', 0) for movie in filtered_movies)
        movie_count = len(filtered_movies)

        # Determine mode
        dry_run = not args.execute
        if dry_run:
            console.print("\n[yellow bold]DRY RUN MODE[/yellow bold]")
            console.print("[yellow]Run with --execute to perform actual deletions[/yellow]")
        else:
            # Get confirmation for actual deletion
            if not get_confirmation(movie_count, total_size, args.keep_files, args.yes):
                console.print("[yellow]Operation cancelled[/yellow]")
                return 0

        # Perform deletion
        deleter = MovieDeleter(client)
        results = deleter.delete_movies(
            movies=filtered_movies,
            keep_files=args.keep_files,
            dry_run=dry_run
        )

        # Show final summary
        console.print("\n[bold green]Operation completed[/bold green]")
        if results['deleted']:
            deleted_size = sum(
                movie.get('sizeOnDisk', 0)
                for movie in filtered_movies
                if movie.get('title') in results['deleted']
            )
            action = "Removed from library" if args.keep_files else "Deleted"
            console.print(f"{action}: {len(results['deleted'])} movies ({bytes_to_gb(deleted_size)})")

        if results['failed']:
            console.print(f"[red]Failed: {len(results['failed'])} movies[/red]")
            if args.verbose:
                for title in results['failed']:
                    console.print(f"  [red]- {title}[/red]")

        return 0 if not results['failed'] else 1

    except RadarrAPIError as e:
        console.print(f"[bold red]Radarr API Error:[/bold red] {e.message}")
        if args.verbose:
            console.print(f"[dim]Status Code: {e.status_code}[/dim]")
            console.print(f"[dim]Endpoint: {e.endpoint}[/dim]")
        return 1
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        if args.verbose:
            import traceback
            console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
        return 1


def cmd_keep(args: argparse.Namespace) -> int:
    """Handle keep list commands."""
    keep_list = KeepListManager()

    if args.keep_command == 'add':
        # Need to fetch movie from Radarr to validate and get title
        if not args.id and not args.title:
            console.print("[red]Error: Must provide either movie ID or --title[/red]")
            return 1

        try:
            client = RadarrClient(args.url, args.api_key)
            all_movies = client.get_movies()

            if args.id:
                # Find by ID
                movie = next((m for m in all_movies if m.get('id') == args.id), None)
                if not movie:
                    console.print(f"[red]Error: Movie with ID {args.id} not found in Radarr[/red]")
                    return 1
            else:
                # Find by title (exact, case-insensitive)
                title_lower = args.title.lower()
                matches = [m for m in all_movies if m.get('title', '').lower() == title_lower]
                if not matches:
                    console.print(f"[red]Error: No movie found with title '{args.title}'[/red]")
                    return 1
                if len(matches) > 1:
                    console.print(f"[red]Error: Multiple movies found with title '{args.title}'. Use movie ID instead.[/red]")
                    for m in matches:
                        console.print(f"  ID {m['id']}: {m['title']} ({m.get('year', 'N/A')})")
                    return 1
                movie = matches[0]

            # Add to keep list (check if already kept first)
            if keep_list.is_kept(movie['id']):
                console.print(f"[yellow]'{movie['title']}' is already in the keep list[/yellow]")
            else:
                keep_list.add(movie['id'], movie['title'])
                console.print(f"[green]Added to keep list: {movie['title']} (ID: {movie['id']})[/green]")
            return 0

        except RadarrAPIError as e:
            console.print(f"[red]Radarr API Error: {e.message}[/red]")
            return 1

    elif args.keep_command == 'remove':
        if not args.id and not args.title:
            console.print("[red]Error: Must provide either movie ID or --title[/red]")
            return 1

        if args.id:
            removed = keep_list.remove(movie_id=args.id)
            if removed:
                console.print(f"[green]Removed movie ID {args.id} from keep list[/green]")
            else:
                console.print(f"[yellow]Movie ID {args.id} was not in the keep list[/yellow]")
        else:
            removed = keep_list.remove(title=args.title)
            if removed:
                console.print(f"[green]Removed '{args.title}' from keep list[/green]")
            else:
                console.print(f"[yellow]'{args.title}' was not in the keep list[/yellow]")
        return 0

    elif args.keep_command == 'list':
        movies = keep_list.list_all()
        if not movies:
            console.print("[yellow]Keep list is empty[/yellow]")
            return 0

        table = Table(title="Keep List")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Title", style="green")
        table.add_column("Added", style="dim")

        for movie in movies:
            added_at = movie.get('added_at', 'N/A')[:10]  # Just date portion
            table.add_row(str(movie['id']), movie['title'], added_at)

        console.print(table)
        console.print(f"\n[bold]Total: {len(movies)} movies in keep list[/bold]")
        return 0

    elif args.keep_command == 'clear':
        movies = keep_list.list_all()
        if not movies:
            console.print("[yellow]Keep list is already empty[/yellow]")
            return 0

        if not args.yes:
            if not Confirm.ask(f"Are you sure you want to clear {len(movies)} movies from keep list?", default=False):
                console.print("[yellow]Operation cancelled[/yellow]")
                return 0

        keep_list.clear()
        console.print(f"[green]Cleared {len(movies)} movies from keep list[/green]")
        return 0

    else:
        console.print("[red]Error: Unknown keep command[/red]")
        return 1


def main() -> int:
    """
    Main entry point for the CLI application.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Load environment variables from .env file
    load_dotenv()

    # Create main parser
    parser = argparse.ArgumentParser(
        description="Radarr Horror Filter - Manage horror movies in your Radarr library",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global arguments
    parser.add_argument(
        '--url',
        default=os.getenv('RADARR_URL'),
        help='Radarr URL (overrides RADARR_URL env var)'
    )
    parser.add_argument(
        '--api-key',
        default=os.getenv('RADARR_API_KEY'),
        help='Radarr API key (overrides RADARR_API_KEY env var)'
    )

    # Create subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Scan command
    scan_parser = subparsers.add_parser(
        'scan',
        help='Scan and list movies by genre'
    )
    scan_parser.add_argument(
        '--genre',
        default='Horror',
        help='Genre to filter (default: Horror)'
    )
    scan_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )
    scan_parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Interactively select movies to add to keep list'
    )

    # Delete command
    delete_parser = subparsers.add_parser(
        'delete',
        help='Delete movies by genre'
    )
    delete_parser.add_argument(
        '--genre',
        default='Horror',
        help='Genre to filter (default: Horror)'
    )
    delete_parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually perform deletions (default: dry-run)'
    )
    delete_parser.add_argument(
        '--keep-files',
        action='store_true',
        help='Keep files on disk (default: delete files)'
    )
    delete_parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt'
    )
    delete_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )
    delete_parser.add_argument(
        '--ignore-keep-list',
        action='store_true',
        help='Ignore keep list and include all matching movies'
    )

    # Keep command with subcommands
    keep_parser = subparsers.add_parser('keep', help='Manage keep list')
    keep_subparsers = keep_parser.add_subparsers(dest='keep_command', help='Keep list action')

    # keep add
    keep_add_parser = keep_subparsers.add_parser('add', help='Add movie to keep list')
    keep_add_parser.add_argument('id', nargs='?', type=int, help='Movie ID to add')
    keep_add_parser.add_argument('--title', '-t', help='Movie title to add (exact match)')

    # keep remove
    keep_remove_parser = keep_subparsers.add_parser('remove', help='Remove movie from keep list')
    keep_remove_parser.add_argument('id', nargs='?', type=int, help='Movie ID to remove')
    keep_remove_parser.add_argument('--title', '-t', help='Movie title to remove')

    # keep list
    keep_subparsers.add_parser('list', help='List all kept movies')

    # keep clear
    keep_clear_parser = keep_subparsers.add_parser('clear', help='Clear entire keep list')
    keep_clear_parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')

    # Parse arguments
    args = parser.parse_args()

    # Validate required global arguments
    if not args.url:
        console.print("[bold red]Error:[/bold red] Radarr URL not provided")
        console.print("Set RADARR_URL environment variable or use --url flag")
        return 1

    if not args.api_key:
        console.print("[bold red]Error:[/bold red] Radarr API key not provided")
        console.print("Set RADARR_API_KEY environment variable or use --api-key flag")
        return 1

    # Route to appropriate command handler
    if args.command == 'scan':
        return cmd_scan(args)
    elif args.command == 'delete':
        return cmd_delete(args)
    elif args.command == 'keep':
        return cmd_keep(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())

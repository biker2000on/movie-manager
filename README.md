# Radarr Horror Filter

A command-line tool to identify, preview, and delete horror movies from your Radarr library. Automatically adds deleted movies to Radarr's exclusion list to prevent future imports.

## Overview

The Radarr Horror Filter helps you manage your media library by:

- **Scanning** your Radarr library for movies in specific genres
- **Previewing** deletion actions before executing them (dry-run mode)
- **Deleting** unwanted movies with optional file preservation
- **Excluding** deleted movies to prevent re-import from lists (IMDb Popular, Top 250, etc.)

## Prerequisites

- **Python 3.8** or higher
- **uv** - Python package manager ([installation guide](https://docs.astral.sh/uv/))
- **Radarr v3+** with API access enabled

## Installation

Clone or download the project, then install dependencies using `uv`:

```bash
uv sync
```

This installs all required packages including `requests`, `python-dotenv`, and `rich` for beautiful CLI output.

## Configuration

### Environment Variables

Copy the example environment file and configure your Radarr connection:

```bash
cp .env.example .env
```

Edit `.env` and set your Radarr details:

```env
RADARR_URL=http://localhost:7878
RADARR_API_KEY=your_api_key_here
```

**Finding your Radarr API Key:**
1. Open Radarr web interface
2. Go to Settings → General
3. Enable "Advanced Settings" (if not already enabled)
4. Copy your API key from the API Key field

### Alternative: Command-line Overrides

You can override environment variables using command-line flags:

```bash
uv run radarr_horror_filter.py scan --url http://radarr.example.com:7878 --api-key YOUR_KEY
```

## Usage

### Scan Command

List all horror movies in your library:

```bash
uv run radarr_horror_filter.py scan
```

**Example output:**
```
Testing connection to Radarr...
Connected to Radarr version 4.0.0

Movies with genre: Horror

┌──────────────────────┬──────┬──────────┬─────────────────┐
│ Title                │ Year │ Size     │ Genres          │
├──────────────────────┼──────┼──────────┼─────────────────┤
│ Saw                  │ 2004 │ 1.86 GB  │ Horror, Thriller│
│ The Conjuring        │ 2013 │ 1.40 GB  │ Horror          │
│ Insidious            │ 2010 │ 2.15 GB  │ Horror, Thriller│
└──────────────────────┴──────┴──────────┴─────────────────┘

Summary:
  Found 3 horror movies out of 127 total
  Horror movies use 5.41 GB of 850.20 GB total storage
```

#### Scan Other Genres

Scan for any genre, not just horror:

```bash
uv run radarr_horror_filter.py scan --genre Thriller
uv run radarr_horror_filter.py scan --genre Documentary
uv run radarr_horror_filter.py scan --genre Action
```

#### Verbose Output

Show detailed connection and processing information:

```bash
uv run radarr_horror_filter.py scan --verbose
# or
uv run radarr_horror_filter.py scan -v
```

### Delete Command

#### Preview Deletions (Dry-Run Mode)

By default, the delete command runs in dry-run mode to show what will happen:

```bash
uv run radarr_horror_filter.py delete
```

This displays the movies that would be deleted without making any changes:

```
Testing connection to Radarr...
Connected to Radarr version 4.0.0

Movies to be deleted (genre: Horror):

┌──────────────────────┬──────┬──────────┬──────────┐
│ Title                │ Year │ Size     │ Genres   │
├──────────────────────┼──────┼──────────┼──────────┤
│ Saw                  │ 2004 │ 1.86 GB  │ Horror   │
│ The Conjuring        │ 2013 │ 1.40 GB  │ Horror   │
└──────────────────────┴──────┴──────────┴──────────┘

DRY RUN MODE
Run with --execute to perform actual deletions
```

#### Execute Deletions

**WARNING:** This permanently deletes files from your server. Be careful!

```bash
uv run radarr_horror_filter.py delete --execute
```

You will be prompted to confirm:

```
WARNING: This will permanently delete 2 movies (3.26 GB) from your server.
Files will be removed from disk and cannot be recovered.

Continue? [y/N]: y

Deleting 2 movies...
✓ Deleted: Saw
✓ Deleted: The Conjuring

Operation completed
Deleted: 2 movies (3.26 GB)
```

#### Keep Files on Disk

Remove movies from Radarr while preserving the actual files:

```bash
uv run radarr_horror_filter.py delete --execute --keep-files
```

This is useful if you want to manually manage the files or keep them archived separately:

```
This will remove 2 movies (3.26 GB) from Radarr.
Files will be preserved on disk.

Continue? [y/N]: y

Deleting 2 movies...
✓ Deleted: Saw
✓ Deleted: The Conjuring

Operation completed
Removed from library: 2 movies (3.26 GB)
```

#### Skip Confirmation Prompt

For automation or scripting, skip the confirmation prompt with `--yes`:

```bash
uv run radarr_horror_filter.py delete --execute --yes
```

This is useful in cron jobs or CI/CD pipelines:

```bash
# Automatically delete all horror movies without prompting
uv run radarr_horror_filter.py delete --execute --yes
```

#### Delete Other Genres

Delete movies from any genre:

```bash
uv run radarr_horror_filter.py delete --execute --genre Thriller
```

### Combined Examples

**Scan with verbose output:**
```bash
uv run radarr_horror_filter.py scan --genre Action --verbose
```

**Delete documentaries and keep files:**
```bash
uv run radarr_horror_filter.py delete --genre Documentary --execute --keep-files
```

**Delete in silent mode (no confirmation):**
```bash
uv run radarr_horror_filter.py delete --execute --yes
```

## IMPORTANT WARNING

⚠️ **By default, `--execute` DELETES FILES FROM DISK.**

Files deleted through the Radarr Horror Filter cannot be recovered. If you want to remove movies from Radarr without deleting the files, always use the `--keep-files` flag:

```bash
# SAFE: Removes from Radarr, keeps files
uv run radarr_horror_filter.py delete --execute --keep-files

# DANGEROUS: Permanently deletes files
uv run radarr_horror_filter.py delete --execute
```

## How Exclusions Work

When you delete a movie using this tool, it is automatically added to Radarr's import exclusion list. This prevents the movie from being re-imported if it appears in:

- IMDb Popular list
- IMDb Top 250 list
- Any other configured import lists

**Example scenario:**
1. You delete the movie "Scary Movie" with `--execute`
2. The tool removes the movie and adds it to Radarr's exclusions
3. Later, "Scary Movie" appears on the IMDb Top 250 list
4. Radarr skips it automatically due to the exclusion
5. You don't have to delete it again

This is especially useful for recurring lists that update regularly.

## Troubleshooting

### Connection Errors

**Error:** `Connection error: Connection refused`

**Solution:**
- Verify Radarr is running: `http://your-radarr-url:7878`
- Check `RADARR_URL` in your `.env` file
- Ensure the URL includes the port (usually 7878)

```bash
# Test connection manually
curl http://localhost:7878/api/v3/system/status?apikey=YOUR_KEY
```

### 401 Unauthorized Error

**Error:** `Radarr API Error 401 at /api/v3/system/status: Unauthorized`

**Solution:**
- Verify your API key in Radarr Settings → General
- Check that `RADARR_API_KEY` in `.env` is correct (no extra spaces)
- API key is case-sensitive

### No Movies Found

**Error:** `No movies found in library`

**Solutions:**
- Verify Radarr has imported movies
- Check that movies have genre tags assigned
- For custom genres, ensure the genre name matches exactly (case-insensitive matching is automatic)

### Movies Not Showing for a Genre

**Possible causes:**
- The movies don't have that genre tag in Radarr
- The genre name doesn't match (try variations like "Sci-Fi" vs "Science Fiction")

**Debug:** Use scan with verbose output to see all genres:

```bash
uv run radarr_horror_filter.py scan --verbose
```

## Testing

Run the test suite to verify functionality:

```bash
uv run pytest test_filter.py -v
```

**Expected output:**
```
test_filter.py::TestGenreFilter::test_filters_horror_movies PASSED
test_filter.py::TestGenreFilter::test_case_insensitive_matching PASSED
test_filter.py::TestGenreFilter::test_empty_movie_list PASSED
test_filter.py::TestMovieDeleter::test_dry_run_makes_no_api_calls PASSED
test_filter.py::TestMovieDeleter::test_delete_files_by_default PASSED
test_filter.py::TestMovieDeleter::test_keep_files_when_flag_set PASSED
test_filter.py::TestRadarrClient::test_test_connection_success PASSED
test_filter.py::TestRadarrClient::test_handles_204_no_content PASSED

======================== 15 passed in 0.24s ========================
```

## Architecture

### Components

- **radarr_horror_filter.py** - Main CLI interface with argument parsing
- **radarr_client.py** - Radarr API client with retry logic and error handling
- **scanner.py** - Movie library scanning and data processing
- **filter.py** - Genre-based filtering logic
- **deleter.py** - Movie deletion with progress tracking
- **test_filter.py** - Comprehensive test suite

### Data Flow

```
User Command
    ↓
radarr_horror_filter.py (CLI parsing)
    ↓
RadarrClient (API connection + retry logic)
    ↓
MovieScanner (fetch all movies)
    ↓
GenreFilter (filter by genre)
    ↓
MovieDeleter (delete + add exclusions)
    ↓
Output (tables, confirmations, results)
```

## API Reference

### Scan Command

```
uv run radarr_horror_filter.py scan [OPTIONS]

Options:
  --genre GENRE          Genre to filter (default: Horror)
  --verbose, -v          Show detailed output
  --url URL              Radarr URL (overrides RADARR_URL env var)
  --api-key KEY          Radarr API key (overrides RADARR_API_KEY env var)
```

### Delete Command

```
uv run radarr_horror_filter.py delete [OPTIONS]

Options:
  --genre GENRE          Genre to filter (default: Horror)
  --execute              Actually perform deletions (default: dry-run)
  --keep-files           Keep files on disk (default: delete files)
  --yes, -y              Skip confirmation prompt
  --verbose, -v          Show detailed output
  --url URL              Radarr URL (overrides RADARR_URL env var)
  --api-key KEY          Radarr API key (overrides RADARR_API_KEY env var)
```

## Performance Notes

- **Large libraries** (1000+ movies): Scanning takes 10-30 seconds depending on network
- **Deletion**: Each movie deletion is ~1 second plus API latency
- **Retry logic**: Failed requests automatically retry with exponential backoff
- **Progress tracking**: Visual progress bar for long operations

## Requirements

- Python 3.8+
- `requests` - HTTP library
- `python-dotenv` - Environment variable management
- `rich` - Beautiful CLI output
- `pytest` - Testing framework

All dependencies are managed by `uv sync`.

## License

[Specify your license here if needed]

## Contributing

[Add contribution guidelines if desired]

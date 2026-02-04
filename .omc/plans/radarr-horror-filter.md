# Radarr Horror Movie Filter - Implementation Plan

## Context

### Original Request
Create a script/tool to manage a Radarr movie collection that:
1. Deletes all horror movies from the collection
2. Prevents Radarr from downloading horror movies in the future while maintaining IMDb Popular and IMDb Top 250 list imports

### Interview Summary
- Fresh project with no existing code
- User has IMDb Popular and IMDb Top 250 lists imported in Radarr
- Need to filter out horror genre from these imports
- Must be safe with dry-run and confirmation prompts
- **User wants files deleted from server by default** (not just removed from Radarr database)

### Research Findings
- Radarr API v3 provides all necessary endpoints
- Key limitation: IMDb lists have NO native genre filtering in Radarr
- Solution: Use API to delete horror movies with `addImportExclusion=true` to prevent re-import
- Exclusions persist and automatically block future horror imports from any list

---

## Work Objectives

### Core Objective
Build a Python CLI tool that connects to Radarr API to identify, delete, and exclude horror movies from the collection.

### Deliverables
1. **Python CLI script** (`radarr_horror_filter.py`) - Main tool
2. **Configuration file** (`.env.example`) - Template for API credentials
3. **Requirements file** (`requirements.txt`) - Python dependencies
4. **README** (`README.md`) - Usage documentation
5. **Unit tests** (`test_filter.py`) - Tests for filter and delete logic

### Definition of Done
- [ ] Tool connects to Radarr API and authenticates successfully
- [ ] Tool identifies all movies with "Horror" genre
- [ ] Dry-run mode shows what would be deleted without making changes
- [ ] Delete mode removes movies AND deletes files from disk by default
- [ ] `--keep-files` flag available to preserve files on disk
- [ ] User confirmation required before destructive actions
- [ ] Clear output showing progress and results
- [ ] Works on Windows (user's platform)
- [ ] Unit tests pass with mocked API responses

---

## Guardrails

### Must Have
- Dry-run mode as default (safe by default)
- Explicit `--execute` flag required for actual deletion
- **File deletion from disk is the DEFAULT behavior when `--execute` is used**
- `--keep-files` flag to optionally preserve files on disk (remove from Radarr only)
- Confirmation prompt before deletion (bypassable with `--yes`)
- **Confirmation prompt must clearly warn that files will be deleted from disk**
- Clear logging of all actions
- Error handling for API failures with retry logic
- Support for custom Radarr URL and API key via environment variables

### Must NOT Have
- No automatic execution without user confirmation
- No hardcoded credentials in source code
- No modification of Radarr settings beyond movie management
- No dependencies on external services beyond Radarr API

---

## Task Flow

```
[Setup] --> [API Client] --> [Movie Scanner] --> [Filter Logic] --> [Delete Handler] --> [CLI Interface] --> [Tests]
    |           |                  |                  |                   |                    |               |
    v           v                  v                  v                   v                    v               v
 .env       connect()         get_movies()      filter_horror()     delete_movie()         main()         pytest
 deps       auth+retry        list all           genre match         exclusions            argparse       mocked
```

### Dependency Graph
```
Task 1 (Setup)
    |
    v
Task 2 (API Client) <-- no dependencies on other tasks
    |
    v
Task 3 (Movie Scanner) <-- depends on Task 2
    |
    v
Task 4 (Filter Logic) <-- depends on Task 3
    |
    v
Task 5 (Delete Handler) <-- depends on Task 2, Task 4
    |
    v
Task 6 (CLI Interface) <-- depends on all above
    |
    v
Task 7 (Documentation) <-- depends on Task 6
    |
    v
Task 8 (Unit Tests) <-- depends on Tasks 2, 4, 5
```

---

## Detailed TODOs

### Task 1: Project Setup
**Objective:** Initialize Python project with dependencies

**Subtasks:**
- [ ] 1.1 Create `requirements.txt` with dependencies:
  ```
  requests>=2.28.0
  python-dotenv>=1.0.0
  rich>=13.0.0
  pytest>=7.0.0
  pytest-mock>=3.10.0
  ```
- [ ] 1.2 Create `pyproject.toml` with Python version requirement:
  ```toml
  [project]
  name = "radarr-horror-filter"
  version = "1.0.0"
  requires-python = ">=3.8"
  ```
- [ ] 1.3 Create `.env.example` template file:
  ```
  RADARR_URL=http://localhost:7878
  RADARR_API_KEY=your_api_key_here
  ```
- [ ] 1.4 Create `.gitignore` to exclude `.env`, `__pycache__`, `.pytest_cache`

**Acceptance Criteria:**
- `pip install -r requirements.txt` succeeds
- `.env.example` contains all required variables with placeholder values
- `.gitignore` prevents accidental credential commits
- `pyproject.toml` specifies Python 3.8+ requirement

---

### Task 2: Radarr API Client
**Objective:** Create reusable API client class with retry logic

**File:** `radarr_client.py`

**Subtasks:**
- [ ] 2.1 Create `RadarrAPIError` custom exception class with attributes: `status_code`, `message`, `endpoint`
- [ ] 2.2 Create `RadarrClient` class with constructor accepting URL and API key
- [ ] 2.3 Implement `_request()` method for authenticated API calls with retry logic:
  - 3 retries for 5xx errors and connection timeouts
  - Exponential backoff: 1s, 2s, 4s between retries
  - Raise `RadarrAPIError` after all retries exhausted
- [ ] 2.4 Implement `test_connection()` using `GET /api/v3/system/status` endpoint:
  - Returns `True` if status 200 and response contains `version` field
  - Raises `RadarrAPIError` with meaningful message on failure
- [ ] 2.5 Implement `get_movies()` returning list of all movies
- [ ] 2.6 Implement `delete_movie(id, delete_files, add_exclusion)` method
- [ ] 2.7 Implement `get_exclusions()` to list current exclusions

**API Details:**
```python
# Headers required
headers = {"X-Api-Key": api_key}

# Endpoints
GET  /api/v3/system/status    # Test connection (returns version, appName)
GET  /api/v3/movie            # List all movies
DELETE /api/v3/movie/{id}     # Delete single movie
  ?deleteFiles=true           # Also delete files from disk
  &addImportExclusion=true    # Add to exclusion list
GET  /api/v3/exclusions       # List exclusions
```

**Retry Implementation:**
```python
import time
from requests.exceptions import ConnectionError, Timeout

MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # seconds

def _request(self, method, endpoint, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            if response.status_code >= 500:
                raise RadarrAPIError(response.status_code, "Server error", endpoint)
            return response
        except (ConnectionError, Timeout, RadarrAPIError) as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
                continue
            raise RadarrAPIError(0, f"Failed after {MAX_RETRIES} retries: {e}", endpoint)
```

**Acceptance Criteria:**
- `test_connection()` returns True with valid credentials, raises `RadarrAPIError` otherwise
- `get_movies()` returns list of movie dicts with `id`, `title`, `genres` fields
- `delete_movie()` successfully removes movie and returns confirmation
- Retry logic handles transient failures (5xx, timeouts) with exponential backoff
- All API errors are caught and re-raised as `RadarrAPIError` with meaningful messages

---

### Task 3: Movie Scanner
**Objective:** Fetch and parse all movies from Radarr

**File:** `scanner.py`

**Subtasks:**
- [ ] 3.1 Create `MovieScanner` class accepting `RadarrClient`
- [ ] 3.2 Implement `scan()` method returning structured movie list
- [ ] 3.3 Parse movie data into dataclass/dict with: id, title, year, genres, hasFile, sizeOnDisk
- [ ] 3.4 Add progress indicator for large libraries

**Acceptance Criteria:**
- `scan()` returns list of movie objects with all required fields
- Progress shown during scan (using rich progress bar)
- Handles empty library gracefully

---

### Task 4: Horror Filter Logic
**Objective:** Identify horror movies from scanned library

**File:** `filter.py`

**Subtasks:**
- [ ] 4.1 Create `HorrorFilter` class
- [ ] 4.2 Implement `filter(movies)` returning only horror movies
- [ ] 4.3 Genre matching should be case-insensitive
- [ ] 4.4 Support `--genre` parameter for filtering other genres (e.g., `--genre Thriller`)
- [ ] 4.5 Generate statistics: total movies, horror count, disk space to reclaim

**Acceptance Criteria:**
- Filter correctly identifies movies with "Horror" in genres array
- Case variations ("horror", "HORROR", "Horror") all match
- Returns accurate count and size statistics
- `--genre` flag allows filtering any genre, defaults to "Horror"

---

### Task 5: Delete Handler
**Objective:** Safely delete movies with exclusion support

**File:** `deleter.py`

**Subtasks:**
- [ ] 5.1 Create `MovieDeleter` class accepting `RadarrClient`
- [ ] 5.2 Implement `delete_movies(movies, keep_files, dry_run)` method with return type:
  ```python
  def delete_movies(...) -> dict:
      """
      Args:
          movies: List of movies to delete
          keep_files: If True, preserve files on disk (default: False = delete files)
          dry_run: If True, don't actually delete anything

      Returns:
          {
              "deleted": ["Movie Title 1", "Movie Title 2"],  # Successfully deleted
              "failed": ["Movie Title 3"],                     # API errors
              "skipped": ["Movie Title 4"]                     # Already excluded
          }
      """
  ```
- [ ] 5.3 In dry-run mode: log what would be deleted, make no API calls
- [ ] 5.4 In execute mode: call delete API for each movie with `deleteFiles=true` by default
- [ ] 5.5 If `keep_files=True`, call delete API with `deleteFiles=false`
- [ ] 5.6 Always add to exclusion list (`addImportExclusion=true`)
- [ ] 5.7 Track and report: successful deletes, failures, skipped
- [ ] 5.8 Add progress bar for deletion process

**Default Behavior:**
- When `--execute` is used WITHOUT `--keep-files`: Files are DELETED from disk
- When `--execute` is used WITH `--keep-files`: Files are PRESERVED on disk

**Acceptance Criteria:**
- Dry-run makes zero API calls, outputs accurate preview
- Execute mode deletes movies AND files from disk by default
- Execute mode with `keep_files=True` removes from Radarr but preserves disk files
- Always adds exclusions to prevent re-import
- Returns dict with "deleted", "failed", "skipped" lists of movie titles
- Failures don't stop the batch; reported at end
- Progress visible during deletion

---

### Task 6: CLI Interface
**Objective:** User-friendly command-line interface

**File:** `radarr_horror_filter.py` (main entry point)

**Subtasks:**
- [ ] 6.1 Create argparse CLI with commands:
  - `scan` - Show all horror movies without deleting
  - `delete` - Delete horror movies (requires --execute)
- [ ] 6.2 Add global flags:
  - `--url` - Radarr URL (overrides env)
  - `--api-key` - API key (overrides env)
  - `--execute` - Actually perform deletions (default: dry-run)
  - `--keep-files` - Keep files on disk, only remove from Radarr (default: delete files)
  - `--genre` - Genre to filter (default: Horror)
  - `--yes` / `-y` - Skip confirmation prompt
  - `--verbose` / `-v` - Detailed output
- [ ] 6.3 Load credentials from `.env` file with python-dotenv
- [ ] 6.4 Show rich-formatted tables for movie listings
- [ ] 6.5 Implement confirmation prompt with exact wording:
  ```
  WARNING: This will permanently delete {N} horror movies ({size} GB) from your server.
  Files will be removed from disk and cannot be recovered.
  Continue? [y/N]
  ```
  If `--keep-files` is used, show instead:
  ```
  This will remove {N} horror movies ({size} GB) from Radarr.
  Files will be preserved on disk.
  Continue? [y/N]
  ```
  Where `{N}` is count and `{size}` is total size formatted to 2 decimal places.
- [ ] 6.6 Display summary after completion showing what was deleted and whether files were removed

**CLI Usage Examples:**
```bash
# Scan and show horror movies (safe, no changes)
python radarr_horror_filter.py scan

# Scan for a different genre
python radarr_horror_filter.py scan --genre Thriller

# Preview what would be deleted
python radarr_horror_filter.py delete

# Actually delete movies AND files from disk (DEFAULT)
python radarr_horror_filter.py delete --execute

# Delete from Radarr but KEEP files on disk
python radarr_horror_filter.py delete --execute --keep-files

# Skip confirmation
python radarr_horror_filter.py delete --execute --yes
```

**Acceptance Criteria:**
- `python radarr_horror_filter.py --help` shows clear usage
- Scan command works without any flags (uses .env)
- Delete without --execute only shows preview
- Delete with --execute deletes movies AND files from disk by default
- `--keep-files` flag preserves files on disk
- Confirmation prompt appears before destructive actions with appropriate warning about file deletion
- Error messages are clear and actionable

---

### Task 7: Documentation
**Objective:** Create README with setup and usage instructions

**File:** `README.md`

**Subtasks:**
- [ ] 7.1 Write overview explaining what the tool does
- [ ] 7.2 Document prerequisites (Python 3.8+, Radarr access)
- [ ] 7.3 Write installation steps
- [ ] 7.4 Document all CLI commands and options including `--genre` and `--keep-files` flags
- [ ] 7.5 Add examples for common use cases
- [ ] 7.6 Document how exclusions work with IMDb lists
- [ ] 7.7 Add troubleshooting section
- [ ] 7.8 **Add clear warning that `--execute` deletes files from disk by default**

**Acceptance Criteria:**
- New user can set up and run tool using only README
- All CLI options documented with examples
- Explains the exclusion mechanism clearly
- Clear warning about file deletion behavior

---

### Task 8: Unit Tests
**Objective:** Ensure correctness of filter and delete logic with mocked API

**File:** `test_filter.py`

**Subtasks:**
- [ ] 8.1 Create pytest fixtures for mock movie data
- [ ] 8.2 Test `HorrorFilter.filter()`:
  - Correctly identifies horror movies
  - Case-insensitive genre matching
  - Handles empty movie list
  - Handles movies with no genres
  - Works with custom genre parameter
- [ ] 8.3 Test `MovieDeleter.delete_movies()` with mocked `RadarrClient`:
  - Dry-run mode makes no API calls
  - Execute mode calls delete API with `deleteFiles=true` by default
  - Execute mode with `keep_files=True` calls delete API with `deleteFiles=false`
  - Returns correct structure with deleted/failed/skipped
  - Handles API errors gracefully
- [ ] 8.4 Test `RadarrClient.test_connection()`:
  - Returns True on successful response
  - Raises `RadarrAPIError` on failure
  - Retry logic triggers on 5xx errors
- [ ] 8.5 Test confirmation prompt logic (skip when `--yes`)

**Test Structure:**
```python
import pytest
from unittest.mock import Mock, patch

class TestHorrorFilter:
    def test_filters_horror_movies(self):
        movies = [
            {"id": 1, "title": "Saw", "genres": ["Horror", "Thriller"]},
            {"id": 2, "title": "Avengers", "genres": ["Action"]},
        ]
        result = HorrorFilter().filter(movies)
        assert len(result) == 1
        assert result[0]["title"] == "Saw"

    def test_case_insensitive_matching(self):
        movies = [{"id": 1, "title": "Test", "genres": ["HORROR"]}]
        result = HorrorFilter().filter(movies)
        assert len(result) == 1

class TestMovieDeleter:
    def test_dry_run_makes_no_api_calls(self):
        client = Mock()
        deleter = MovieDeleter(client)
        result = deleter.delete_movies([...], dry_run=True)
        client.delete_movie.assert_not_called()

    def test_delete_files_by_default(self):
        client = Mock()
        deleter = MovieDeleter(client)
        result = deleter.delete_movies([{"id": 1, "title": "Test"}], dry_run=False)
        client.delete_movie.assert_called_with(1, delete_files=True, add_exclusion=True)

    def test_keep_files_when_flag_set(self):
        client = Mock()
        deleter = MovieDeleter(client)
        result = deleter.delete_movies([{"id": 1, "title": "Test"}], dry_run=False, keep_files=True)
        client.delete_movie.assert_called_with(1, delete_files=False, add_exclusion=True)

class TestRadarrClient:
    def test_retry_on_server_error(self):
        # Mock 500 response then success
        ...
```

**Acceptance Criteria:**
- All tests pass with `pytest test_filter.py`
- Tests use mocked API responses (no real Radarr needed)
- Coverage includes happy path and error cases
- Dry-run verified to make zero API calls
- Default file deletion behavior tested
- `--keep-files` behavior tested

---

## Commit Strategy

| Commit | Tasks | Message |
|--------|-------|---------|
| 1 | Task 1 | `feat: initialize project with dependencies and config` |
| 2 | Task 2 | `feat: add Radarr API client with retry logic` |
| 3 | Task 3, 4 | `feat: add movie scanner and horror filter logic` |
| 4 | Task 5 | `feat: add delete handler with file deletion by default` |
| 5 | Task 6 | `feat: add CLI interface with scan and delete commands` |
| 6 | Task 7 | `docs: add README with setup and usage instructions` |
| 7 | Task 8 | `test: add unit tests for filter and delete logic` |

---

## Success Criteria

### Functional Verification
- [ ] `python radarr_horror_filter.py scan` lists horror movies correctly
- [ ] `python radarr_horror_filter.py delete` shows preview without making changes
- [ ] `python radarr_horror_filter.py delete --execute` deletes movies AND files from disk
- [ ] `python radarr_horror_filter.py delete --execute --keep-files` removes from Radarr but keeps files
- [ ] After deletion, re-running scan shows zero horror movies
- [ ] Deleted movies appear in Radarr exclusion list
- [ ] New horror movies from IMDb lists are blocked by exclusions
- [ ] `pytest test_filter.py` passes all tests

### Quality Checks
- [ ] No Python syntax errors (`python -m py_compile *.py`)
- [ ] No hardcoded credentials in any file
- [ ] All error paths handled gracefully
- [ ] Output is readable and informative

### User Experience
- [ ] Tool is safe by default (dry-run)
- [ ] Clear warning about file deletion when using `--execute`
- [ ] Clear progress indication for long operations
- [ ] Helpful error messages guide user to fix issues

---

## File Structure

```
movie-manager/
├── .env.example           # Template for credentials
├── .env                   # Actual credentials (gitignored)
├── .gitignore             # Ignore .env and cache
├── pyproject.toml         # Python version requirement
├── requirements.txt       # Python dependencies
├── README.md              # Documentation
├── radarr_horror_filter.py  # Main CLI entry point
├── radarr_client.py       # API client class with retry logic
├── scanner.py             # Movie scanning logic
├── filter.py              # Genre filtering logic
├── deleter.py             # Deletion handling
└── test_filter.py         # Unit tests
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Accidental file deletion | Dry-run default, explicit `--execute` required, confirmation prompt with clear file deletion warning, `--keep-files` option available |
| User wants to preserve files | `--keep-files` flag available to remove from Radarr only |
| API key exposure | .env file, .gitignore, no hardcoded values |
| Incomplete deletion batch | Track failures, report at end, re-runnable |
| Network failures | Retry logic with exponential backoff (3 retries: 1s, 2s, 4s) |
| Large library performance | Progress bars, batch processing |
| Transient API errors | Custom `RadarrAPIError` exception with retry handling |

---

## Notes for Implementation

1. **Radarr API v3 only** - This tool targets Radarr v3 API exclusively. Users on older versions should upgrade Radarr.
2. **Exclusions are persistent** - once added, they survive Radarr restarts
3. **IMDb list syncs** will automatically skip excluded titles
4. **Genre is in `genres` array** - e.g., `["Horror", "Thriller"]`
5. **sizeOnDisk** is in bytes - convert for display
6. **Windows paths** - use forward slashes or raw strings in Python
7. **`--genre` flag** - Added for flexibility to filter other genres; defaults to "Horror" to match original requirement
8. **File deletion is DEFAULT** - When `--execute` is used, files are deleted from disk unless `--keep-files` is specified

---

## Architect Questions - Answers

**Q1: Should the tool support Radarr API v2 for backward compatibility, or is v3-only acceptable?**

A: **v3-only is acceptable.** Radarr v3 has been stable since 2020 and is the recommended version. Supporting v2 would add complexity without significant benefit. Users on v2 should upgrade Radarr, which is straightforward.

**Q2: Is there value in a `--genre` flag to allow filtering other genres for future flexibility?**

A: **Yes, added.** The `--genre` flag has been added to Task 4 and Task 6, defaulting to "Horror" but allowing users to filter any genre (e.g., `--genre Thriller`). This provides flexibility with minimal added complexity.

**Q3: Should file deletion be the default behavior?**

A: **Yes.** Per user feedback, when `--execute` is used, files should be deleted from the server by default. The `--keep-files` flag is available for users who want to preserve files on disk while removing movies from Radarr.

# Work Plan: Keep List Feature for Radarr Horror Filter

## Context

### Original Request
Add a "keep list" feature to the Radarr horror filter tool. Users need to mark specific horror movies that should NOT be deleted, even though they match the horror genre filter.

### Research Findings

**Current Architecture:**
```
CLI (radarr_horror_filter.py)
    |
    v
RadarrClient (radarr_client.py) --> Radarr API
    |
    v
MovieScanner (scanner.py) --> Returns movie list
    |
    v
GenreFilter (filter.py) --> Filters by genre
    |
    v
MovieDeleter (deleter.py) --> Deletes movies
```

**Key Observations:**
1. Movie data structure includes: `id`, `title`, `year`, `genres`, `hasFile`, `sizeOnDisk`
2. GenreFilter already has a clean `filter()` interface that returns filtered movie list
3. MovieDeleter has a `skipped` list in results that is currently unused - perfect for keep list integration
4. CLI uses argparse with subcommands (`scan`, `delete`)
5. Test file has 23 tests with good patterns to follow
6. Rich library used for console output and tables

**RadarrClient API (from radarr_client.py):**
- `get_movies()` -> `List[Dict]` - Returns all movies from Radarr
- Each movie dict contains: `id`, `title`, `year`, `genres`, etc.

**Integration Points:**
- After `GenreFilter.filter()` and before `MovieDeleter.delete_movies()`
- New CLI subcommand `keep` with sub-actions (add, remove, list, clear)
- Delete command needs `--ignore-keep-list` flag

---

## Work Objectives

### Core Objective
Enable users to protect specific horror movies from deletion by maintaining a persistent keep list that integrates seamlessly with the existing scan/delete workflow.

### Deliverables
1. `keep_list.py` - KeepListManager class with CRUD operations
2. Updated `radarr_horror_filter.py` - New `keep` subcommand and delete integration
3. `test_keep_list.py` - Comprehensive unit tests for keep list functionality
4. Updated `deleter.py` - Utilize the `skipped` field for kept movies

### Definition of Done
- [ ] User can add movies to keep list by ID or title
- [ ] User can remove movies from keep list
- [ ] User can view all movies in keep list
- [ ] User can clear the entire keep list
- [ ] Delete command automatically skips movies in keep list
- [ ] Delete command shows "Skipped (keep list): N movies" in output
- [ ] Delete command has `--ignore-keep-list` flag to override
- [ ] Scan command shows which movies are in keep list (visual indicator)
- [ ] All existing tests pass
- [ ] New tests cover all keep list functionality

---

## Guardrails

### Must Have
- JSON file storage at `.keep-list.json` in working directory (intentional: allows per-project keep lists)
- Case-insensitive EXACT title matching (see Task 2.3 for details)
- Movie ID takes precedence over title when both provided
- Clear user feedback when adding/removing movies
- Backward compatibility - existing commands work unchanged without keep list
- API validation: always verify movie exists in Radarr before adding to keep list

### Must NOT Have
- Database or external storage dependencies
- Changes to Radarr API calls or RadarrClient
- Breaking changes to existing CLI interface
- Automatic keep list population (user must explicitly add)
- Partial/fuzzy title matching (exact match only to avoid ambiguity)

---

## Task Flow

```
[Task 1: KeepListManager Class]
         |
         v
[Task 2: CLI Keep Subcommand]
         |
         v
[Task 3: Delete Command Integration]
         |
         v
[Task 4: Scan Command Enhancement]
         |
         v
[Task 5: Unit Tests]
         |
         v
[Task 6: Integration Testing]
```

**Dependencies:**
- Task 2 depends on Task 1
- Task 3 depends on Task 1
- Task 4 depends on Task 1
- Task 5 depends on Tasks 1-4
- Task 6 depends on all previous tasks

---

## Detailed TODOs

### Task 1: Create KeepListManager Class

**File:** `keep_list.py`

**Subtasks:**
1.1. Create `KeepListManager` class with constructor accepting optional file path (default: `.keep-list.json`)
1.2. Implement `load()` method - read JSON file, return empty list if file doesn't exist
1.3. Implement `save()` method - write current list to JSON file with pretty formatting
1.4. Implement `add(movie_id: int, title: str)` method - add movie to list, prevent duplicates by ID
     - **Note:** Both `movie_id` and `title` are REQUIRED parameters
     - The caller (CLI) is responsible for providing both values
     - This method does NOT call Radarr API - it just stores the data
1.5. Implement `remove(movie_id: int = None, title: str = None)` method - remove by ID or title
1.6. Implement `list_all()` method - return all kept movies
1.7. Implement `clear()` method - remove all entries
1.8. Implement `is_kept(movie_id: int = None, title: str = None)` method - check if movie is in list
1.9. Implement `filter_kept(movies: List[Dict])` method - return movies NOT in keep list

**Storage Format:**
```json
{
  "version": 1,
  "movies": [
    {"id": 123, "title": "The Exorcist", "added_at": "2024-01-15T10:30:00Z"},
    {"id": 456, "title": "Hereditary", "added_at": "2024-01-16T14:20:00Z"}
  ]
}
```

**Acceptance Criteria:**
- [ ] File created/loaded correctly
- [ ] Duplicate prevention works (by ID)
- [ ] Case-insensitive title lookup in `is_kept()` and `remove()`
- [ ] Graceful handling of missing file
- [ ] JSON format is human-readable

---

### Task 2: Implement CLI Keep Subcommand

**File:** `radarr_horror_filter.py`

**Subtasks:**
2.1. Add `keep` subparser with sub-subcommands: `add`, `remove`, `list`, `clear`

2.2. **Implement `keep add <id>` - add movie by Radarr ID**
     - **Flow:**
       1. Parse `<id>` as integer
       2. Call `RadarrClient.get_movies()` to fetch all movies
       3. Search for movie with matching `id` field
       4. If NOT found: print error `"Error: Movie with ID {id} not found in Radarr"` and exit(1)
       5. If found: extract `title` from the movie dict
       6. Call `KeepListManager.add(id, title)`
       7. Print success: `"Added to keep list: {title} (ID: {id})"`

2.3. **Implement `keep add --title "Movie Name"` - add movie by title**
     - **Flow:**
       1. Call `RadarrClient.get_movies()` to fetch all movies
       2. Search for movies with EXACT title match (case-insensitive)
          - Compare `movie['title'].lower() == user_input.lower()`
       3. **If ZERO matches:** print error `"Error: No movie found with title '{title}'"` and exit(1)
       4. **If MULTIPLE matches:** This should not happen with exact matching, but if it does:
          - Print error `"Error: Multiple movies found with title '{title}'. Use movie ID instead."`
          - List the matching movies with their IDs for user reference
          - exit(1)
       5. **If EXACTLY ONE match:** extract `id` and `title` from the movie dict
       6. Call `KeepListManager.add(id, title)`
       7. Print success: `"Added to keep list: {title} (ID: {id})"`
     - **Important:** The stored title should be the one from Radarr, not the user input

2.4. Implement `keep remove <id>` - remove movie by ID
     - Call `KeepListManager.remove(movie_id=id)`
     - Print success or "not found" message

2.5. Implement `keep remove --title "Movie Name"` - remove movie by title
     - Call `KeepListManager.remove(title=title)` (case-insensitive match done inside KeepListManager)
     - Print success or "not found" message

2.6. Implement `keep list` - display all kept movies in table format
     - Use Rich table matching existing scan output style
     - Show columns: ID, Title, Added Date

2.7. Implement `keep clear` - clear all entries with confirmation
     - Prompt: `"Are you sure you want to clear the keep list? (y/N): "`
     - Only clear if user types 'y' or 'Y'

2.8. Add `--yes/-y` flag to `keep clear` to skip confirmation

**CLI Interface:**
```
python radarr_horror_filter.py keep add 123
python radarr_horror_filter.py keep add --title "The Exorcist"
python radarr_horror_filter.py keep remove 123
python radarr_horror_filter.py keep remove --title "The Exorcist"
python radarr_horror_filter.py keep list
python radarr_horror_filter.py keep clear [-y]
```

**Error Messages:**
| Scenario | Message |
|----------|---------|
| ID not found | `"Error: Movie with ID {id} not found in Radarr"` |
| Title not found | `"Error: No movie found with title '{title}'"` |
| Multiple title matches | `"Error: Multiple movies found with title '{title}'. Use movie ID instead."` |
| Already in keep list | `"'{title}' is already in the keep list"` |
| Not in keep list (remove) | `"'{title}' was not in the keep list"` |

**Acceptance Criteria:**
- [ ] All subcommands work correctly
- [ ] `keep add <id>` validates movie exists in Radarr before adding
- [ ] `keep add --title` uses exact case-insensitive matching
- [ ] `keep add --title` handles 0 and multiple matches correctly
- [ ] Helpful error messages for invalid input
- [ ] Table display matches existing scan output style
- [ ] Clear command requires confirmation unless -y flag

---

### Task 3: Integrate Keep List with Delete Command

**File:** `radarr_horror_filter.py`, `deleter.py`

**Subtasks:**
3.1. Add `--ignore-keep-list` flag to delete parser
3.2. In `cmd_delete()`, load keep list before deletion
3.3. Filter out kept movies from deletion list (unless --ignore-keep-list)
3.4. Update deletion output to show "Skipped (keep list): N movies"
3.5. In `MovieDeleter.delete_movies()`, accept optional `kept_movies` parameter
3.6. Populate `results['skipped']` with kept movie titles

**Updated Flow:**
```python
# In cmd_delete():
keep_list = KeepListManager()
filtered_movies = genre_filter.filter(all_movies)

if not args.ignore_keep_list:
    kept_movies = [m for m in filtered_movies if keep_list.is_kept(m['id'])]
    filtered_movies = keep_list.filter_kept(filtered_movies)
    # Show kept movies count and names
    if kept_movies:
        console.print(f"[yellow]Skipped (keep list): {len(kept_movies)} movies[/yellow]")
        for m in kept_movies:
            console.print(f"  - {m['title']}")
```

**Acceptance Criteria:**
- [ ] Kept movies are skipped during deletion
- [ ] Output clearly shows how many were skipped and why
- [ ] --ignore-keep-list flag bypasses keep list
- [ ] Dry run also shows kept movies would be skipped

---

### Task 4: Enhance Scan Command with Keep List Indicator

**File:** `radarr_horror_filter.py`

**Subtasks:**
4.1. Modify `display_movies_table()` to accept optional keep_list parameter
4.2. Add "Kept" column or marker to table for movies in keep list
4.3. Show summary line: "X movies in keep list" after scan results

**Table Update:**
```
| Title           | Year | Size    | Genres          | Kept |
|-----------------|------|---------|-----------------|------|
| The Exorcist    | 1973 | 4.2 GB  | Horror          | Yes  |
| Saw             | 2004 | 2.1 GB  | Horror, Thriller|      |
```

**Acceptance Criteria:**
- [ ] Keep list status visible in scan output
- [ ] Summary shows total kept movies count
- [ ] Works correctly when keep list is empty

---

### Task 5: Create Unit Tests

**File:** `test_keep_list.py`

**Subtasks:**
5.1. Test `KeepListManager` initialization (with/without existing file)
5.2. Test `add()` - normal add, duplicate prevention
5.3. Test `remove()` - by ID, by title, non-existent
5.4. Test `list_all()` - empty list, populated list
5.5. Test `clear()` - removes all entries
5.6. Test `is_kept()` - by ID, by title, case-insensitive
5.7. Test `filter_kept()` - correctly filters movie list
5.8. Test file persistence (save/load cycle)
5.9. Test graceful handling of corrupted JSON file

**Test Structure:**
```python
class TestKeepListManager:
    def test_add_movie_by_id(self): ...
    def test_add_movie_prevents_duplicates(self): ...
    def test_remove_movie_by_id(self): ...
    def test_remove_movie_by_title_case_insensitive(self): ...
    def test_is_kept_returns_true_for_kept_movie(self): ...
    def test_is_kept_returns_false_for_unknown_movie(self): ...
    def test_filter_kept_removes_kept_movies(self): ...
    def test_clear_removes_all_entries(self): ...
    def test_load_creates_empty_list_if_file_missing(self): ...
    def test_save_load_round_trip(self): ...
```

**Acceptance Criteria:**
- [ ] All tests pass
- [ ] Edge cases covered (empty list, missing file, duplicates)
- [ ] Test isolation (each test uses temp file)

---

### Task 6: Integration Testing

**Manual verification steps:**

6.1. Fresh start test:
```bash
# Remove any existing keep list
rm .keep-list.json 2>/dev/null

# Scan should work normally
python radarr_horror_filter.py scan --genre Horror

# Keep list should be empty
python radarr_horror_filter.py keep list
```

6.2. Add/remove workflow:
```bash
# Add a movie by ID (CLI fetches title from Radarr)
python radarr_horror_filter.py keep add 123

# Verify it's in the list
python radarr_horror_filter.py keep list

# Add a movie by title (CLI searches Radarr)
python radarr_horror_filter.py keep add --title "The Exorcist"

# Remove it
python radarr_horror_filter.py keep remove 123

# Verify it's gone
python radarr_horror_filter.py keep list
```

6.3. Delete integration:
```bash
# Add a horror movie to keep list
python radarr_horror_filter.py keep add 123

# Dry-run delete should show it as skipped
python radarr_horror_filter.py delete --genre Horror

# With ignore flag, it should be included
python radarr_horror_filter.py delete --genre Horror --ignore-keep-list
```

6.4. Error handling:
```bash
# Try to add non-existent movie ID
python radarr_horror_filter.py keep add 999999
# Expected: "Error: Movie with ID 999999 not found in Radarr"

# Try to add non-existent title
python radarr_horror_filter.py keep add --title "Not A Real Movie"
# Expected: "Error: No movie found with title 'Not A Real Movie'"
```

**Acceptance Criteria:**
- [ ] All manual test scenarios pass
- [ ] No regressions in existing functionality
- [ ] Error handling works as expected

---

## Commit Strategy

### Commit 1: Add KeepListManager class
- Files: `keep_list.py`
- Message: "feat: add KeepListManager class for keep list storage"

### Commit 2: Add keep CLI subcommand
- Files: `radarr_horror_filter.py`
- Message: "feat: add keep subcommand for managing keep list"

### Commit 3: Integrate with delete command
- Files: `radarr_horror_filter.py`, `deleter.py`
- Message: "feat: integrate keep list with delete command"

### Commit 4: Enhance scan command
- Files: `radarr_horror_filter.py`
- Message: "feat: show keep list status in scan output"

### Commit 5: Add unit tests
- Files: `test_keep_list.py`
- Message: "test: add comprehensive tests for keep list feature"

---

## Success Criteria

### Functional Requirements
- [ ] Keep list persists between sessions
- [ ] Movies can be added/removed by ID or title
- [ ] Adding by ID fetches and stores title from Radarr
- [ ] Adding by title uses exact case-insensitive matching
- [ ] Delete command respects keep list by default
- [ ] Delete command can ignore keep list with flag
- [ ] Scan command shows keep list status

### Non-Functional Requirements
- [ ] No breaking changes to existing commands
- [ ] All existing tests pass
- [ ] New tests provide good coverage
- [ ] Code follows existing project patterns
- [ ] Error messages are user-friendly

### Verification Commands
```bash
# Run all tests
pytest test_filter.py test_keep_list.py -v

# Check no syntax errors
python -m py_compile keep_list.py radarr_horror_filter.py

# Verify help text
python radarr_horror_filter.py keep --help
python radarr_horror_filter.py delete --help
```

---

## Estimated Complexity

**Overall: MEDIUM**

- Task 1 (KeepListManager): Low complexity - straightforward CRUD
- Task 2 (CLI subcommand): Medium complexity - argparse nesting + Radarr API integration
- Task 3 (Delete integration): Low complexity - simple filtering
- Task 4 (Scan enhancement): Low complexity - table modification
- Task 5 (Unit tests): Medium complexity - comprehensive coverage
- Task 6 (Integration): Low complexity - manual verification

**Total estimated tasks:** 6 major tasks, ~30 subtasks
**Files to create:** 2 (`keep_list.py`, `test_keep_list.py`)
**Files to modify:** 2 (`radarr_horror_filter.py`, `deleter.py`)

---

## Design Notes

### Keep List File Location
The `.keep-list.json` file is stored in the current working directory. This is **intentional** to allow per-project keep lists. Users running the tool from different directories can maintain separate keep lists if desired.

### Title Matching Strategy
**Exact match only** (case-insensitive) is used for `keep add --title` to avoid ambiguity:
- "The Exorcist" matches "THE EXORCIST" and "the exorcist"
- "Exorcist" does NOT match "The Exorcist" (partial match rejected)

This prevents accidental additions when user input is ambiguous. If users need to add movies with similar titles, they should use the movie ID instead.

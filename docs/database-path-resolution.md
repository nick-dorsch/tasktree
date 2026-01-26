# Database Path Resolution

TaskTree uses a flexible database path resolution strategy to support both repository-local and user-level database storage.

## Path Resolution Priority

The database path is resolved in the following order:

### 1. Environment Variable Override (Highest Priority)

Set `TASKTREE_DB_PATH` to specify an absolute path to the database file:

```bash
export TASKTREE_DB_PATH=/path/to/custom/tasktree.db
```

**Constraints:**
- Must be an absolute path (relative paths will raise `ValueError`)
- Parent directory will be created automatically if it doesn't exist
- Takes precedence over all other resolution methods

**Use cases:**
- CI/CD environments with specific file locations
- Testing with temporary databases
- Multi-repo setups with shared database

### 2. Repository-Local Database (Default)

When running inside a git repository, TaskTree creates a `.tasktree/tasktree.db` file in the repository root:

```
my-project/
├── .git/
├── .tasktree/
│   └── tasktree.db  # Database is here
├── src/
│   └── module/
│       └── file.py  # TaskTree works from any subdirectory
└── README.md
```

**How it works:**
- Walks up the directory tree from `cwd` looking for `.git/` directory
- Creates `.tasktree/` directory in the repo root
- Each repository gets its own isolated task database

**Benefits:**
- Tasks are scoped to the repository
- Works from any subdirectory in the repo
- Database can be committed (if desired) or ignored via `.gitignore`
- Natural separation between different projects

### 3. User Home Directory (Fallback)

When not in a git repository, TaskTree uses `~/.tasktree/tasktree.db`:

```
~/.tasktree/
└── tasktree.db  # Global task database
```

**Use cases:**
- Personal task tracking outside of repositories
- System-wide task management
- Working in non-git directories

## Repository Root Discovery

The repository root is identified by walking up from the current working directory until a `.git` directory is found.

**Example:**

```
/home/user/repos/myproject/src/module/
→ Check: /home/user/repos/myproject/src/module/.git (not found)
→ Check: /home/user/repos/myproject/src/.git (not found)
→ Check: /home/user/repos/myproject/.git (found!)
→ Repo root: /home/user/repos/myproject
→ Database: /home/user/repos/myproject/.tasktree/tasktree.db
```

**Important notes:**
- Only `.git` **directories** are recognized (`.git` files are ignored)
- Stops at the first `.git` found (nearest parent)
- Stops at filesystem root if no `.git` is found
- Works with nested repositories (uses the innermost repo)

## Directory Creation

TaskTree automatically creates the `.tasktree` directory if it doesn't exist:

- Directory is created with default permissions (`0755`)
- Parent directories are created if needed
- Raises `PermissionError` if directory cannot be created

## Failure Modes and Error Handling

### 1. Invalid TASKTREE_DB_PATH

```python
# ❌ Relative path - raises ValueError
TASKTREE_DB_PATH=relative/path.db

# ✅ Absolute path - works correctly
TASKTREE_DB_PATH=/absolute/path/to/db.db
```

**Error:**
```
ValueError: TASKTREE_DB_PATH must be an absolute path, got: relative/path.db
```

### 2. Permission Denied

If TaskTree cannot create the `.tasktree` directory:

```
PermissionError: Cannot create directory /path/to/.tasktree: Permission denied
```

**Solutions:**
- Ensure write permissions in the repository root
- Use `TASKTREE_DB_PATH` to specify an alternative location
- Check filesystem quotas and disk space

### 3. No Repository Found

When not in a git repository and no environment variable is set:
- Falls back to `~/.tasktree/tasktree.db` silently
- This is not an error condition

### 4. Multiple .git Directories (Nested Repos)

When working in a git submodule or nested repository:
- Uses the **nearest** `.git` directory (innermost repo)
- Each nested repo gets its own `.tasktree/` directory
- Tasks are isolated per repository

## Migration from Previous Versions

If you were previously using TaskTree with the `data/tasktree.db` path:

### Option 1: Keep Using the Old Location

Set the environment variable to maintain the old behavior:

```bash
export TASKTREE_DB_PATH=/home/nick/repos/tasktree/data/tasktree.db
```

### Option 2: Move to Repository-Local Database

1. Copy your existing database to the new location:
   ```bash
   mkdir -p .tasktree
   cp data/tasktree.db .tasktree/tasktree.db
   ```

2. Update `.gitignore` if you want to exclude the database:
   ```
   .tasktree/
   ```

### Option 3: Fresh Start

Simply start using TaskTree - it will automatically create `.tasktree/tasktree.db` in your repository root.

## Examples

### Example 1: Repository-Local Usage

```bash
cd ~/projects/my-app
tasktree add-task "Setup CI/CD"
# Database: ~/projects/my-app/.tasktree/tasktree.db

cd ~/projects/my-app/src/backend
tasktree list-tasks
# Still uses: ~/projects/my-app/.tasktree/tasktree.db
```

### Example 2: Custom Location

```bash
export TASKTREE_DB_PATH=/tmp/tasktree-test.db
tasktree add-task "Test task"
# Database: /tmp/tasktree-test.db (regardless of cwd)
```

### Example 3: Multiple Repositories

```bash
cd ~/projects/frontend
tasktree add-task "Update dependencies"
# Database: ~/projects/frontend/.tasktree/tasktree.db

cd ~/projects/backend
tasktree add-task "Add API endpoint"
# Database: ~/projects/backend/.tasktree/tasktree.db

# Each repo has isolated tasks!
```

### Example 4: Global Task Tracking

```bash
cd ~/documents  # Not a git repo
tasktree add-task "Review quarterly report"
# Database: ~/.tasktree/tasktree.db
```

## Best Practices

1. **Add `.tasktree/` to `.gitignore`** if you don't want to commit your task database
2. **Use environment variables in CI/CD** to specify temporary database locations
3. **Don't mix repository-local and global databases** for the same project
4. **Document custom TASKTREE_DB_PATH usage** in your project README if you use it

## Technical Implementation

The path resolution is implemented in `src/tasktree_mcp/paths.py`:

- `find_repo_root(start_path)`: Discovers the repository root
- `get_db_path()`: Resolves the database path using the priority order
- Automatically creates directories as needed
- Validates environment variable settings

## Testing

The path resolution behavior is thoroughly tested in `tests/test_paths.py`, covering:

- Repository root discovery from various starting points
- Environment variable precedence
- Directory creation
- Permission error handling
- Edge cases (nested repos, missing .git, etc.)

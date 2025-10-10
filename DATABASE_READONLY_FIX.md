# Database Readonly Issue - Permanent Fix

## Problem Description

The application was experiencing "sqlite3.OperationalError: attempt to write a readonly database" errors when trying to perform write operations (user registration, logging, etc.). This was preventing normal application functionality.

## Root Cause Analysis

The issue was caused by several factors:

1. **Database Path Mismatch**: The application configuration was looking for different database file names/paths than what actually existed
2. **Permission Issues**: Database files and directories didn't have proper write permissions
3. **User Permission Conflicts**: Container user permissions didn't match host file permissions

## Permanent Fix Applied

### 1. Database Configuration Updates

**File: `app/config/settings.py`**
- Updated default database URL to match docker-compose configuration: `sqlite+aiosqlite:///./data/promptenchanter2.db`

**File: `app/database/database.py`**
- Added automatic directory creation with proper permissions
- Added permission setting for database files (755 for directories, 664 for files)
- Enhanced error handling for permission issues

### 2. Docker Configuration Updates

**File: `Dockerfile`**
- Set specific UID (1000) for appuser to match host user
- Added proper directory permissions during build

**File: `docker-entrypoint.sh`**
- Enhanced permission setting for data directory and database files
- Added checks for both database file variants

**File: `docker-compose.yml`**
- Ensured DATABASE_URL environment variable matches expected path
- Volume mounting configured correctly

### 3. Environment Configuration

**File: `.env`**
- Created proper environment configuration file
- Set DATABASE_URL to correct path

### 4. Database Files

- Copied existing database to match expected filename (`promptenchanter2.db`)
- Set proper permissions (664) on all database files

### 5. Utility Scripts

**File: `scripts/fix_db_permissions_simple.py`**
- Simple script to fix database permissions without dependencies
- Can be run independently to resolve permission issues

**File: `scripts/init_database_safe.py`**
- Safe database initialization with fallback mechanisms
- Handles various error scenarios gracefully

## Verification

The fix has been verified by:

1. ✅ Database files have correct permissions (664)
2. ✅ Data directory has correct permissions (755)
3. ✅ Write operations work correctly (tested with INSERT/SELECT/DELETE)
4. ✅ Directory is writable by application user

## Prevention Measures

To prevent this issue from recurring:

### 1. Always Use Consistent Database Paths
- Ensure `DATABASE_URL` in environment matches actual file locations
- Use absolute paths or consistent relative paths

### 2. Proper Permission Management
- Database files should have 664 permissions (rw-rw-r--)
- Database directories should have 755 permissions (rwxr-xr-x)
- Container user should have matching UID with host user

### 3. Environment Configuration
- Always use `.env` file for environment-specific settings
- Ensure docker-compose environment variables match application expectations

### 4. Regular Monitoring
- Monitor application logs for permission-related errors
- Include database connectivity checks in health checks

## Troubleshooting

If the readonly database error occurs again:

### Quick Fix
```bash
# Run the permission fix script
python3 scripts/fix_db_permissions_simple.py
```

### Manual Fix
```bash
# Set directory permissions
chmod 755 /path/to/data/directory

# Set database file permissions
chmod 664 /path/to/database/file.db

# Ensure proper ownership (if needed)
chown appuser:appuser /path/to/data/directory
chown appuser:appuser /path/to/database/file.db
```

### Verification Commands
```bash
# Check permissions
ls -la /workspace/data/

# Test database connectivity
sqlite3 /workspace/data/promptenchanter2.db ".tables"

# Test write operations
sqlite3 /workspace/data/promptenchanter2.db "CREATE TABLE test_write (id INTEGER);"
```

## Files Modified

1. `app/config/settings.py` - Updated default database URL
2. `app/database/database.py` - Added permission handling
3. `Dockerfile` - Enhanced user and permission setup
4. `docker-entrypoint.sh` - Added database permission fixes
5. `.env` - Created environment configuration
6. `scripts/fix_db_permissions_simple.py` - Permission fix utility
7. `scripts/init_database_safe.py` - Safe database initialization

## Summary

The readonly database issue has been permanently resolved through:
- Proper database path configuration
- Correct file and directory permissions
- Enhanced Docker container setup
- Comprehensive error handling and fallback mechanisms
- Utility scripts for maintenance and troubleshooting

The application should now handle database operations correctly without permission-related errors.
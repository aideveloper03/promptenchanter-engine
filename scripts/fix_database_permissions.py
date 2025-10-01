#!/usr/bin/env python3
"""
Script to fix database permissions and ensure proper setup
"""
import os
import sys
import asyncio
from pathlib import Path

# Add the workspace directory to the Python path
sys.path.insert(0, '/workspace')

from app.config.settings import get_settings
from app.database.database import init_database

def fix_permissions():
    """Fix database file and directory permissions"""
    settings = get_settings()
    database_url = settings.database_url
    
    if "sqlite" not in database_url:
        print("Not using SQLite, no permission fixes needed")
        return True
    
    # Extract database path
    db_path = database_url.replace('sqlite+aiosqlite:///', '')
    db_file = Path(db_path)
    db_dir = db_file.parent
    
    print(f"Database path: {db_path}")
    print(f"Database directory: {db_dir}")
    
    try:
        # Ensure directory exists
        db_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Directory created/verified: {db_dir}")
        
        # Set directory permissions
        os.chmod(str(db_dir), 0o755)
        print(f"✅ Directory permissions set: 755")
        
        # If database file exists, set its permissions
        if db_file.exists():
            os.chmod(str(db_file), 0o664)
            print(f"✅ Database file permissions set: 664")
        else:
            print(f"ℹ️ Database file doesn't exist yet: {db_file}")
        
        # Check if we can write to the directory
        test_file = db_dir / "test_write.tmp"
        try:
            test_file.touch()
            test_file.unlink()
            print("✅ Directory is writable")
        except Exception as e:
            print(f"❌ Directory is not writable: {e}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error fixing permissions: {e}")
        return False

async def test_database_connection():
    """Test database connection and initialization"""
    try:
        await init_database()
        print("✅ Database connection and initialization successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def main():
    """Main function"""
    print("🔧 Fixing database permissions...")
    
    if not fix_permissions():
        print("❌ Failed to fix permissions")
        sys.exit(1)
    
    print("\n🗄️ Testing database connection...")
    if not await test_database_connection():
        print("❌ Database connection test failed")
        sys.exit(1)
    
    print("\n✅ All database checks passed!")

if __name__ == "__main__":
    asyncio.run(main())
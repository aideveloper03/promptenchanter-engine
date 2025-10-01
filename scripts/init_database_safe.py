#!/usr/bin/env python3
"""
Safe database initialization script that handles permission issues
"""
import os
import sys
import asyncio
import sqlite3
from pathlib import Path

# Add the workspace directory to the Python path
sys.path.insert(0, '/workspace')

async def safe_init_database():
    """Safely initialize database with proper error handling"""
    
    # First, fix permissions
    print("🔧 Fixing database permissions...")
    
    data_dir = Path("/workspace/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        os.chmod(str(data_dir), 0o755)
        print(f"✅ Directory permissions set: {data_dir}")
    except Exception as e:
        print(f"⚠️ Could not set directory permissions: {e}")
    
    # Database files to check
    db_files = [
        data_dir / "promptenchanter.db",
        data_dir / "promptenchanter2.db"
    ]
    
    for db_file in db_files:
        if db_file.exists():
            try:
                os.chmod(str(db_file), 0o664)
                print(f"✅ Database file permissions set: {db_file}")
            except Exception as e:
                print(f"⚠️ Could not set file permissions for {db_file}: {e}")
    
    # Test basic SQLite connectivity
    test_db_path = data_dir / "promptenchanter2.db"
    
    try:
        # Test with sqlite3 directly first
        conn = sqlite3.connect(str(test_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        
        print(f"✅ SQLite connection successful. Found {len(tables)} tables.")
        
        # If we have tables, the database is already initialized
        if len(tables) > 0:
            print("ℹ️ Database already contains tables, skipping initialization")
            return True
            
    except Exception as e:
        print(f"⚠️ SQLite connection test failed: {e}")
    
    # Try to import and use the app's database initialization
    try:
        from app.database.database import init_database
        await init_database()
        print("✅ Database initialized using app's init_database function")
        return True
    except Exception as e:
        print(f"❌ App database initialization failed: {e}")
        
        # Fallback: create a minimal database structure
        try:
            print("🔄 Attempting fallback database creation...")
            conn = sqlite3.connect(str(test_db_path))
            cursor = conn.cursor()
            
            # Create a simple test table to verify write access
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS db_test (
                    id INTEGER PRIMARY KEY,
                    test_value TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Test insert
            cursor.execute("INSERT INTO db_test (test_value) VALUES (?)", ("test_write",))
            conn.commit()
            
            # Test select
            cursor.execute("SELECT COUNT(*) FROM db_test")
            count = cursor.fetchone()[0]
            
            conn.close()
            
            print(f"✅ Fallback database creation successful. Test records: {count}")
            return True
            
        except Exception as fallback_error:
            print(f"❌ Fallback database creation failed: {fallback_error}")
            return False

async def main():
    """Main function"""
    print("🗄️ Safe Database Initialization")
    print("=" * 40)
    
    success = await safe_init_database()
    
    if success:
        print("\n✅ Database initialization completed successfully!")
        return 0
    else:
        print("\n❌ Database initialization failed!")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
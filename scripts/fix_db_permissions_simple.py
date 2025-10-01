#!/usr/bin/env python3
"""
Simple script to fix database permissions without dependencies
"""
import os
import sys
from pathlib import Path

def fix_permissions():
    """Fix database file and directory permissions"""
    
    # Database paths to check
    db_paths = [
        "/workspace/data/promptenchanter.db",
        "/workspace/data/promptenchanter2.db",
        "./data/promptenchanter.db",
        "./data/promptenchanter2.db"
    ]
    
    data_dirs = [
        "/workspace/data",
        "./data"
    ]
    
    print("🔧 Fixing database permissions...")
    
    # Fix directory permissions
    for data_dir in data_dirs:
        dir_path = Path(data_dir)
        if dir_path.exists():
            try:
                os.chmod(str(dir_path), 0o755)
                print(f"✅ Directory permissions set: {dir_path} (755)")
            except Exception as e:
                print(f"⚠️ Could not set directory permissions for {dir_path}: {e}")
        else:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                os.chmod(str(dir_path), 0o755)
                print(f"✅ Directory created and permissions set: {dir_path} (755)")
            except Exception as e:
                print(f"❌ Could not create directory {dir_path}: {e}")
    
    # Fix database file permissions
    for db_path in db_paths:
        db_file = Path(db_path)
        if db_file.exists():
            try:
                os.chmod(str(db_file), 0o664)
                print(f"✅ Database file permissions set: {db_file} (664)")
            except Exception as e:
                print(f"⚠️ Could not set file permissions for {db_file}: {e}")
        else:
            print(f"ℹ️ Database file doesn't exist: {db_file}")
    
    # Test write permissions
    test_dirs = ["/workspace/data", "./data"]
    for test_dir in test_dirs:
        dir_path = Path(test_dir)
        if dir_path.exists():
            test_file = dir_path / "test_write.tmp"
            try:
                test_file.touch()
                test_file.unlink()
                print(f"✅ Directory is writable: {dir_path}")
            except Exception as e:
                print(f"❌ Directory is not writable: {dir_path} - {e}")
                return False
    
    return True

def main():
    """Main function"""
    print("🗄️ Database Permissions Fix Tool")
    print("=" * 40)
    
    if fix_permissions():
        print("\n✅ Database permissions fixed successfully!")
        return 0
    else:
        print("\n❌ Failed to fix database permissions!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
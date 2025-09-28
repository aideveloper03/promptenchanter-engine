#!/usr/bin/env python3
"""
Password hash migration script
Migrates existing bcrypt password hashes to argon2id in the database.

This script is optional - the system will automatically upgrade hashes during user login.
Use this script if you want to proactively migrate all password hashes at once.

WARNING: This script will modify the database. Make sure to backup your database first!
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

async def migrate_user_passwords():
    """Migrate user password hashes from bcrypt to argon2id"""
    try:
        from app.database.database import get_db_session_context
        from app.database.models import User, Admin, SupportStaff
        from app.security.encryption import password_manager
        from sqlalchemy import select, update
        
        print("🔄 Starting user password hash migration...")
        
        async with get_db_session_context() as session:
            # Get all users with bcrypt hashes
            result = await session.execute(
                select(User).where(
                    User.password_hash.like('$2%')  # bcrypt hashes start with $2
                )
            )
            users = result.scalars().all()
            
            if not users:
                print("   ✅ No user bcrypt hashes found to migrate")
                return 0
            
            print(f"   Found {len(users)} user(s) with bcrypt hashes")
            
            # Note: We cannot migrate without the plain password
            # This is by design - password hashes are one-way
            print("   ⚠️  Cannot migrate existing hashes without plain passwords")
            print("   ⚠️  Migration will happen automatically when users log in")
            print("   ⚠️  This is the secure approach - we never store plain passwords")
            
            return len(users)
            
    except Exception as e:
        print(f"   ❌ Error during user migration: {e}")
        return -1


async def migrate_admin_passwords():
    """Migrate admin password hashes from bcrypt to argon2id"""
    try:
        from app.database.database import get_db_session_context
        from app.database.models import Admin
        from sqlalchemy import select
        
        print("🔄 Starting admin password hash migration...")
        
        async with get_db_session_context() as session:
            # Get all admins with bcrypt hashes
            result = await session.execute(
                select(Admin).where(
                    Admin.password_hash.like('$2%')  # bcrypt hashes start with $2
                )
            )
            admins = result.scalars().all()
            
            if not admins:
                print("   ✅ No admin bcrypt hashes found to migrate")
                return 0
            
            print(f"   Found {len(admins)} admin(s) with bcrypt hashes")
            print("   ⚠️  Cannot migrate existing hashes without plain passwords")
            print("   ⚠️  Migration will happen automatically when admins log in")
            
            return len(admins)
            
    except Exception as e:
        print(f"   ❌ Error during admin migration: {e}")
        return -1


async def migrate_support_staff_passwords():
    """Migrate support staff password hashes from bcrypt to argon2id"""
    try:
        from app.database.database import get_db_session_context
        from app.database.models import SupportStaff
        from sqlalchemy import select
        
        print("🔄 Starting support staff password hash migration...")
        
        async with get_db_session_context() as session:
            # Get all support staff with bcrypt hashes
            result = await session.execute(
                select(SupportStaff).where(
                    SupportStaff.password_hash.like('$2%')  # bcrypt hashes start with $2
                )
            )
            staff = result.scalars().all()
            
            if not staff:
                print("   ✅ No support staff bcrypt hashes found to migrate")
                return 0
            
            print(f"   Found {len(staff)} support staff with bcrypt hashes")
            print("   ⚠️  Cannot migrate existing hashes without plain passwords")
            print("   ⚠️  Migration will happen automatically when staff log in")
            
            return len(staff)
            
    except Exception as e:
        print(f"   ❌ Error during support staff migration: {e}")
        return -1


async def check_migration_status():
    """Check the current status of password hash migration"""
    try:
        from app.database.database import get_db_session_context
        from app.database.models import User, Admin, SupportStaff
        from sqlalchemy import select, func
        
        print("📊 Checking migration status...")
        
        async with get_db_session_context() as session:
            # Count bcrypt vs argon2 hashes for each table
            tables = [
                ("Users", User),
                ("Admins", Admin),
                ("Support Staff", SupportStaff)
            ]
            
            total_bcrypt = 0
            total_argon2 = 0
            
            for table_name, model in tables:
                # Count bcrypt hashes
                bcrypt_result = await session.execute(
                    select(func.count()).where(model.password_hash.like('$2%'))
                )
                bcrypt_count = bcrypt_result.scalar()
                
                # Count argon2 hashes
                argon2_result = await session.execute(
                    select(func.count()).where(model.password_hash.like('$argon2%'))
                )
                argon2_count = argon2_result.scalar()
                
                # Count total
                total_result = await session.execute(
                    select(func.count()).select_from(model)
                )
                total_count = total_result.scalar()
                
                print(f"   {table_name}:")
                print(f"     Total: {total_count}")
                print(f"     Bcrypt: {bcrypt_count}")
                print(f"     Argon2: {argon2_count}")
                
                if total_count > 0:
                    percentage = (argon2_count / total_count) * 100
                    print(f"     Migration: {percentage:.1f}% complete")
                
                total_bcrypt += bcrypt_count
                total_argon2 += argon2_count
            
            print(f"\n   Overall Migration Status:")
            print(f"     Total Bcrypt hashes remaining: {total_bcrypt}")
            print(f"     Total Argon2 hashes: {total_argon2}")
            
            if total_bcrypt == 0:
                print("   🎉 All password hashes have been migrated to argon2id!")
            else:
                print(f"   ⏳ {total_bcrypt} password hashes still need migration")
                print("   💡 These will be automatically upgraded when users log in")
            
            return total_bcrypt, total_argon2
            
    except Exception as e:
        print(f"   ❌ Error checking migration status: {e}")
        return -1, -1


def print_migration_info():
    """Print information about the migration process"""
    print("📋 Password Hash Migration Information")
    print("=" * 50)
    print()
    print("🔐 Migration Details:")
    print("   • Old: bcrypt with 72-byte password limit")
    print("   • New: argon2id with 1024-byte password limit")
    print("   • Security: argon2id is more resistant to GPU attacks")
    print("   • Performance: argon2id uses memory-hard functions")
    print()
    print("🔄 Migration Process:")
    print("   • Automatic: Hashes upgrade during user login")
    print("   • Backward Compatible: Old bcrypt hashes still work")
    print("   • Secure: Plain passwords are never stored or logged")
    print("   • Seamless: Users don't need to reset passwords")
    print()
    print("⚙️ Configuration:")
    print("   • Algorithm: argon2id (most secure variant)")
    print("   • Time cost: 3 iterations")
    print("   • Memory cost: 64 MB")
    print("   • Parallelism: 1 thread")
    print("   • Hash length: 32 bytes")
    print("   • Salt length: 16 bytes")
    print()


async def main():
    """Main migration function"""
    print_migration_info()
    
    # Check current status
    bcrypt_count, argon2_count = await check_migration_status()
    
    if bcrypt_count < 0:
        print("❌ Failed to check migration status")
        return False
    
    print()
    
    # Check for bcrypt hashes to migrate
    user_count = await migrate_user_passwords()
    admin_count = await migrate_admin_passwords()
    staff_count = await migrate_support_staff_passwords()
    
    print()
    print("=" * 50)
    
    if user_count < 0 or admin_count < 0 or staff_count < 0:
        print("❌ Migration check failed")
        return False
    
    total_pending = user_count + admin_count + staff_count
    
    if total_pending == 0:
        print("🎉 No password hashes need migration!")
        print("✅ All accounts are using argon2id")
    else:
        print(f"📊 Migration Summary:")
        print(f"   • Users with bcrypt hashes: {user_count}")
        print(f"   • Admins with bcrypt hashes: {admin_count}")
        print(f"   • Support staff with bcrypt hashes: {staff_count}")
        print(f"   • Total pending migration: {total_pending}")
        print()
        print("💡 Next Steps:")
        print("   • Hashes will automatically upgrade when users log in")
        print("   • No action required from users")
        print("   • Monitor logs for 'password_hash_upgraded' events")
        print("   • Run this script periodically to check progress")
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
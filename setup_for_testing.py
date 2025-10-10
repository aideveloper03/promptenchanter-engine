#!/usr/bin/env python3
"""
Setup script for PromptEnchanter testing
Prepares the system by creating necessary admin accounts and initial data
"""

import asyncio
import sys
import subprocess
from pathlib import Path

class TestSetup:
    def __init__(self):
        self.log_messages = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log setup messages"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        self.log_messages.append(log_entry)
    
    async def check_dependencies(self) -> bool:
        """Check if all required dependencies are available"""
        self.log("🔍 Checking dependencies...")
        
        required_files = [
            "requirements.txt",
            "main.py",
            "app/",
            "scripts/create_admin.py",
            ".env"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            self.log(f"❌ Missing required files: {', '.join(missing_files)}", "ERROR")
            return False
        
        self.log("✅ All required files found")
        return True
    
    async def create_database_directories(self) -> bool:
        """Create necessary directories for the database and logs"""
        self.log("📁 Creating necessary directories...")
        
        directories = ["data", "logs"]
        
        try:
            for directory in directories:
                Path(directory).mkdir(exist_ok=True)
                self.log(f"  Created/verified directory: {directory}")
            
            self.log("✅ Directories created successfully")
            return True
            
        except Exception as e:
            self.log(f"❌ Failed to create directories: {e}", "ERROR")
            return False
    
    async def setup_admin_account(self) -> bool:
        """Setup default admin account for testing"""
        self.log("👤 Setting up admin account...")
        
        try:
            # Check if create_admin script exists
            admin_script = Path("scripts/create_admin.py")
            if not admin_script.exists():
                self.log("❌ Admin creation script not found", "ERROR")
                return False
            
            # Run admin creation script
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(admin_script),
                "--username", "admin",
                "--password", "admin123",
                "--name", "Test Administrator",
                "--email", "admin@example.com",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                self.log("✅ Admin account created successfully")
                self.log("   Username: admin")
                self.log("   Password: admin123")
                return True
            else:
                error_output = stderr.decode() if stderr else "Unknown error"
                if "already exists" in error_output.lower():
                    self.log("ℹ️  Admin account already exists")
                    return True
                else:
                    self.log(f"❌ Admin account creation failed: {error_output}", "ERROR")
                    return False
                    
        except Exception as e:
            self.log(f"❌ Admin account setup exception: {e}", "ERROR")
            return False
    
    async def verify_environment_config(self) -> bool:
        """Verify environment configuration"""
        self.log("⚙️  Verifying environment configuration...")
        
        try:
            env_file = Path(".env")
            if not env_file.exists():
                self.log("❌ .env file not found", "ERROR")
                return False
            
            # Read .env file and check for critical settings
            with open(env_file, 'r') as f:
                env_content = f.read()
            
            critical_settings = [
                "WAPI_URL",
                "WAPI_KEY",
                "SECRET_KEY",
                "DATABASE_URL"
            ]
            
            missing_settings = []
            for setting in critical_settings:
                if f"{setting}=" not in env_content:
                    missing_settings.append(setting)
            
            if missing_settings:
                self.log(f"⚠️  Missing environment settings: {', '.join(missing_settings)}", "WARN")
                self.log("   Tests may fail due to missing configuration", "WARN")
            else:
                self.log("✅ Environment configuration looks good")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Environment verification failed: {e}", "ERROR")
            return False
    
    async def check_docker_services(self) -> bool:
        """Check if Docker services are running (if using Docker)"""
        self.log("🐳 Checking Docker services...")
        
        try:
            # Check if docker-compose.yml exists
            compose_file = Path("docker-compose.yml")
            if not compose_file.exists():
                self.log("ℹ️  No docker-compose.yml found, skipping Docker check")
                return True
            
            # Check if Docker is available
            process = await asyncio.create_subprocess_exec(
                "docker", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                self.log("⚠️  Docker not available, skipping Docker services check", "WARN")
                return True
            
            # Check if any containers are running
            process = await asyncio.create_subprocess_exec(
                "docker-compose", "ps",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode()
                if "Up" in output:
                    self.log("✅ Docker services are running")
                else:
                    self.log("ℹ️  Docker services not running (this is OK for local testing)")
            else:
                self.log("ℹ️  Could not check Docker services status")
            
            return True
            
        except Exception as e:
            self.log(f"ℹ️  Docker check failed (this is OK): {e}")
            return True
    
    async def run_setup(self) -> bool:
        """Run complete setup process"""
        self.log("🚀 Starting PromptEnchanter test setup...")
        
        setup_steps = [
            ("Dependencies Check", self.check_dependencies),
            ("Create Directories", self.create_database_directories),
            ("Environment Config", self.verify_environment_config),
            ("Docker Services", self.check_docker_services),
            ("Admin Account Setup", self.setup_admin_account),
        ]
        
        failed_steps = []
        
        for step_name, step_function in setup_steps:
            self.log(f"\n📋 {step_name}")
            try:
                success = await step_function()
                if not success:
                    failed_steps.append(step_name)
            except Exception as e:
                self.log(f"❌ {step_name} failed with exception: {e}", "ERROR")
                failed_steps.append(step_name)
        
        # Summary
        self.log("\n" + "="*60)
        self.log("SETUP SUMMARY")
        self.log("="*60)
        
        if failed_steps:
            self.log(f"❌ {len(failed_steps)} step(s) failed:", "ERROR")
            for step in failed_steps:
                self.log(f"  • {step}", "ERROR")
            self.log("\n⚠️  Some tests may fail due to setup issues", "WARN")
            return False
        else:
            self.log("✅ All setup steps completed successfully!")
            self.log("\n🎯 System is ready for testing!")
            self.log("\nNext steps:")
            self.log("  1. Start the application: python main.py")
            self.log("  2. Run tests: python test_all_systems.py")
            return True
    
    def save_setup_log(self):
        """Save setup log to file"""
        try:
            with open("setup_log.txt", "w") as f:
                f.write("\n".join(self.log_messages))
            self.log(f"\n📋 Setup log saved to: setup_log.txt")
        except Exception as e:
            self.log(f"⚠️  Could not save setup log: {e}", "WARN")


async def main():
    """Main setup function"""
    print("🎯 PromptEnchanter Test Setup")
    print("This script will prepare your system for comprehensive testing.\n")
    
    setup = TestSetup()
    
    try:
        success = await setup.run_setup()
        setup.save_setup_log()
        
        if success:
            print("\n🎉 Setup completed successfully!")
            return True
        else:
            print("\n❌ Setup completed with issues. Check the log above.")
            return False
            
    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted by user")
        return False
    except Exception as e:
        print(f"\n💥 Setup failed with error: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Fatal setup error: {e}")
        sys.exit(1)
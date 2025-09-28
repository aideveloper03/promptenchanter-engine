#!/usr/bin/env python3
"""
Master test script for all PromptEnchanter systems
Runs comprehensive tests for user management, admin system, and support system
"""

import asyncio
import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path

class MasterTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    async def run_test_script(self, script_name: str, description: str) -> dict:
        """Run a test script and return its results"""
        self.log(f"🚀 Running {description}...")
        
        try:
            # Run the test script
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_name, self.base_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Parse output
            output = stdout.decode() if stdout else ""
            error_output = stderr.decode() if stderr else ""
            
            if process.returncode == 0:
                self.log(f"✅ {description} completed successfully")
                
                # Try to load results from JSON file
                result_file = script_name.replace('.py', '_results.json')
                if Path(result_file).exists():
                    with open(result_file, 'r') as f:
                        results = json.load(f)
                    return {"success": True, "results": results, "output": output}
                else:
                    return {"success": True, "output": output}
            else:
                self.log(f"❌ {description} failed with return code {process.returncode}", "ERROR")
                return {"success": False, "error": error_output, "output": output}
                
        except Exception as e:
            self.log(f"❌ {description} failed with exception: {e}", "ERROR")
            return {"success": False, "exception": str(e)}
    
    def analyze_results(self, test_name: str, results: dict) -> dict:
        """Analyze test results and provide summary"""
        analysis = {
            "test_name": test_name,
            "overall_success": results.get("success", False),
            "detailed_results": {}
        }
        
        if "results" in results:
            test_results = results["results"]
            total_tests = 0
            passed_tests = 0
            
            for key, value in test_results.items():
                total_tests += 1
                if isinstance(value, bool):
                    if value:
                        passed_tests += 1
                    analysis["detailed_results"][key] = {"status": "PASS" if value else "FAIL"}
                elif isinstance(value, dict):
                    if value.get("success"):
                        passed_tests += 1
                        analysis["detailed_results"][key] = {"status": "PASS"}
                    else:
                        analysis["detailed_results"][key] = {"status": "FAIL", "error": value.get("error", "Unknown")}
                else:
                    analysis["detailed_results"][key] = {"status": "UNKNOWN", "value": str(value)}
            
            analysis["summary"] = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            }
        
        return analysis
    
    async def run_all_tests(self) -> dict:
        """Run all system tests"""
        self.log("🎯 Starting comprehensive PromptEnchanter testing suite")
        self.log(f"   Testing URL: {self.base_url}")
        
        all_results = {}
        
        # Test configurations
        tests = [
            ("test_user_management.py", "User Management System Tests"),
            ("test_admin_system.py", "Admin System Tests"),
            ("test_support_system.py", "Support System Tests")
        ]
        
        # Run each test suite
        for script, description in tests:
            if Path(script).exists():
                results = await self.run_test_script(script, description)
                all_results[script] = results
                
                # Analyze results
                analysis = self.analyze_results(script, results)
                all_results[f"{script}_analysis"] = analysis
            else:
                self.log(f"❌ Test script not found: {script}", "ERROR")
                all_results[script] = {"success": False, "error": "Script not found"}
        
        return all_results
    
    def generate_summary_report(self, all_results: dict) -> str:
        """Generate a comprehensive summary report"""
        report = []
        report.append("=" * 80)
        report.append("PROMPTENCHANTER COMPREHENSIVE TEST REPORT")
        report.append("=" * 80)
        report.append(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Test URL: {self.base_url}")
        report.append("")
        
        # Overall statistics
        total_systems = 0
        successful_systems = 0
        total_tests = 0
        total_passed = 0
        
        for key, value in all_results.items():
            if key.endswith("_analysis"):
                total_systems += 1
                analysis = value
                
                if analysis.get("overall_success"):
                    successful_systems += 1
                
                if "summary" in analysis:
                    total_tests += analysis["summary"]["total_tests"]
                    total_passed += analysis["summary"]["passed_tests"]
        
        report.append("OVERALL SUMMARY")
        report.append("-" * 40)
        report.append(f"Systems Tested: {total_systems}")
        report.append(f"Systems Passing: {successful_systems}")
        report.append(f"Total Individual Tests: {total_tests}")
        report.append(f"Total Tests Passed: {total_passed}")
        report.append(f"Overall Success Rate: {(total_passed / total_tests * 100):.1f}%" if total_tests > 0 else "N/A")
        report.append("")
        
        # Detailed results for each system
        for key, value in all_results.items():
            if key.endswith("_analysis"):
                analysis = value
                system_name = analysis["test_name"].replace("test_", "").replace(".py", "").replace("_", " ").title()
                
                report.append(f"{system_name.upper()} TEST RESULTS")
                report.append("-" * 40)
                
                if "summary" in analysis:
                    summary = analysis["summary"]
                    report.append(f"Tests Run: {summary['total_tests']}")
                    report.append(f"Tests Passed: {summary['passed_tests']}")
                    report.append(f"Tests Failed: {summary['failed_tests']}")
                    report.append(f"Success Rate: {summary['success_rate']:.1f}%")
                    report.append("")
                    
                    # Detailed test results
                    if analysis["detailed_results"]:
                        report.append("Detailed Results:")
                        for test_name, test_result in analysis["detailed_results"].items():
                            status = test_result["status"]
                            emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
                            report.append(f"  {emoji} {test_name}: {status}")
                            if "error" in test_result:
                                report.append(f"    Error: {test_result['error']}")
                        report.append("")
                else:
                    status = "✅ PASS" if analysis["overall_success"] else "❌ FAIL"
                    report.append(f"Overall Status: {status}")
                    report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 40)
        
        failed_systems = []
        for key, value in all_results.items():
            if key.endswith("_analysis") and not value.get("overall_success"):
                system_name = value["test_name"].replace("test_", "").replace(".py", "").replace("_", " ").title()
                failed_systems.append(system_name)
        
        if failed_systems:
            report.append("Failed Systems:")
            for system in failed_systems:
                report.append(f"  • {system}")
            report.append("")
            report.append("Recommended Actions:")
            report.append("  1. Check server logs for detailed error information")
            report.append("  2. Verify database connections and dependencies")
            report.append("  3. Ensure all required environment variables are set")
            report.append("  4. Run individual test scripts for detailed debugging")
        else:
            report.append("✅ All systems passed testing!")
            report.append("  • User management system is working correctly")
            report.append("  • Admin system is functioning properly")
            report.append("  • Support system is operational")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


async def main():
    """Main test function"""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print(f"🎯 PromptEnchanter Comprehensive Testing Suite")
    print(f"Testing URL: {base_url}")
    print("")
    
    tester = MasterTester(base_url)
    
    try:
        # Run all tests
        all_results = await tester.run_all_tests()
        
        # Save detailed results
        with open("comprehensive_test_results.json", "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        
        # Generate and save summary report
        summary_report = tester.generate_summary_report(all_results)
        with open("test_summary_report.txt", "w") as f:
            f.write(summary_report)
        
        # Print summary to console
        print(summary_report)
        
        print(f"\n📋 Detailed results saved to: comprehensive_test_results.json")
        print(f"📋 Summary report saved to: test_summary_report.txt")
        
        return all_results
        
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
        return None
    except Exception as e:
        print(f"\n💥 Testing failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        results = asyncio.run(main())
        if results:
            print("\n🎉 Comprehensive testing completed!")
        else:
            print("\n❌ Testing was interrupted or failed")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)
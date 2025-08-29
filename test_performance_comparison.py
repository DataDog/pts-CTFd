#!/usr/bin/env python3
"""
Performance comparison script for CTFd test optimizations.

This script demonstrates the performance improvements achieved through:
1. Pytest fixtures vs create_ctfd/destroy_ctfd pattern
2. Parallel test execution with pytest-xdist
3. Optimized database operations

Usage:
    python test_performance_comparison.py
"""

import time
import subprocess
import sys


def run_command_with_timing(command, description):
    """Run a command and measure execution time"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Exit code: {result.returncode}")
        print(f"Duration: {duration:.2f} seconds")
        
        if result.returncode != 0:
            print("STDERR:", result.stderr)
        else:
            print("SUCCESS!")
            
        return duration, result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("TIMEOUT: Command took longer than 5 minutes")
        return 300, False


def main():
    """Run performance comparison tests"""
    print("CTFd Test Performance Comparison")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Single legacy test (baseline)
    duration, success = run_command_with_timing(
        "pytest tests/test_setup.py::test_setup_integrations -v",
        "Legacy Test (Single)"
    )
    results["legacy_single"] = {"duration": duration, "success": success}
    
    # Test 2: Optimized fixture-based test
    duration, success = run_command_with_timing(
        "pytest tests/api/v1/test_challenges_optimized.py::TestChallengesVisibility::test_api_challenges_visibility[public-200-200] -v",
        "Optimized Test (Single)"
    )
    results["optimized_single"] = {"duration": duration, "success": success}
    
    # Test 3: Multiple legacy tests (to show scaling issues)
    duration, success = run_command_with_timing(
        "pytest tests/test_setup.py tests/models/test_model_utils.py -v",
        "Legacy Tests (Multiple)"
    )
    results["legacy_multiple"] = {"duration": duration, "success": success}
    
    # Test 4: Multiple optimized tests with parallelization
    duration, success = run_command_with_timing(
        "pytest tests/api/v1/test_challenges_optimized.py -v -n 2",
        "Optimized Tests (Parallel)"
    )
    results["optimized_parallel"] = {"duration": duration, "success": success}
    
    # Test 5: Subset of original tests with parallelization
    duration, success = run_command_with_timing(
        "pytest tests/test_setup.py tests/models/ -v -n 2 --tb=short",
        "Original Tests (Parallel)"
    )
    results["original_parallel"] = {"duration": duration, "success": success}
    
    # Generate performance report
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result["success"] else "✗ FAIL"
        print(f"{test_name:20} | {result['duration']:8.2f}s | {status}")
    
    # Calculate improvements
    if results["legacy_single"]["success"] and results["optimized_single"]["success"]:
        improvement = (results["legacy_single"]["duration"] - results["optimized_single"]["duration"]) 
        improvement_pct = (improvement / results["legacy_single"]["duration"]) * 100
        print(f"\nSingle Test Improvement: {improvement:.2f}s ({improvement_pct:.1f}% faster)")
    
    if results["legacy_multiple"]["success"] and results["optimized_parallel"]["success"]:
        improvement = (results["legacy_multiple"]["duration"] - results["optimized_parallel"]["duration"])
        improvement_pct = (improvement / results["legacy_multiple"]["duration"]) * 100
        print(f"Multiple Test Improvement: {improvement:.2f}s ({improvement_pct:.1f}% faster)")
    
    print("\nRecommendations:")
    print("1. Migrate high-frequency test files to fixture-based pattern")
    print("2. Use 'make test-fast' for development testing")
    print("3. Use 'make test-unit' for quick feedback during coding")
    print("4. Reserve full test suite for CI/CD pipelines")


if __name__ == "__main__":
    main()
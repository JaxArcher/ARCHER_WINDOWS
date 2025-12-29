#!/usr/bin/env python3
"""
Basic test script for ARCHER Enhancements Module
Tests only the core functionality without external dependencies
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_file_structure():
    """Test that all enhancement files exist."""
    print("Testing File Structure...")
    
    enhancements_dir = Path("src/enhancements")
    
    required_files = [
        "__init__.py",
        "integration_agent.py",
        "knowledge_base.py",
        "conversation_enhancer.py",
        "call_transcription.py"
    ]
    
    all_exist = True
    for file_name in required_files:
        file_path = enhancements_dir / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"SUCCESS: {file_name} exists ({size} bytes)")
        else:
            print(f"FAILED: {file_name} not found")
            all_exist = False
    
    return all_exist

def test_syntax():
    """Test that Python files have valid syntax."""
    print("\nTesting Python Syntax...")
    
    import py_compile
    import glob
    
    python_files = glob.glob("src/enhancements/*.py")
    
    all_valid = True
    for file_path in python_files:
        try:
            with open(file_path, 'rb') as f:
                py_compile.compile(f.read(), file_path, 'exec')
            print(f"SUCCESS: {Path(file_path).name} syntax valid")
        except SyntaxError as e:
            print(f"FAILED: {Path(file_path).name} syntax error: {e}")
            all_valid = False
        except Exception as e:
            print(f"FAILED: {Path(file_path).name} error: {e}")
            all_valid = False
    
    return all_valid

def test_import_structure():
    """Test that the module structure is correct."""
    print("\nTesting Import Structure...")
    
    try:
        # Test that __init__.py has correct exports
        import importlib.util
        spec = importlib.util.spec_from_file_location("enhancements", "src/enhancements/__init__.py")
        module = importlib.util.module_from_spec(spec)
        
        # Check that expected classes are in __all__
        expected_classes = [
            "IntegrationAgent",
            "KnowledgeBaseRAG",
            "ConversationEnhancer",
            "CallTranscriptionService"
        ]
        
        # Read the file to check __all__
        with open("src/enhancements/__init__.py", 'r') as f:
            content = f.read()
        
        for class_name in expected_classes:
            if class_name in content:
                print(f"SUCCESS: {class_name} found in __init__.py")
            else:
                print(f"FAILED: {class_name} not found in __init__.py")
                return False
        
        return True
        
    except Exception as e:
        print(f"FAILED: Import structure test failed: {e}")
        return False

def test_class_definitions():
    """Test that all major classes are defined."""
    print("\nTesting Class Definitions...")
    
    try:
        # Read each file and check for class definitions
        files_to_check = {
            "integration_agent.py": ["IntegrationAgent", "ToolConfig", "GoogleDriveIntegration", "RESTAPIIntegration"],
            "knowledge_base.py": ["KnowledgeBaseRAG", "DocumentMetadata", "KnowledgeChunk"],
            "conversation_enhancer.py": ["ConversationEnhancer"],
            "call_transcription.py": ["CallTranscriptionService", "SpeakerSegment", "CallTranscript"]
        }
        
        all_found = True
        for file_name, class_names in files_to_check.items():
            file_path = Path("src/enhancements") / file_name
            with open(file_path, 'r') as f:
                content = f.read()
            
            for class_name in class_names:
                if f"class {class_name}" in content:
                    print(f"SUCCESS: {class_name} defined in {file_name}")
                else:
                    print(f"FAILED: {class_name} not found in {file_name}")
                    all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"FAILED: Class definition test failed: {e}")
        return False

def test_documentation():
    """Test that files have proper documentation."""
    print("\nTesting Documentation...")
    
    try:
        python_files = [
            "src/enhancements/integration_agent.py",
            "src/enhancements/knowledge_base.py",
            "src/enhancements/conversation_enhancer.py",
            "src/enhancements/call_transcription.py"
        ]
        
        all_documented = True
        for file_path in python_files:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for module docstring
            if content.startswith('"""') or content.startswith("'''"):
                print(f"SUCCESS: {Path(file_path).name} has module docstring")
            else:
                print(f"FAILED: {Path(file_path).name} missing module docstring")
                all_documented = False
        
        return all_documented
        
    except Exception as e:
        print(f"FAILED: Documentation test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("ARCHER Enhancements Module Basic Test Suite")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Python Syntax", test_syntax),
        ("Import Structure", test_import_structure),
        ("Class Definitions", test_class_definitions),
        ("Documentation", test_documentation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\nRunning {test_name}...")
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nOverall: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("All basic tests passed! Enhancements module structure is correct.")
        print("Note: Full functionality testing requires additional dependencies.")
        return 0
    else:
        print("Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
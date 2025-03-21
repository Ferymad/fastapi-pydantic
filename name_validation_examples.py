#!/usr/bin/env python
"""
Name Validation Examples

This script demonstrates the name validation capabilities of the FastAPI-Pydantic
validation service by testing various valid and invalid name inputs.

Run this script to test name validation against a running instance of the service.
"""

import json
import sys
import requests
from typing import Dict, Any, List, Optional

# Configuration
API_URL = "http://localhost:8000/validate"
VALID_NAMES = [
    "John Smith",
    "María Rodríguez",
    "Jean-Claude O'Brien",
    "Søren Kierkegaard",
    "Johann Sebastian Bach",
    "Николай Римский-Корсаков",  # Nikolai Rimsky-Korsakov
    "李 白",  # Li Bai
]

INVALID_NAMES = [
    "asdfghjkl",  # Random characters
    "qwertyuiop",  # Keyboard pattern
    "aaaaaaaaa",   # Repeating characters
    "x",           # Too short
    "123456",      # Numbers
    "!@#$%^",      # Special characters
]

NAME_FIELDS = [
    "name",
    "customer_name",
    "full_name",
    "first_name",
    "last_name",
    "contact_name",
    "person_name"
]

def create_validation_request(name: str, field_name: str = "customer_name") -> Dict[str, Any]:
    """Create a validation request with the given name."""
    return {
        "data": {
            field_name: name,
            "email": "test@example.com",  # Including other fields to make it realistic
            "order_date": "2023-10-15"
        },
        "schema": {
            field_name: {"type": "string", "required": True},
            "email": {"type": "string", "format": "email", "required": True},
            "order_date": {"type": "string", "format": "date", "required": True}
        },
        "validation_type": "order",
        "validation_level": "standard"
    }

def validate_name(name: str, field_name: str = "customer_name") -> Dict[str, Any]:
    """Send a validation request to the API and return the response."""
    request = create_validation_request(name, field_name)
    try:
        response = requests.post(API_URL, json=request)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        sys.exit(1)

def print_validation_result(name: str, result: Dict[str, Any], field_name: str) -> None:
    """Print the validation result in a readable format."""
    is_valid = result.get("is_valid", False)
    
    print(f"Name: '{name}' in field '{field_name}'")
    print(f"Is valid: {'✅ YES' if is_valid else '❌ NO'}")
    
    if not is_valid:
        # Check for structural validation issues
        if "structural_validation" in result and result["structural_validation"]:
            structural_validation = result["structural_validation"]
            if not structural_validation.get("is_structurally_valid", True):
                print("Structural validation errors:")
                for error in structural_validation.get("errors", []):
                    print(f"  - {error}")
                
                if "suggestions" in structural_validation and structural_validation["suggestions"]:
                    print("Suggestions:")
                    for suggestion in structural_validation["suggestions"]:
                        print(f"  - {suggestion}")
        
        # Check for semantic validation issues
        if "semantic_validation" in result and result["semantic_validation"]:
            semantic_validation = result["semantic_validation"]
            if not semantic_validation.get("is_semantically_valid", True):
                print("Semantic validation issues:")
                for issue in semantic_validation.get("issues", []):
                    print(f"  - {issue}")
                
                if "suggestions" in semantic_validation and semantic_validation["suggestions"]:
                    print("Suggestions:")
                    for suggestion in semantic_validation["suggestions"]:
                        print(f"  - {suggestion}")
    
    print("-" * 80)

def test_valid_names() -> None:
    """Test a range of valid names."""
    print("\n=== Testing Valid Names ===\n")
    for name in VALID_NAMES:
        result = validate_name(name)
        print_validation_result(name, result, "customer_name")

def test_invalid_names() -> None:
    """Test a range of invalid names."""
    print("\n=== Testing Invalid Names ===\n")
    for name in INVALID_NAMES:
        result = validate_name(name)
        print_validation_result(name, result, "customer_name")

def test_different_field_names() -> None:
    """Test name validation across different field names."""
    print("\n=== Testing Different Field Names ===\n")
    # Pick one valid and one invalid name
    valid_name = VALID_NAMES[0]
    invalid_name = INVALID_NAMES[0]
    
    for field_name in NAME_FIELDS:
        # Test with valid name
        result = validate_name(valid_name, field_name)
        print_validation_result(valid_name, result, field_name)
        
        # Test with invalid name
        result = validate_name(invalid_name, field_name)
        print_validation_result(invalid_name, result, field_name)

def main() -> None:
    """Run all name validation tests."""
    print("=== Name Validation Examples ===")
    print(f"API URL: {API_URL}")
    print("Testing connection to API...")
    
    try:
        # Test API connection with a simple request
        test_request = create_validation_request("Test User")
        response = requests.post(API_URL, json=test_request)
        response.raise_for_status()
        print("API connection successful!")
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API: {e}")
        print("Make sure the validation service is running at the specified URL.")
        sys.exit(1)
    
    # Run tests
    test_valid_names()
    test_invalid_names()
    test_different_field_names()
    
    print("\nAll name validation examples completed!")

if __name__ == "__main__":
    main() 
import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.validation import validate_name_content, NameStr
from pydantic import BaseModel, ValidationError

client = TestClient(app)

# Test model using our custom NameStr type
class NameModel(BaseModel):
    name: NameStr

# Test direct validation function
def test_validate_name_content():
    # Valid names should pass
    assert validate_name_content("John Doe") == "John Doe"
    assert validate_name_content("María Rodríguez") == "María Rodríguez"
    assert validate_name_content("Jean-Claude O'Brien") == "Jean-Claude O'Brien"
    
    # Invalid names should raise exceptions
    with pytest.raises(ValueError):
        validate_name_content("asdfghjkl")  # Random characters
    
    with pytest.raises(ValueError):
        validate_name_content("aaaaaaaaaaa")  # Repeating characters
    
    with pytest.raises(ValueError):
        validate_name_content("qwertyuiop")  # Keyboard pattern
        
    with pytest.raises(ValueError):
        validate_name_content("a")  # Too short

# Test NameStr type in a Pydantic model
def test_name_str_validation():
    # Valid names should work
    valid_model = NameModel(name="Jane Smith")
    assert valid_model.name == "Jane Smith"
    
    # Invalid names should fail validation
    with pytest.raises(ValidationError):
        NameModel(name="asdfghjkl")  # Random characters
    
    with pytest.raises(ValidationError):
        NameModel(name="123456")  # Numbers aren't valid names

# Test the API validation endpoint with name validation
def test_validation_api_with_name():
    # Test with valid name
    valid_request = {
        "data": {
            "customer_name": "John Smith",
            "email": "john@example.com",
            "order_date": "2023-10-15"
        },
        "schema": {
            "customer_name": {"type": "string", "required": True},
            "email": {"type": "string", "format": "email", "required": True},
            "order_date": {"type": "string", "format": "date", "required": True}
        },
        "validation_type": "order",
        "validation_level": "standard"
    }
    
    response = client.post("/validate", json=valid_request)
    assert response.status_code == 200
    result = response.json()
    
    # In a test environment, we should get some validation response
    assert "is_valid" in result
    
    # Test with invalid name
    invalid_request = {
        "data": {
            "customer_name": "asdfghjkl",  # Invalid name
            "email": "john@example.com",
            "order_date": "2023-10-15"
        },
        "schema": {
            "customer_name": {"type": "string", "required": True},
            "email": {"type": "string", "format": "email", "required": True},
            "order_date": {"type": "string", "format": "date", "required": True}
        },
        "validation_type": "order",
        "validation_level": "standard"
    }
    
    response = client.post("/validate", json=invalid_request)
    assert response.status_code == 200
    result = response.json()
    
    # Check if there's a semantic validation result
    # If semantic validation is not available in test, validate structural errors
    if "semantic_validation" in result and result["semantic_validation"] is not None:
        # Check for semantic validation failure
        assert result["semantic_validation"]["is_semantically_valid"] == False
        
        # Verify the error message contains information about the name validation failure
        name_issue_found = any("customer_name" in issue for issue in result["semantic_validation"]["issues"])
        assert name_issue_found, "Name validation issue not found in response"
    else:
        # If semantic validation is disabled in test environment, check that structural validation 
        # catches the invalid name on field creation
        assert result["is_valid"] == False
        assert "structural_validation" in result
        
        # Check if we have validation errors field or different structure
        if "validation_errors" in result["structural_validation"]:
            validation_errors = result["structural_validation"]["validation_errors"]
            assert len(validation_errors) > 0, "No validation errors found"
        elif "errors" in result["structural_validation"]:
            errors = result["structural_validation"]["errors"]
            assert len(errors) > 0, "No errors found" 
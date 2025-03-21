# Name Validation

This document explains the name validation capabilities implemented in the FastAPI-Pydantic validation service.

## Overview

The name validation feature provides robust validation for name fields in API requests. It's designed to catch common issues with name inputs, such as:

- Random character sequences (e.g., "asdfghjkl")
- Keyboard patterns (e.g., "qwertyuiop")
- Repeating characters (e.g., "aaaaaaaa")
- Names that are too short
- Names with invalid character distributions

## Implementation Details

Our name validation uses a hybrid approach that combines:

1. **Pattern-based validation**: Checks for valid characters and patterns in names
2. **Heuristic-based validation**: Analyzes character distribution and keyboard patterns
3. **Pydantic integration**: Uses Pydantic v2's `Annotated` and `AfterValidator` features

### Custom Type: `NameStr`

The validation creates a custom Pydantic type `NameStr` that can be used in schemas:

```python
NameStr = Annotated[str, AfterValidator(validate_name_content)]
```

### Validation Function

The core validation logic is in the `validate_name_content` function, which checks:

1. **Character distribution**: Ensures the name has a reasonable distribution of characters
2. **Keyboard patterns**: Detects sequences that match keyboard layouts (e.g., "qwerty")
3. **Repeating characters**: Identifies sequences with excessive repetition
4. **Name length**: Validates that names are of reasonable length

## Usage in API Validation

### Automatic Field Detection

The validation service automatically applies name validation to fields with common name identifiers:

- `name`
- `customer_name`
- `full_name`
- `first_name`
- `last_name`
- `contact_name`
- `person_name`

### Schema Integration

When creating a schema, name fields are automatically enhanced with name validation:

```json
{
  "customer_name": {"type": "string", "required": true}
}
```

The validation service recognizes this as a name field and applies the appropriate validation.

### Error Messages

When name validation fails, detailed error messages are provided to guide users:

```json
{
  "is_valid": false,
  "semantic_validation": {
    "is_semantically_valid": false,
    "issues": [
      "Field 'customer_name': Invalid name: appears to contain random characters or keyboard pattern"
    ],
    "suggestions": [
      "Provide a valid name for 'customer_name'"
    ]
  }
}
```

## Testing

The name validation system includes comprehensive tests in `tests/test_name_validation.py` that verify:

1. Direct function validation with valid and invalid names
2. Integration with Pydantic models
3. End-to-end API validation with name fields

## Limitations

Current limitations include:

1. Limited support for non-Latin alphabets and international naming conventions
2. No validation for name components (first name, last name, etc.)
3. False positives may occur for uncommon but valid names

## Future Improvements

Planned improvements include:

1. Enhanced support for international names
2. Machine learning-based name validation
3. Configurable validation rules
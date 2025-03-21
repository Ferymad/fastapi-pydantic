# FastAPI-Pydantic Validation Service

A robust validation service built with FastAPI and Pydantic v2 that provides advanced validation capabilities for API outputs including format validation.

## Features

- **Schema-Based Validation**: Validate data against a specified schema with support for nested objects
- **Format Validation**: Validate common formats including:
  - Email validation
  - Date format validation
  - Phone number pattern validation
  - **Advanced Name Validation**: Detect random character sequences, keyboard patterns, and other issues in name fields
- **Semantic Validation**: Check data consistency and relationships
- **Multiple Validation Levels**: Basic, standard, and strict validation options
- **Detailed Error Messages**: Get comprehensive error information and helpful suggestions

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/fastapi-pydantic.git
cd fastapi-pydantic

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

Start the server:

```bash
uvicorn app.main:app --reload
```

### Validate Data

Validate data against a schema:

```bash
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "customer_name": "John Smith",
      "email": "john@example.com",
      "order_date": "2023-10-15",
      "items": ["item1", "item2"],
      "total_price": 29.99
    },
    "schema": {
      "customer_name": {"type": "string", "required": true},
      "email": {"type": "string", "format": "email", "required": true},
      "order_date": {"type": "string", "format": "date", "required": true},
      "items": {"type": "array", "items": {"type": "string"}, "required": true},
      "total_price": {"type": "number", "required": true}
    },
    "validation_type": "order",
    "validation_level": "standard"
  }'
```

## Name Validation

The service includes advanced name validation to detect:

- Random character sequences (e.g., "asdfghjkl")
- Keyboard patterns (e.g., "qwertyuiop")
- Repeating characters (e.g., "aaaaaaaa")
- Names that are too short
- Names with invalid character distributions

Name validation is automatically applied to fields with common name identifiers:
- `name`
- `customer_name`
- `full_name`
- `first_name`
- `last_name`
- `contact_name`
- `person_name`

If a field contains invalid name content, you'll receive descriptive error messages.

## Documentation

For more detailed documentation, visit:

- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Name Validation: [./docs/name_validation.md](./docs/name_validation.md)

## Testing

Run tests with pytest:

```bash
python -m pytest
```

Run name validation tests specifically:

```bash
python -m pytest tests/test_name_validation.py -v
```

## License

MIT 
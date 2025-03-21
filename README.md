# FastAPI-Pydantic Validation Service

A robust validation service built with FastAPI and Pydantic v2 that provides advanced validation capabilities for API outputs including format validation and a schema repository with versioning support.

## Features

- **Schema-Based Validation**: Validate data against a specified schema with support for nested objects
- **Schema Repository**: Store, retrieve, and manage validation schemas with versioning support
- **Format Validation**: Validate common formats including:
  - Email validation
  - Date format validation
  - Phone number pattern validation
  - **Advanced Name Validation**: Detect random character sequences, keyboard patterns, and other issues in name fields
- **Semantic Validation**: Check data consistency and relationships
- **Multiple Validation Levels**: Basic, standard, and strict validation options
- **Detailed Error Messages**: Get comprehensive error information and helpful suggestions
- **API Key Authentication**: Secure your endpoints with API key validation
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Structured Error Responses**: Consistent, detailed validation error format with suggestions

## Installation

### Local Development

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

# Create environment file
cp .env.example .env
# Edit .env with your configuration
```

### Configuration

Edit the `.env` file to set up your environment:

```
# API Configuration
API_KEY=your_api_key_here
AUTH_ENABLED=true

# OpenAI Configuration (required for enhanced validation)
OPENAI_API_KEY=your_openai_api_key_here
SEMANTIC_VALIDATION_ENABLED=true

# Service Information
SERVICE_NAME=ai-validation-service
SERVICE_VERSION=0.1.0
ENVIRONMENT=development  # development, staging, production

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Usage

### Start the Server

For local development:

```bash
uvicorn app.main:app --reload
```

With Docker:

```bash
# Build and start the container
docker-compose up --build

# Run in background
docker-compose up -d
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/validate` | POST | Validate data against a schema or stored schema |
| `/schemas` | GET | List all available schemas |
| `/schemas` | POST | Create a new schema |
| `/schemas/{schema_name}` | GET | Get schema details |
| `/schemas/{schema_name}` | PUT | Update a schema |
| `/schemas/{schema_name}` | DELETE | Delete a schema |
| `/schemas/{schema_name}/versions` | GET | Get schema version history |
| `/schemas/{schema_name}/validate` | POST | Validate data against a stored schema |
| `/health` | GET | Health check endpoint |

### Basic Validation

Validate data against a schema:

```bash
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
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
    "type": "order",
    "level": "standard"
  }'
```

### Schema Repository

#### Create a Schema

```bash
curl -X POST "http://localhost:8000/schemas/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "name": "customer_order",
    "description": "Validation schema for customer orders",
    "schema": {
      "customer_name": {"type": "string", "required": true},
      "email": {"type": "string", "format": "email", "required": true},
      "order_date": {"type": "string", "format": "date", "required": true},
      "items": {"type": "array", "items": {"type": "string"}, "required": true},
      "total_price": {"type": "number", "required": true}
    },
    "validation_level": "standard",
    "example": {
      "customer_name": "John Smith",
      "email": "john@example.com",
      "order_date": "2023-10-15",
      "items": ["item1", "item2"],
      "total_price": 29.99
    }
  }'
```

#### Validate Using a Stored Schema

```bash
curl -X POST "http://localhost:8000/schemas/customer_order/validate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "customer_name": "John Smith",
    "email": "john@example.com",
    "order_date": "2023-10-15",
    "items": ["item1", "item2"],
    "total_price": 29.99
  }'
```

You can also use the main validation endpoint with a schema name:

```bash
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "data": {
      "customer_name": "John Smith",
      "email": "john@example.com",
      "order_date": "2023-10-15",
      "items": ["item1", "item2"],
      "total_price": 29.99
    },
    "schema_name": "customer_order",
    "type": "order",
    "level": "standard"
  }'
```

#### List All Schemas

```bash
curl -X GET "http://localhost:8000/schemas/" \
  -H "X-API-Key: your_api_key"
```

#### Get Schema Details

```bash
curl -X GET "http://localhost:8000/schemas/customer_order" \
  -H "X-API-Key: your_api_key"
```

#### Update a Schema

```bash
curl -X PUT "http://localhost:8000/schemas/customer_order" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "description": "Updated validation schema for customer orders",
    "schema": {
      "customer_name": {"type": "string", "required": true},
      "email": {"type": "string", "format": "email", "required": true},
      "order_date": {"type": "string", "format": "date", "required": true},
      "items": {"type": "array", "items": {"type": "string"}, "required": true},
      "total_price": {"type": "number", "required": true},
      "customer_notes": {"type": "string", "required": false}
    },
    "version_notes": "Added customer_notes field"
  }'
```

#### Delete a Schema

```bash
curl -X DELETE "http://localhost:8000/schemas/customer_order" \
  -H "X-API-Key: your_api_key"
```

#### Get Schema Version History

```bash
curl -X GET "http://localhost:8000/schemas/customer_order/versions" \
  -H "X-API-Key: your_api_key"
```

## Validation Response Format

The validation endpoint returns a structured response:

```json
{
  "is_valid": true|false,
  "structural_validation": {
    "is_structurally_valid": true|false,
    "errors": [
      {
        "type": "error_type",
        "loc": ["field_name"],
        "msg": "Human-readable error message",
        "input": "Invalid input value",
        "url": "https://errors.pydantic.dev/...",
        "suggestion": "How to fix the error"
      }
    ],
    "suggestions": ["Fix validation error: ..."]
  },
  "semantic_validation": {
    "is_semantically_valid": true|false,
    "semantic_score": 0.95,
    "issues": ["Description of semantic issues"],
    "suggestions": ["How to fix semantic issues"]
  }
}
```

## Specialized Validation

### Name Validation

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

## Deployment

### Docker Deployment

The project includes Docker and Docker Compose configuration for easy deployment:

```bash
# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

### Production Considerations

For production deployment:

1. **API Security**:
   - Always set `AUTH_ENABLED=true`
   - Use a strong, randomly generated API key
   - Consider using HTTPS with a reverse proxy like Nginx

2. **Data Persistence**:
   - Mount a volume for the `data` directory to persist schemas
   - For production, consider migrating to a database-backed storage

3. **Environment Variables**:
   - Set `ENVIRONMENT=production`
   - Configure appropriate logging level
   - Never expose sensitive keys in your repository

4. **Monitoring**:
   - Set up monitoring for the `/health` endpoint
   - Consider enabling Logfire integration for advanced monitoring

For a comprehensive deployment preparation guide, see the [Deployment Checklist](docs/deployment_checklist.md).

### Manual Deployment

For manual deployment without Docker:

1. Set up a Python environment (3.8+)
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables or create a `.env` file
4. Run with a production ASGI server:
   ```bash
   gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000
   ```

## Documentation

For more detailed documentation, visit:

- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc UI: [http://localhost:8000/redoc](http://localhost:8000/redoc)
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

## Project Structure

```
fastapi-pydantic/
│
├── app/                    # Application code
│   ├── api/                # API routes
│   │   └── routes/         # Route handlers
│   ├── repository/         # Schema repository implementation
│   ├── main.py             # FastAPI application entry point
│   ├── models.py           # Pydantic data models
│   ├── validation.py       # Validation logic
│   ├── auth.py             # Authentication utilities
│   ├── config.py           # Configuration management
│   └── monitoring.py       # Logging and monitoring
│
├── data/                   # Data storage
│   └── schemas/            # Schema repository storage
│
├── docs/                   # Documentation
├── tests/                  # Tests
├── examples/               # Example usage scripts
├── scripts/                # Utility scripts
│
├── .env.example            # Example environment variables
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose configuration
└── README.md               # Project documentation
```

## Known Issues and Limitations

- Pydantic warning about "field name schema shadows an attribute in parent BaseModel" - This is a harmless warning about field naming and doesn't affect functionality
- Semantic validation requires an OpenAI API key and connection to function
- Schema repository currently uses file-based storage which should be upgraded to a database for high-load production environments

## License

MIT 
# AI Output Validation Service

A lightweight validation service built with FastAPI and Pydantic v2 to validate AI-generated outputs with both standard structural validation and enhanced semantic validation.

## Features

- Dynamic validation against provided schemas
- Enhanced semantic validation with PydanticAI
- Structured logging and monitoring with Logfire
- Configurable validation levels
- Optional API key authentication
- Detailed validation reports with suggestions for improvement

## Getting Started

### Prerequisites

- Python 3.8+
- Docker (optional)
- OpenAI API Key (for semantic validation)

### Local Development

1. Clone the repository
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables (create a .env file):
   ```
   # Required for semantic validation
   OPENAI_API_KEY=your_openai_api_key
   
   # Optional configuration
   SERVICE_NAME=ai-output-validator
   SERVICE_VERSION=0.1.0
   ENV=development
   AUTH_ENABLED=false
   SECRET_KEY=your_secret_key
   LOGFIRE_API_KEY=your_logfire_api_key
   ```
5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```
6. Access the API documentation at http://localhost:8000/docs

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for semantic validation | "" |
| `SERVICE_NAME` | Name of the service | "ai-output-validator" |
| `SERVICE_VERSION` | Version of the service | "0.1.0" |
| `ENV` | Environment (development, staging, production) | "development" |
| `AUTH_ENABLED` | Whether authentication is enabled | false |
| `SECRET_KEY` | Secret key for API authentication | "dev_secret_key_change_in_production" |
| `LOGFIRE_API_KEY` | Logfire API key for monitoring | "" |
| `LOG_LEVEL` | Logging level | "INFO" |
| `CORS_ORIGINS` | Comma-separated list of allowed origins for CORS | "*" |

### Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t ai-output-validator .
   ```
2. Run the container:
   ```bash
   docker run -p 8000:8000 \
     -e OPENAI_API_KEY=your_openai_api_key \
     -e ENV=production \
     -e AUTH_ENABLED=true \
     -e SECRET_KEY=your_secret_key \
     ai-output-validator
   ```

## API Endpoints

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/validate` | POST | Validates AI output against provided schema with semantic checks | Optional API Key |
| `/health` | GET | Health check endpoint | None |
| `/` | GET | API information | None |

### Validation Request Format

The validation endpoint accepts a JSON body with the following fields:

```json
{
  "content": { 
    "key1": "value1",
    "key2": "value2"
  },
  "schema": {
    "key1": {"type": "str", "required": true},
    "key2": {"type": "str", "required": true}
  },
  "validation_type": "generic",
  "validation_level": "standard"
}
```

- `content`: The AI-generated output to validate
- `schema`: Pydantic schema definition for validation
- `validation_type`: Type of validation to perform (generic, recommendation, summary, etc.)
- `validation_level`: Level of semantic validation (basic, standard, strict)

### Validation Response Format

```json
{
  "standard_validation": {
    "status": "valid",
    "errors": [],
    "validated_data": { "key1": "value1", "key2": "value2" }
  },
  "semantic_validation": {
    "is_semantically_valid": true,
    "semantic_score": 0.95,
    "issues": [],
    "suggestions": []
  },
  "processing_time_ms": 450.23
}
```

## Enhanced Validation with PydanticAI

The service provides enhanced validation with semantic checks powered by PydanticAI. This goes beyond structural validation to evaluate the content quality, relevance, and coherence.

### How Enhanced Validation Works

1. First, standard structural validation is performed using the provided schema
2. Then, semantic validation is performed using PydanticAI if the structural validation passes
3. The results include both standard and semantic validation details, with suggestions for improvement

### Example Request

```python
import requests

# Your AI output data and schema
validation_request = {
    "content": {
        "response_text": "This is a response from the AI",
        "confidence_score": 0.92
    },
    "schema": {
        "response_text": {"type": "str", "required": True},
        "confidence_score": {"type": "float", "required": False}
    },
    "validation_type": "generic",
    "validation_level": "standard"
}

# Send to enhanced validation service
response = requests.post(
    "http://your-service-url/validate",
    headers={"x-api-key": "your-secret-key"},  # Only needed if AUTH_ENABLED=true
    json=validation_request
)

# Check validation result
result = response.json()
if result["standard_validation"]["status"] == "valid":
    if result["semantic_validation"]["is_semantically_valid"]:
        print("Both structural and semantic validation passed!")
    else:
        print("Structural validation passed, but semantic issues found:")
        for issue in result["semantic_validation"]["issues"]:
            print(f" - {issue}")
else:
    print("Structural validation failed:", result["standard_validation"]["errors"])
```

### Validation Levels

You can specify the validation level for semantic checks:

- `basic`: Light validation focused on basic structure and content
- `standard` (default): Balanced validation for most use cases
- `strict`: Rigorous validation with comprehensive checks

## Monitoring and Logging

The service includes structured logging and monitoring capabilities:

- All requests and validation events are logged with detailed context
- When configured with a Logfire API key, logs are sent to Logfire for analysis
- Processing times are tracked and included in response headers
- Standard Python logging is used as a fallback when Logfire is not configured

## License

MIT 
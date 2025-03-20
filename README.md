# AI Output Validation Service

A lightweight validation service built with FastAPI and Pydantic v2 to validate AI agent outputs against predefined schemas.

## Features

- Validation endpoints for different AI output types
- API key authentication for security
- Detailed validation error responses
- Easy integration with n8n workflows

## Getting Started

### Prerequisites

- Python 3.8+
- Docker (optional)

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
4. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```
5. Access the API documentation at http://localhost:8000/docs

### Environment Variables

- `API_KEY`: API key for authentication (default: "test_api_key")

### Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t ai-validation-service .
   ```
2. Run the container:
   ```bash
   docker run -p 8000:8000 -e API_KEY=your_api_key ai-validation-service
   ```

## API Endpoints

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/validate/{validation_type}` | POST | Validates AI output against specified schema | API Key |
| `/health` | GET | Health check endpoint | None |

### Supported Validation Types

- `generic`: Basic validation for any AI output
- `recommendation`: Validates recommendation-style outputs
- `summary`: Validates text summary outputs
- `classification`: Validates classification outputs

## n8n Integration

### Example Workflow

1. Set up an AI agent node in n8n (e.g., OpenAI)
2. Add an HTTP Request node:
   - Method: POST
   - URL: `http://your-service-url/validate/recommendation`
   - Headers: `x-api-key: your-api-key`
   - Body: Output from the AI agent node
3. Add a Switch node to handle the validation result:
   - Valid case: `{{$node["HTTP Request"].json["status"] === "valid"}}`
   - Invalid case: `{{$node["HTTP Request"].json["status"] === "invalid"}}`

## License

MIT 
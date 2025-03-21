# Deployment Checklist for FastAPI-Pydantic Validation Service

This checklist provides the steps necessary to prepare the validation service for production deployment.

## Pre-Deployment Tasks

- [ ] Update version number in `config.py` if needed
- [ ] Verify all tests are passing: `python -m pytest`
- [ ] Check for security vulnerabilities in dependencies: `pip-audit`
- [ ] Make sure `.env` file is properly configured and not committed to git
- [ ] Update documentation (README.md, API docs, etc.)
- [ ] Create a production-ready `.env` file with secure keys

## Security Configuration

- [ ] Generate a strong API key (consider using a password manager or `openssl rand -hex 32`)
- [ ] Set `AUTH_ENABLED=true` in production environments
- [ ] Configure CORS settings appropriately for your deployment
- [ ] Set up rate limiting if you expect high traffic
- [ ] If using semantic validation, secure your OpenAI API key

## Environment Setup

- [ ] Configure environment variables for production:
  - [ ] `ENVIRONMENT=production`
  - [ ] `LOG_LEVEL=INFO` (or `WARNING` for high-traffic deployments)
  - [ ] `API_KEY=<secure-api-key>`
  - [ ] `AUTH_ENABLED=true`
  - [ ] `SERVICE_NAME=ai-output-validator` (or your preferred name)
  - [ ] `SERVICE_VERSION=<current-version>`

## Docker Deployment

- [ ] Build and test Docker image locally:
  ```bash
  docker build -t validation-service .
  docker run -p 8000:8000 --env-file .env validation-service
  ```
- [ ] Test health check endpoint: `curl http://localhost:8000/health`
- [ ] Test a sample validation request to ensure everything is working
- [ ] If using Docker Compose, test the full stack:
  ```bash
  docker-compose up -d
  # Test endpoints
  docker-compose logs
  docker-compose down
  ```

## Infrastructure Setup

- [ ] Set up domain name and DNS records if needed
- [ ] Configure a reverse proxy (like Nginx) for HTTPS
- [ ] Set up SSL certificates (consider Let's Encrypt)
- [ ] Configure firewall to only expose necessary ports
- [ ] Set up monitoring for the service (consider Prometheus/Grafana)
- [ ] Configure backup solution for schema repository data

## Production Deployment

- [ ] Deploy to staging environment first if available
- [ ] Deploy to production:
  ```bash
  # Using Docker
  docker-compose -f docker-compose.prod.yml up -d
  
  # Or manually
  gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000
  ```
- [ ] Verify the deployment with health check
- [ ] Test key functionality with production configuration
- [ ] Monitor logs for any issues

## Post-Deployment

- [ ] Set up regular backup of schema repository data
- [ ] Configure alerts for service downtime
- [ ] Document deployment details for the team
- [ ] Create a rollback plan in case of issues
- [ ] Schedule regular dependency updates
- [ ] Set up log rotation to prevent disk space issues

## Scaling Considerations

For high-load environments:

- [ ] Consider using a database backend for schema storage
- [ ] Set up load balancing across multiple instances
- [ ] Implement caching for frequently accessed schemas
- [ ] Monitor performance metrics and optimize as needed
- [ ] Consider using Redis for rate limiting 
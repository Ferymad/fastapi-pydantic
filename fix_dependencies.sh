#!/bin/bash
# Fix missing dependencies in production
# Run this script inside your container or deployment to fix dependency issues

echo "Installing missing dependencies..."
pip install --no-cache-dir nest_asyncio>=1.5.6

echo "Checking for other potential missing dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "Done! Try restarting your application now." 
FROM python:3.11-slim

# Metadata
LABEL maintainer="Harmony SASE QA Team 'Eden Fridman'"
LABEL version="1.1.0"
LABEL description="TestRail MCP server"

# Create non-root user
RUN useradd -m -u 1000 mcpuser

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Switch to non-root user
USER mcpuser

# Run the server
CMD ["python", "-m", "src.stdio"]
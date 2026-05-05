FROM python:3.14-slim

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash aicoreutils

WORKDIR /app

# Copy project files
COPY src/ src/
COPY pyproject.toml .

# Install aicoreutils from source with MCP server
RUN pip install --no-cache-dir -e .

# Verify MCP server can be imported
RUN python -c "from aicoreutils.mcp_server import server_loop; print('MCP server ready')"

# Switch to non-root user
USER aicoreutils

# MCP server on stdio
CMD ["python", "-m", "aicoreutils.mcp_server"]

FROM python:3.12-slim

WORKDIR /app

# Copy project files for Glama verification
COPY src/ src/
COPY pyproject.toml .

# Install aicoreutils from source with MCP server
RUN pip install --no-cache-dir -e .

# Verify MCP server can be imported
RUN python -c "from aicoreutils.mcp_server import server_loop; print('MCP server ready')"

# MCP server on stdio
CMD ["python", "-m", "aicoreutils.mcp_server"]

FROM python:3.12-slim

WORKDIR /app

# Install aicoreutils from PyPI
RUN pip install --no-cache-dir aicoreutils

# Verify installation
RUN python -c "import aicoreutils; print(f'aicoreutils v{aicoreutils.__version__}')"

# MCP server runs on stdio (no TCP port needed)
ENTRYPOINT ["python", "-m", "aicoreutils.mcp_server"]

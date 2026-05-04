# AI Agent 使用示例 / AI Agent Task Examples

## 文件探索 / File Exploration

```bash
# List directory with structured JSON
aicoreutils ls . --recursive --max-depth 2 --limit 50

# Read file contents
aicoreutils cat README.md

# Check file metadata
aicoreutils stat pyproject.toml

# Count lines in Python source
aicoreutils wc src/ --recursive

# Find large directories
aicoreutils du src/ --max-depth 2
```

## 文件操作 / File Operations

```bash
# Create directory (dry-run first)
aicoreutils mkdir build/logs --parents --dry-run
aicoreutils mkdir build/logs --parents

# Copy file with overwrite protection
aicoreutils cp config.json config.backup.json --dry-run
aicoreutils cp config.json config.backup.json --allow-overwrite

# Move/rename file
aicoreutils mv old_name.txt new_name.txt --dry-run
aicoreutils mv old_name.txt new_name.txt

# Touch/update timestamp
aicoreutils touch .timestamp
```

## 文本处理 / Text Processing

```bash
# Search: sort lines, deduplicate
echo -e "banana\napple\napple\ncherry" | aicoreutils sort
echo -e "banana\napple\napple\ncherry" | aicoreutils sort | aicoreutils uniq

# Extract columns from CSV-like data
echo "name,age,city" > data.txt
echo "Alice,30,NYC" >> data.txt
aicoreutils cut data.txt --delimiter , --fields 1,3

# Character translation
echo "HELLO WORLD" | aicoreutils tr --from "A-Z" --to "a-z"
```

## 安全检查 / Safety Operations

```bash
# Dry-run all destructive operations
aicoreutils rm old_data/ --recursive --dry-run
aicoreutils install script.sh /usr/local/bin/ --dry-run

# Verify before deletion
aicoreutils rm old_data/ --recursive

# Secure shred with confirmation
aicoreutils shred secret.key --allow-destructive

# Check disk before large operations
aicoreutils df
aicoreutils du downloads/ --limit 20
```

## 系统信息 / System Info

```bash
aicoreutils uname
aicoreutils arch
aicoreutils nproc
aicoreutils uptime
aicoreutils date

aicoreutils whoami
aicoreutils id
aicoreutils groups

aicoreutils env
aicoreutils printenv --name HOME
```

## 哈希与编码 / Hashing & Encoding

```bash
# SHA-256 integrity check
aicoreutils sha256sum dist/*.whl

# Base64 encode/decode
echo "hello world" | aicoreutils base64
echo "aGVsbG8gd29ybGQ=" | aicoreutils base64 --decode

# Flexible encoding via basenc
aicoreutils basenc README.md --base base64
aicoreutils basenc README.md --base base32
```

## 进程控制 / Process Control

```bash
# Run with timeout
aicoreutils timeout -- 5 -- python -c "import time; time.sleep(10)"

# Lower CPU priority for background task
aicoreutils nice -- 10 -- python heavy_script.py --dry-run

# Prevent hangup for long tasks
aicoreutils nohup -- python server.py --allow-nohup
```

## OpenAI Function Calling 格式

```bash
# Export all 114 tools as OpenAI-compatible function definitions
aicoreutils tool-list --format openai --pretty > openai-tools.json
```

## MCP Server 直接使用

```bash
# Start MCP JSON-RPC server on stdio
python -m aicoreutils.mcp_server
# Or: aicoreutils-mcp
```

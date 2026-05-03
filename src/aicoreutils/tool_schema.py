"""Tool schema generation for LLM function-calling.

Auto-generates parameter schemas from argparse subparser definitions.
Used by both the MCP server and the tool-list command.
"""

from __future__ import annotations

import argparse
from typing import Any

_TYPE_MAP: dict[type[Any] | None, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    None: "string",
}

_COMMAND_DESCRIPTIONS: dict[str, str] = {
    # ── Meta / Discovery ──────────────────────────────────────────────
    "catalog": "List prioritized GNU Coreutils categories for agents. Read-only. Use to discover available command groups before selecting a tool. Returns category names ordered by relevance. See also 'tool-list' for the full tool index and 'schema' for protocol documentation.",
    "schema": "Print the aicoreutils JSON protocol and exit code conventions. Read-only. Use to understand the JSON envelope structure, exit code semantics, and protocol version before invoking other tools. See also 'coreutils' for the command list and 'catalog' for categories by function.",
    "coreutils": "List all available commands as a flat index, or describe individual tools. Read-only. Use with 'list=true' to enumerate all tools, or by name to inspect a specific command. Returns short descriptions with each tool name. See also 'tool-list' for compact LLM context and 'catalog' for categorical grouping.",
    "tool-list": "Return a compact tool index optimized for LLM function-calling context. Read-only. Use to retrieve the current tool surface (names, descriptions, input schemas) for agent planning. Supports OpenAI function-calling format via --format=openai. See also 'coreutils' for human-readable listing and 'catalog' for categorization.",
    # ── Path / Directory Utilities ─────────────────────────────────────
    "pwd": "Print the current working directory as JSON. Read-only, no side effects. Use to determine the active directory context before running file operations. Returns the absolute path string. See also 'ls' for listing directory contents and 'realpath' for resolving paths.",
    "basename": "Return the final path component of file paths, stripping directory prefixes. Read-only. Use to extract filenames from full paths. Supports optional suffix removal. See also 'dirname' to extract parent directories and 'realpath' for full canonical resolution.",
    "dirname": "Return parent directory path components from file paths. Read-only. Use to extract the directory portion of a path, discarding the final component. See also 'basename' for the inverse operation and 'realpath' for canonical paths.",
    "realpath": "Resolve file paths to absolute canonical form, following all symlinks. Read-only, no side effects. Use to normalize paths for reliable comparison or to find the true location of a file. Use 'readlink' for reading a single symlink target without full resolution.",
    "readlink": "Read symbolic link targets or canonicalize paths (with --canonicalize). Read-only. Use to discover what a symlink points to, or to resolve the full path when canonicalization is needed. Use 'realpath' for always-resolved paths and 'ls -l' for seeing symlink metadata.",
    # ── File Testing ───────────────────────────────────────────────────
    "test": "Evaluate path predicates (file, is_dir, is_executable, etc.) and return structured JSON results. Read-only. Use to check file existence, type, or permissions in conditional scripts. Returns per-predicate boolean results. See also '[' (alias) for alternative syntax, and 'stat' for detailed file metadata.",
    "[": "Evaluate path predicates (alias for 'test'). Read-only. Use to check file existence, type, or permissions in conditional scripts. Returns per-predicate boolean results as JSON. See also 'test' for the primary interface and 'stat' for detailed file metadata.",
    # ── Directory Listing ──────────────────────────────────────────────
    "ls": "List directory contents as structured JSON. Read-only. Use to inspect files and subdirectories, with optional recursive traversal (--depth), streaming, and symlink following. Returns entries with name, type, size, and permissions. See also 'dir' for structured output and 'stat' for single-file metadata.",
    "dir": "List directory contents in a structured format. Read-only. Alias for 'ls' with an organized file listing layout. Use when you want a clean directory listing with column-aligned output. See also 'ls' for the primary interface and 'vdir' for verbose output with extended details.",
    "vdir": "List directory contents with verbose, detailed output. Read-only. Alias for 'ls' producing extended file information. Use when you need all available metadata for each entry. See also 'ls' for the primary interface and 'dir' for standard structured output.",
    "stat": "Return file metadata (size, permissions, timestamps, owner, etc.) as structured JSON. Read-only. Use to inspect detailed file attributes without reading file contents. Supports multiple paths. See also 'ls' for directory listing and 'du' for disk usage estimation.",
    # ── File Reading ──────────────────────────────────────────────────
    "cat": "Read file contents and return bounded JSON output by default. Read-only. Limits output size to prevent context overflow; use --raw for full plain text. Supports byte-offset and length parameters to read partial files. Returns truncated JSON when output exceeds bounds. See also 'head' for first lines, 'tail' for last lines, and 'od' for binary dumps.",
    "head": "Return the first N lines (default 10) of files as JSON. Read-only. Use to preview the beginning of a file or inspect headers. Supports multiple paths. Returns JSON with line arrays by default, or raw text with --raw. See also 'tail' for last lines and 'cat' for full file contents.",
    "tail": "Return the last N lines (default 10) of files as JSON. Read-only. Use to preview file endings, check recent log entries, or verify output. Returns JSON with line arrays by default, or raw text with --raw. See also 'head' for first lines and 'cat' for full file contents.",
    # ── File Statistics ────────────────────────────────────────────────
    "wc": "Count bytes, characters, lines, and words in files, returning results as JSON. Read-only. Use to measure file size, line count, or word frequency. Returns per-file counts plus a total. See also 'stat' for file metadata and 'du' for disk space usage.",
    # ── Hashing / Checksums ─────────────────────────────────────────────
    "md5sum": "Compute MD5 hash of files as JSON. Read-only. Use for fast non-cryptographic integrity checks or legacy compatibility. Not suitable for security-critical applications — use 'sha256sum' or 'b2sum' for cryptographic verification. Returns per-file hash values.",
    "sha1sum": "Compute SHA-1 hash of files as JSON. Read-only. Use for basic integrity verification or legacy compatibility. Not recommended for new security-critical applications — prefer 'sha256sum' or 'b2sum'. Returns per-file hash values.",
    "sha224sum": "Compute SHA-224 hash of files as JSON. Read-only. Use for cryptographic integrity verification with shorter output. Not as widely supported as SHA-256. Returns per-file hash values. See also 'hash' for multi-algorithm support.",
    "sha256sum": "Compute SHA-256 hash of files as JSON. Read-only. Use for cryptographic integrity verification and digital signatures. Standard choice for most security applications. Returns per-file hash values. See also 'hash' for multi-algorithm support.",
    "sha384sum": "Compute SHA-384 hash of files as JSON. Read-only. Use for cryptographic integrity verification with higher security margin than SHA-256. Returns per-file hash values. See also 'hash' for multi-algorithm support.",
    "sha512sum": "Compute SHA-512 hash of files as JSON. Read-only. Use for cryptographic integrity verification requiring the highest security margin. Returns per-file hash values. See also 'hash' for multi-algorithm support.",
    "b2sum": "Compute BLAKE2b hash of files as JSON. Read-only. Use for high-speed cryptographic hashing; BLAKE2b is faster than SHA-2/3 on many platforms. Returns per-file hash values. See also 'hash' for multi-algorithm support.",
    "hash": "Compute hash of files with selectable algorithm (md5, sha1, sha256, sha384, sha512, blake2b) as JSON. Read-only. Use when you need flexible algorithm choice via a single tool. Returns per-file hash values. See also individual hash tools (md5sum, sha256sum, etc.) for dedicated single-algorithm interfaces.",
    "cksum": "Return CRC32 checksums for files or stdin. Read-only. Use for fast non-cryptographic checksum verification (e.g., data transmission integrity). Not for security verification — use 'sha256sum' or 'b2sum' for cryptographic hashes. Returns checksum and byte count per file.",
    "sum": "Return simple 16-bit byte sums for files or stdin. Read-only. Use for legacy BSD-style checksum verification or quick file identity checks. Not for data integrity — prefer 'cksum' for CRC32 or 'sha256sum' for cryptographic verification. Returns sum and block count per file.",
    # ── Text Processing (Line-Based) ────────────────────────────────────
    "sort": "Sort text lines from files or stdin deterministically. Read-only. Use to order lines alphabetically, numerically (--numeric), or in reverse (--reverse). Supports stable sorting — equal lines maintain input order. Requires reading all input into memory. See also 'uniq' for deduplication and 'shuf' for randomization.",
    "comm": "Compare two sorted files line-by-line and return column-tagged records showing lines unique to each file and lines common to both. Read-only. Requires both input files to be pre-sorted (use 'sort' first). Use for finding differences or intersections between two datasets. See also 'join' for field-based merging and 'diff' for detailed comparison.",
    "join": "Join two sorted files on a selected field (default: first whitespace-separated field). Read-only. Requires both inputs to be pre-sorted by the join field. Performs an inner join by default. Use to combine related data from two sources by a common key. See also 'paste' for side-by-side merging without key matching.",
    "paste": "Merge corresponding lines from multiple files side-by-side with a configurable delimiter. Read-only. Use to combine columns from separate files into a single table. Supports custom delimiters (default: tab). See also 'join' for key-based merging and 'cat' for vertical concatenation.",
    "shuf": "Shuffle input lines randomly, with optional deterministic seed for reproducible results. Read-only. Use to randomize line order for testing, sampling, or fair ordering. Set a seed to reproduce the same order. See also 'sort' for ordered output and 'uniq' for deduplication.",
    "tac": "Reverse input lines from files or stdin (last line first). Read-only. Use to invert line order of a file. Reads stdin if no paths are given. Returns JSON with reversed lines by default, or raw text with --raw. See also 'tail -r' for similar behavior and 'sort -r' for reverse-sorted output.",
    "nl": "Number input lines with configurable formatting (a deterministic subset of GNU nl). Read-only. Use to add line numbers to text files. Supports custom number format, starting number, and increment. Returns JSON by default, or raw text with --raw. See also 'cat -n' for simple line numbering.",
    # ── Text Formatting ─────────────────────────────────────────────────
    "fold": "Wrap long input lines to a fixed character width. Read-only. Use to constrain line length for display or formatting requirements. Handles tabs and wide characters. Not for paragraph reflowing — use 'fmt' to intelligently rewrap paragraphs. Returns JSON by default, or raw text with --raw.",
    "fmt": "Reflow paragraphs to a fixed character width, preserving paragraph structure. Read-only. Use to reformat text to a consistent width while maintaining paragraph boundaries. Reads from stdin if no paths given. Returns JSON by default, or raw text with --raw. See also 'fold' for hard line wrapping without paragraph awareness.",
    "csplit": "Split input into multiple files at regex match points, with dry-run and overwrite protection. Destructive (creates files). Use to divide a file into chunks based on content patterns. Supports regex patterns for split points. Returns JSON describing created files. Use --dry_run to preview splits before execution. See also 'split' for size-based splitting.",
    "split": "Split input into chunked files by line count or size, with dry-run and overwrite protection. Destructive (creates output files). Default: 1000 lines per chunk with prefix 'x'. Use to divide large files into manageable pieces. Supports line-count, byte-size, and chunk-number modes. Use --dry_run to preview. See also 'csplit' for regex-based splitting.",
    "od": "Dump input bytes as structured rows (hex, octal, or decimal formats). Read-only. Use to inspect raw binary content of files or stdin. Supports configurable output format and grouping. Returns JSON with byte arrays by default, or raw dump with --raw. See also 'cat' for text content and 'xxd' for hex dumps.",
    "numfmt": "Convert numbers between plain, SI (K, M, G), and IEC (Ki, Mi, Gi) unit systems. Read-only. Use to humanize raw byte counts or parse human-readable sizes back to numbers. Supports configurable precision, unit scaling, and padding. Returns JSON by default, or raw text with --raw. See also 'seq' for number generation and 'printf' for formatted output.",
    "tsort": "Topologically sort whitespace-separated dependency pairs. Read-only. Use for dependency resolution — given pairs of items where the first must precede the second, returns a valid ordering. Detects cycles and reports errors. Returns JSON-sorted list by default, or raw text with --raw. See also 'sort' for lexical ordering.",
    "pr": "Paginate text into deterministic pages with headers and footers. Read-only. Use to format text for printing or paginated display. Supports page length, width, column layout, and custom headers. Returns JSON by default, or raw text with --raw. See also 'fmt' for paragraph reformatting and 'fold' for line wrapping.",
    "ptx": "Build a permuted (keyword-in-context) index from input text. Read-only. Reads files or stdin and produces a concordance showing each word in its surrounding context. Use to create searchable cross-references of terms in a document. Not for plain text indexing without permutation. Returns JSON by default, or raw text with --raw.",
    # ── Text Filters ───────────────────────────────────────────────────
    "uniq": "Collapse adjacent duplicate lines from files or stdin, optionally counting occurrences. Read-only. Use to remove consecutive duplicate lines. Does NOT sort — input must already be grouped. Pipe through 'sort' first if you need to deduplicate a full file. Returns JSON by default, or raw text with --raw.",
    "cut": "Select specific fields, characters, or bytes from each input line. Read-only. Use to extract columns from tabular data (default delimiter: tab) or fixed-position substrings. Supports field ranges and multiple field selection. See also 'paste' for combining columns and 'tr' for character-level operations.",
    "tr": "Translate or delete literal characters from files or stdin. Read-only. Use for character substitution, case conversion, or deletion. Does NOT support regex — operates on individual characters. Returns JSON by default, or raw text with --raw. See also 'sed' for regex-based substitution.",
    "expand": "Convert tabs to spaces in files or stdin with configurable tab width. Read-only. Use to normalize indentation from tabs to spaces for consistent display. Returns JSON by default, or raw text with --raw. See also 'unexpand' for the reverse operation (spaces to tabs).",
    "unexpand": "Convert spaces to tabs in files or stdin with configurable tab width. Read-only. Use to compress leading spaces into tabs for more compact storage. Returns JSON by default, or raw text with --raw. See also 'expand' for the reverse operation (tabs to spaces).",
    # ── Encoding ───────────────────────────────────────────────────────
    "base64": "Encode or decode base64 data from files or stdin. Read-only. Use for base64 encoding/decoding of binary data for transmission over text protocols. Supports decode mode via --decode. Returns JSON by default, or raw text with --raw. See also 'base32' and 'basenc' for other encoding schemes.",
    "base32": "Encode or decode base32 data from files or stdin. Read-only. Use for base32 encoding/decoding (human-friendly compared to base64). Supports decode mode via --decode. Returns JSON by default, or raw text with --raw. See also 'base64' and 'basenc' for other encoding schemes.",
    "basenc": "Encode or decode data in base16, base32, base64, or base64url formats from files or stdin. Read-only. Use when you need multiple encoding formats via a single tool with --encoding parameter. Returns JSON by default, or raw text with --raw. See also dedicated 'base64' and 'base32' tools for simpler single-format usage.",
    # ── System Information ─────────────────────────────────────────────
    "date": "Return current or supplied time as structured JSON with year, month, day, hour, minute, second, and timezone fields. Read-only. Use to query system time or parse date strings. Supports custom time input. See also 'uptime' for system uptime duration and 'sleep' for pausing execution.",
    "env": "Return environment variables as structured JSON (key-value object). Read-only. Use to inspect available environment variables in the agent's execution context. Supports filtering by variable name. See also 'printenv' for selected variable output and 'echo' for custom output.",
    "printenv": "Return selected environment variables by name. Read-only. Use to query specific environment variable values without the full env listing. Returns values as JSON by default. Not for listing all variables — use 'env' for the complete environment dump.",
    "whoami": "Return the current user identity (username, UID, GID) as JSON. Read-only. Use to determine the effective user running the current process. Returns structured identity data by default, or plain username with --raw. See also 'id' for full user/group info and 'logname' for login name only.",
    "groups": "Return group IDs and names for the current user (or a specified user). Read-only. Use to determine which groups a user belongs to. Returns group information where the platform exposes it. See also 'id' for full user identity and 'whoami' for current username.",
    "id": "Return user ID, group ID, and group membership as JSON. Read-only. Use for comprehensive user identity inspection. Returns numeric IDs and names. See also 'whoami' for username only and 'groups' for group membership listing.",
    "uname": "Return system information (kernel name, hostname, release, version, machine architecture) as structured JSON. Read-only. Use for cross-platform system identification. Returns multi-field JSON by default, or uname-like raw text with --raw. See also 'arch' for architecture only and 'hostname' for hostname only.",
    "arch": "Return the machine architecture (e.g., x86_64, aarch64). Read-only. Use to detect CPU architecture for platform-conditional operations. Returns a plain string. See also 'uname' for comprehensive system information including architecture.",
    "hostname": "Return the system hostname. Read-only. Use to identify the current machine in network contexts. Returns the hostname string as JSON by default, or plain text with --raw. See also 'hostid' for a deterministic hex identifier and 'uname' for full system info.",
    "hostid": "Return a deterministic host identifier in hexadecimal format. Read-only. Use for stable, reproducible machine identification (e.g., license key generation). Returns a hex string. See also 'hostname' for the human-readable name and 'uname' for full system info.",
    "logname": "Return the current user's login name. Read-only. Use to get the original login name (unaffected by 'su' or 'sudo'). Returns the login name string as JSON by default, or plain text with --raw. See also 'whoami' for effective user and 'id' for full identity.",
    "uptime": "Return system uptime in seconds. Read-only. Use to check how long the system has been running. Returns seconds as JSON by default, or plain integer with --raw (e.g., for calculations). See also 'date' for current timestamp and 'nproc' for CPU information.",
    "tty": "Check if stdin is a terminal (TTY) and report the terminal device name. Read-only. Use to determine whether the running context has an interactive terminal. Returns JSON with is_tty boolean and terminal name, or the terminal path with --raw. Returns non-zero exit code if not a TTY.",
    "users": "List currently logged-in users (deduplicated usernames). Read-only. Use to quickly check who is logged into the system. Returns a space-separated list of usernames as JSON. Not for detailed session info — see 'who' for session details and 'pinky' for per-user account info.",
    "pinky": "Print detailed user account information (login name, home directory, shell, full name). Read-only. Use for inspecting specific user profiles by name. Returns structured user records as JSON. Not for listing logged-in users — use 'users' or 'who' instead. See also 'id' for current user identity and 'whoami' for own username.",
    "who": "Return logged-in user sessions with terminal, login time, and remote host details. Read-only. Use to see active sessions and where users are connecting from. Returns session records as JSON. See also 'users' for a simple username list and 'pinky' for detailed per-user records.",
    "nproc": "Return the number of available CPU cores. Read-only. Use for determining parallelism (e.g., setting worker counts). Returns a JSON object with the count by default, or plain integer with --raw. See also 'uptime' for system load context and 'arch' for CPU architecture.",
    # ── Disk / Filesystem ──────────────────────────────────────────────
    "df": "Return disk space usage for filesystems as JSON (total, used, available, percentage). Read-only. Use to check free disk space across mounted filesystems. Supports filtering by specific filesystem paths. See also 'du' for per-directory usage and 'stat' for single-file metadata.",
    "du": "Estimate file and directory space usage as JSON. Read-only. Use to find which directories consume the most disk space. Supports configurable depth and unit display. Not for filesystem-level overview — use 'df' for filesystem free space. See also 'stat' for single-file metadata.",
    "dd": "Copy and convert input to output with bounded preview and dry-run support. Destructive to output files. Use for block-level data copying and format conversion. Supports input/output file selection, block size, count, and byte skipping. Use --dry_run to preview before executing. Use --max_preview_bytes to limit output.",
    "sync": "Flush cached writes to disk. Read-only operation that may affect I/O performance. Use to ensure all pending filesystem writes are committed to storage before a critical operation. Where supported by the platform. Use --dry_run to report without actually syncing.",
    "dircolors": "Return LS_COLORS configuration as JSON. Read-only. Color output is disabled by default for agent-friendly output. Use to inspect or generate shell color configuration for 'ls'. Returns JSON with color mappings, or shell eval format with --shell.",
    # ── Number / Expression Tools ──────────────────────────────────────
    "seq": "Print a sequence of numbers as JSON. Read-only. Use to generate numeric ranges for iteration or data generation. Accepts [FIRST [INCREMENT]] LAST format via the 'number' parameter. Supports printf-style formatting. Returns number array as JSON by default, or raw text with --raw. See also 'yes' for string repetition and 'printf' for formatted output.",
    "printf": "Format and print text with printf-style conversion specifiers (%s, %d, %f, etc.). Read-only. Use for precise formatting of strings, numbers, and other data types. Returns formatted output as JSON by default, or raw text with --raw. See also 'echo' for simple output and 'seq' for number sequences.",
    "echo": "Echo input text as JSON. Read-only. Use to output text or variable values to stdout. Supports escape character interpretation. Returns text wrapped in JSON by default, or raw text with --raw. Not for formatted output — use 'printf' for format control. See also 'printf' for formatted output and 'cat' for file content.",
    "pathchk": "Validate path name components for portability and correctness. Read-only. Use to verify that path names are valid and portable across platforms. Returns JSON validation results with error details. Supports checking path length limits and component validity. See also 'realpath' for path resolution and 'test' for existence checks.",
    "factor": "Compute the prime factors of given integers. Read-only. Use to decompose numbers into their prime factors. Accepts integer input and returns factor arrays as JSON. Not for general arithmetic — use 'expr' for arithmetic expressions. Supports configurable max_value to prevent excessive computation.",
    "expr": "Evaluate arithmetic and comparison expressions in a safe AST subset. Read-only. Use for numeric computation and string comparisons in scripts. Supports +, -, *, /, %, comparisons, and string operations. Not for executing arbitrary code — limited to a deterministic safe subset. Returns results as JSON.",
    # ── Control Flow ───────────────────────────────────────────────────
    "true": "Exit with status 0, indicating success. No side effects. Does nothing else. Takes no arguments. Always returns the same result (idempotent). Use to signal successful completion in scripts or pipelines. See also 'false' for the failure counterpart.",
    "false": "Exit with status 1, indicating failure. No side effects. Does nothing else. Takes no arguments. Always returns the same result (idempotent). Use to signal error conditions in scripts or to test error-handling logic. See also 'true' for the success counterpart.",
    # ── Process Execution / Control ────────────────────────────────────
    "sleep": "Pause execution for a specified number of seconds. Read-only operation that blocks. Use to introduce delays between operations or to throttle execution. Bounded by max_seconds for safety. Use --dry_run to preview the duration without actually sleeping. Not for timing — see 'date' for timestamps and 'timeout' for command execution with a time limit.",
    "timeout": "Run a command with a bounded time limit, capturing its output. May terminate child processes. Use to prevent runaway commands from blocking indefinitely. Captures stdout/stderr and returns them as JSON, including exit code and whether the command timed out. See also 'sleep' for simple delays.",
    "stdbuf": "Run a command with controlled stdout and stderr buffering modes (0=none, L=line, or byte size). Executes the given command. Use to debug buffering issues by forcing unbuffered or line-buffered output. See also 'timeout' for time-limited execution.",
    "chroot": "Plan or run a command inside a changed root directory. Potentially destructive and typically requires elevated privileges. Use --dry_run to preview the operation. Requires explicit --allow_chroot confirmation for actual execution. Not for casual file operations — use only when filesystem isolation is required.",
    "stty": "Inspect or modify terminal settings. Can change terminal behavior if --allow_change is enabled. Use to query current terminal configuration (baud rate, line discipline, etc.). Potentially destructive when changing settings — use --dry_run to preview. Not for simple TTY detection — use 'tty' for that.",
    "nice": "Run a command with a niceness adjustment (process priority) where supported by the platform. Executes the given command. Use to lower the priority of background tasks or raise priority for critical work. See also 'stdbuf' for buffering control and 'timeout' for time-limited execution.",
    "kill": "Plan or send a signal to a process. Potentially destructive — can terminate processes. Use --dry_run to preview. Requires --allow_signal for actual signal delivery. Use to stop or signal processes by PID. Not for process monitoring — see 'ps' style tools for process listing.",
    "nohup": "Run a command immune to hangups (SIGHUP), with explicit confirmation. Executes the given command. Use for long-running background tasks that should persist after the parent session ends. Requires --allow_nohup confirmation. See also 'timeout' for time-limited execution.",
    "chcon": "Plan or apply an SELinux security context change to files. Potentially destructive to file security labels. Use --dry_run to preview. Requires --allow_context confirmation for actual changes. Not for general file permissions — use 'chmod' instead. See also 'runcon' for running commands under contexts.",
    "runcon": "Plan or run a command under an SELinux security context. Requires explicit confirmation. Use to execute commands with specific SELinux labels. Use --dry_run to preview the plan. Requires --allow_context for actual execution. See also 'chcon' for file context changes.",
    "yes": "Repeatedly print a given string (default 'y') to stdout. Read-only. Bounded by the 'count' parameter to prevent infinite output. Use to auto-answer prompts with 'y' in scripts or to generate repetitive test data. Not for single-line output — use 'echo' or 'printf' instead. See also 'seq' for number sequences.",
    # ── File / Directory Creation ──────────────────────────────────────
    "mkdir": "Create directories with dry-run and parent directory creation support. Destructive (creates directories). Use to create new directories, optionally creating all intermediate parent directories. Returns JSON with created paths. Use --dry_run to preview. See also 'rmdir' for removing empty directories and 'touch' for creating empty files.",
    "touch": "Update file timestamps or create empty files. Destructive (modifies timestamps, creates files if absent). Use to update a file's access and modification times or to create placeholder files. Does not modify file contents for existing files. See also 'mkdir' for directory creation and 'truncate' for file size control.",
    "cp": "Copy files and directories with dry-run and overwrite protection. Destructive to destination paths. Use to duplicate files or directory trees. Supports recursive copying. Overwrite is disabled by default for safety. Use --dry_run to preview before executing. See also 'mv' for move/rename and 'install' for copy with attribute setting.",
    "mv": "Move or rename files and directories with dry-run and overwrite protection. Destructive (moves/renames files). Use to relocate or rename files and directories. Overwrite is disabled by default. Use --dry_run to preview before executing. See also 'cp' for copy operations and 'ln' for creating links.",
    "ln": "Create hard or symbolic links with dry-run and overwrite protection. Destructive (creates filesystem links). Use to create file references without duplicating data. Use --symbolic for symlinks (supports cross-filesystem) or default for hard links (must be on same filesystem). Overwrite is disabled by default. See also 'link' for hard links and 'cp' for copying.",
    "link": "Create hard links with dry-run and overwrite protection. Destructive (creates filesystem links). Use to create additional directory entries referencing the same file data. Hard links cannot span filesystems. Overwrite is disabled by default. See also 'ln' for both hard and symbolic links.",
    # ── File Permission / Ownership ─────────────────────────────────────
    "chmod": "Change file permissions (octal modes only, e.g., 755). Destructive to file permissions. Use to set read/write/execute permissions on files and directories. Only accepts octal mode values. Use --dry_run to preview. See also 'chown' for ownership and 'chgrp' for group ownership changes.",
    "chown": "Change file ownership (user and/or group). Destructive and typically requires elevated privileges. Use to transfer file ownership between users. Supports changing owner, group, or both. Use --dry_run to preview. See also 'chgrp' for group-only changes and 'chmod' for permission changes.",
    "chgrp": "Change file group ownership. Destructive to file group assignment. Use to change which group a file belongs to. Use --dry_run to preview. See also 'chown' for full ownership changes (user+group) and 'chmod' for permission changes.",
    # ── File Size / Content Manipulation ───────────────────────────────
    "truncate": "Shrink or extend file sizes to a specified length. Destructive (modifies file contents). Use to resize files by truncating or extending. Extending fills with null bytes. Overwrite protection is enabled by default. Use --dry_run to preview. See also 'touch' for timestamp-only updates and 'dd' for block-level operations.",
    "mktemp": "Create temporary files or directories safely with unique, random names. Destructive (creates temporary files/dirs). Use to generate unique temporary file or directory names for scratch data. Creates the file/dir atomically to prevent race conditions. Returns the path as JSON. See also 'mkdir' for permanent directories and 'touch' for empty files.",
    "mkfifo": "Create named pipes (FIFOs) with dry-run support. Destructive (creates special files). Use to create inter-process communication channels via FIFO special files. Returns JSON with created path. Use --dry_run to preview. See also 'mknod' for other device nodes.",
    "mknod": "Create device nodes (block or character special files) with dry-run support. Destructive (creates device files). Typically requires elevated privileges. Use to create special device files for kernel driver access. Use --dry_run to preview. See also 'mkfifo' for named pipe creation.",
    "install": "Copy files and set attributes (permissions, ownership) in one operation, with dry-run support. Destructive to destination. Use for software install scripts that need to copy files with specific permissions and ownership. See also 'cp' for simple copying and 'ginstall' (alias).",
    "ginstall": "Copy files and set attributes (alias for 'install'). Destructive to destination. See also 'install' for the primary interface.",
    # ── Output Tee ─────────────────────────────────────────────────────
    "tee": "Read stdin and write to files and stdout simultaneously, with dry-run support. Destructive (writes to files). Use to capture command output while also passing it through to stdout (or another command). Supports append mode. Use --dry_run to preview. See also 'cat' for pure output and 'echo' for direct output.",
    # ── File / Directory Removal ───────────────────────────────────────
    "rmdir": "Remove empty directories only, with dry-run support. Destructive. Fails if directory is not empty (use 'rm' for non-empty directories). Use to remove directories you know are empty. Use --dry_run to preview. See also 'rm' for recursive removal and 'unlink' for single file removal.",
    "unlink": "Remove a single file (not directories), with dry-run support. Destructive and irreversible. Use to remove individual files. Fails on directories — use 'rmdir' for empty directories. Use --dry_run to preview. See also 'rm' for broader removal and 'rmdir' for directories.",
    "rm": "Remove files and directories with dry-run support. Destructive and irreversible. Use to delete files or recursively delete directory trees. Use --dry_run to preview. Not for secure deletion — use 'shred' to overwrite before removal. See also 'rmdir' for empty directories and 'unlink' for single files.",
    "shred": "Overwrite file contents with random data and then remove the file, with explicit confirmation required. Destructive and irreversible — makes data unrecoverable. Use for secure deletion of sensitive files. Use --dry_run to preview without executing. Requires --allow_destructive to actually execute. See also 'rm' for standard non-secure deletion.",
}


def _arg_to_schema(action: argparse.Action) -> dict[str, Any]:
    """Convert an argparse action to a JSON Schema property."""
    schema: dict[str, Any] = {"description": action.help or ""}
    if action.choices is not None:
        schema["type"] = "string"
        schema["enum"] = list(action.choices)
    elif action.type in _TYPE_MAP:
        schema["type"] = _TYPE_MAP[action.type]
    else:
        schema["type"] = "string"
    if action.default is not None and action.default is not argparse.SUPPRESS:
        schema["default"] = action.default
    return schema


def _command_tools(parser: argparse.ArgumentParser) -> list[dict[str, Any]]:
    """Generate MCP-compatible tool list from all registered subcommands."""
    subparsers_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            subparsers_action = action
            break
    if subparsers_action is None:
        return []

    tools: list[dict[str, Any]] = []
    for name, subparser in sorted(subparsers_action.choices.items()):
        properties: dict[str, Any] = {}
        required: list[str] = []

        for action in subparser._actions:
            dest = action.dest
            if dest in ("help", "pretty", "command") or dest == argparse.SUPPRESS:
                continue
            prop_schema = _arg_to_schema(action)
            if action.option_strings is None or len(action.option_strings) == 0:
                if action.nargs in ("*", "+", "?"):
                    prop_schema["type"] = "array"
                    prop_schema["items"] = {"type": "string"}
                if action.required:
                    required.append(dest)
                properties[dest] = prop_schema
            else:
                if action.nargs == 0 and action.const is not None:
                    prop_schema["type"] = "boolean"
                properties[dest] = prop_schema

        description = _COMMAND_DESCRIPTIONS.get(name, subparser.description or "")

        tools.append(
            {
                "name": name,
                "description": description,
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        )

    return tools


def tools_openai(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert tool schemas to OpenAI function-calling format."""
    result: list[dict[str, Any]] = []
    for tool in tools:
        result.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["inputSchema"],
                },
            }
        )
    return result


def tools_anthropic(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert tool schemas to Anthropic tool-use format."""
    result: list[dict[str, Any]] = []
    for tool in tools:
        result.append(
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["inputSchema"],
            }
        )
    return result

"""Tool schema generation for LLM function-calling.

Auto-generates parameter schemas from argparse subparser definitions.
Used by both the MCP server and the tool-list command.

All descriptions follow the best-practices template derived from:
- 2602.14878v2: "MCP Tool Descriptions Are Smelly" (6-component rubric)
- 2602.18914v1: "From Docs to Descriptions" (4-dimension standard)
- Glama TDQS: Purpose(25%) + Usage(20%) + Behavior(20%) + Parameters(15%)
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
    "[": "Evaluate path predicates (file existence, type, permissions) — alias for 'test'. Read-only, no side effects. Returns JSON with predicate result and success/failure exit code. Use in scripts for conditional file checks. Not for detailed file inspection — use 'stat' for full metadata. See also 'test', 'stat'.",
    "arch": "Return the machine architecture string (e.g., x86_64, aarch64). Read-only, no side effects. Returns JSON with the architecture name. Use for platform-conditional logic in agent workflows. Not for full system information — use 'uname' for kernel, hostname, and OS details. See also 'uname'.",
    "b2sum": "Compute BLAKE2b cryptographic hash of files or stdin as JSON. Read-only, no side effects. Returns per-file hash digests and byte counts. Use for high-speed integrity verification — faster than SHA-2/3 on 64-bit platforms. Not for security-critical contexts where SHA-256 is mandated — use 'sha256sum'. See also 'hash', 'sha256sum'.",
    "base32": "Encode or decode base32 data from files or stdin. Read-only, no side effects. Returns JSON with the result by default; use --raw for raw output on stdout. Use for human-friendly encoding (avoids ambiguous characters). Not for compact encoding — use 'base64' for smaller output size. See also 'base64', 'basenc'.",
    "base64": "Encode or decode base64 data from files or stdin. Read-only, no side effects. Returns JSON with the result by default; use --raw for raw output on stdout. Use for standard base64 encoding in data transfer and storage. Not for flexible multi-base handling — use 'basenc' to switch between base16/32/64/64url. See also 'base32', 'basenc'.",
    "basename": "Return the final path component, stripping all directory prefixes. Read-only, no side effects. Returns JSON with the stripped filename. Use to extract filenames from full paths. Not for extracting directory portions — use 'dirname' for the inverse operation. See also 'dirname', 'realpath'.",
    "basenc": "Encode or decode data in base16 (hex), base32, base64, or base64url from files or stdin. Read-only, no side effects. Returns JSON with encoded/decoded data by default; use --raw for raw bytes on stdout. Select format with --base (default base64), switch to decode mode with --decode. Use --max_output_bytes to bound output size. Use when you need flexible base selection via a single tool. Not for fixed-format needs — use 'base64' or 'base32' for dedicated encoding. See also 'base64', 'base32'.",
    "cat": "Read and output file contents. Read-only, no side effects. Returns JSON by default with bounded content; use --raw for full plain-text output. Supports byte-offset and length for partial reads. Use to inspect file contents in agent workflows. Not for binary inspection — use 'od' for hex/octal dumps. See also 'head', 'tail', 'od'.",
    "catalog": "List all commands organized by GNU Coreutils priority categories. Read-only, no side effects. Returns JSON with commands grouped by priority (P0=essential, P1=common, P2=useful, P3=specialized). Use to discover the full command surface by functional area. Not for LLM function-calling context — use 'tool-list' for machine-optimized output. See also 'tool-list', 'coreutils'.",
    "chcon": "Plan or apply an SELinux security context to files. Destructive: may alter file security labels, affecting access control. Use --dry_run to preview without changes. Requires --allow_context for actual execution; fails safely otherwise. Use to manage SELinux contexts on labeled filesystems. Not for general permission changes — use 'chmod'. See also 'runcon', 'chmod'.",
    "chgrp": "Change file group ownership with dry-run support. Destructive: modifies filesystem group metadata. Use --dry_run to preview changes safely. Returns JSON with operation result. Use to reassign group ownership of files. Not for changing user ownership — use 'chown'. Not for permission changes — use 'chmod'. See also 'chown', 'chmod'.",
    "chmod": "Change file permissions using octal modes (e.g., 644, 755). Destructive: modifies filesystem permission bits. Use --dry_run to preview without changing. Returns JSON with old and new mode values. Use to control read/write/execute access. Not for ownership changes — use 'chown' or 'chgrp'. See also 'chown', 'chgrp'.",
    "chown": "Change file user ownership with dry-run support. Destructive: modifies filesystem ownership metadata. May require elevated privileges. Use --dry_run to preview. Returns JSON with operation result. Use to transfer file ownership between users. Not for group-only changes — use 'chgrp'. Not for permission changes — use 'chmod'. See also 'chgrp', 'chmod'.",
    "chroot": "Plan or run a command inside a changed root directory. Destructive: isolates command execution to a new filesystem root. May require elevated privileges. Use --dry_run to preview. Requires --allow_chroot for execution; fails safely otherwise. Use to test software in isolated environments. Not for simple directory changes — use 'cd' or path arguments on other commands. See also 'runcon'.",
    "cksum": "Compute CRC32 checksums and byte counts for files or stdin. Read-only, no side effects. Returns JSON with checksum and byte count per file. Use for fast data-transmission integrity verification. Not for cryptographic security — use 'sha256sum' or 'b2sum'. See also 'sha256sum', 'md5sum', 'sum'.",
    "comm": "Compare two sorted files line by line, returning column-tagged records (unique to file1, unique to file2, common). Read-only, no side effects. Requires pre-sorted input — use 'sort' first. Returns JSON with structured comparison results. Use to find differences and overlaps between datasets. Not for unsorted data — results are wrong without prior sorting. See also 'join', 'uniq', 'sort'.",
    "coreutils": "List all available commands as a flat text index. Read-only, no side effects. Use --list to enumerate tool names, --raw for plain text without JSON envelope. Use for quick overview of installed commands. Not for LLM tool discovery — use 'tool-list' for structured function-calling metadata. See also 'catalog', 'tool-list'.",
    "cp": "Copy files and directories with dry-run and overwrite protection. Destructive to destination: creates new copies on the filesystem. Overwrite protection enabled by default — use --allow_overwrite to replace existing files. Use --dry_run to preview the operation safely. Returns JSON with source and destination paths. Use to duplicate files or directories. Not for moving files — use 'mv' to relocate without copying. Not for setting permissions on copy — use 'install'. See also 'mv', 'install'.",
    "csplit": "Split input into multiple files at regex match points with dry-run and overwrite protection. Destructive: creates output files on the filesystem. Use --dry_run to preview split points without creating files. Returns JSON with generated filenames and record counts. Use to partition data by content patterns. Not for fixed-size splitting — use 'split' for line-count or byte-size chunks. See also 'split'.",
    "cut": "Select specific fields, characters, or bytes from each input line. Read-only, no side effects. Returns JSON with the extracted columns by default; use --raw for plain text. Use to extract columns from tabular or delimited data. Not for replacing characters — use 'tr' for translation/deletion. Not for merging columns — use 'paste'. See also 'paste', 'tr'.",
    "date": "Return current system time or parse a supplied date string as structured JSON. Read-only, no side effects. Returns JSON with ISO 8601 timestamp and timezone-aware fields. Use to query the system clock or validate date strings in agent workflows. Not for measuring elapsed time — use 'uptime' for system runtime or combine 'date' with arithmetic. See also 'uptime'.",
    "dd": "Copy and convert data blocks between input and output with bounded preview and dry-run support. Destructive to output: writes data to the destination file. Use --dry_run to preview the operation. Returns JSON with bytes read/written and throughput. Use for block-level data copying and format conversion. Not for simple file copying — use 'cp' for files and directories. See also 'cp', 'truncate'.",
    "df": "Return disk space usage for mounted filesystems as JSON. Read-only, no side effects. Returns JSON with total, used, available, and usage percentage per filesystem. Use to check free space and monitor storage across mount points. Not for per-directory usage — use 'du' for directory-level detail. See also 'du'.",
    "dir": "List directory contents in column-aligned format — alias for 'ls' producing structured JSON. Read-only, no side effects. Supports recursive depth, hidden files, symlink following, streaming (NDJSON), and result limiting. Returns per-entry metadata: type, size, permissions, modification time. Use for clean tabular directory listings. Prefer 'dir' over 'ls' when column-aligned output is desired; prefer 'ls' for default list format. Not for extended metadata — use 'vdir' for verbose output or 'stat' for single-file detail. See also 'ls', 'vdir', 'stat'.",
    "dircolors": "Return LS_COLORS configuration mapping file types to ANSI color codes. Read-only, no side effects. Returns JSON with the color mapping; color output disabled by default for agent-friendly display. Use to inspect how the shell colors file listings. Not for actual directory listing — use 'ls' or 'dir'. See also 'ls'.",
    "dirname": "Return the parent directory portion of file paths, stripping the final component. Read-only, no side effects. Returns JSON with the directory path. Use to extract directory prefixes from full paths. Not for extracting the filename — use 'basename' for the final component. See also 'basename', 'realpath'.",
    "du": "Estimate file and directory space usage recursively as JSON. Read-only, no side effects (stat-only, does not write). Returns JSON with per-directory byte counts. Use to find space-consuming directories and files. Not for filesystem-level overview — use 'df' for mounted filesystem totals. See also 'df', 'stat'.",
    "echo": "Output provided text as JSON. Read-only, no side effects. Returns JSON with the echoed text by default; use --raw for plain text output. Use to display values or construct output strings in agent pipelines. Not for formatted output — use 'printf' for precise format control with conversion specifiers. See also 'printf'.",
    "env": "Return all environment variables or filter by name pattern as structured JSON. Read-only, no side effects. Returns JSON with key-value pairs of environment variables. Use to inspect the execution context available to child processes. Not for querying a single variable by exact name — use 'printenv' for direct lookup. See also 'printenv'.",
    "expand": "Convert tab characters to spaces in files or stdin. Read-only, no side effects (does not modify files). Returns JSON with the converted text by default; use --raw for plain output. Use configurable tab stops to control spacing. Use to normalize indentation to spaces. Not for converting spaces to tabs — use 'unexpand' for the reverse operation. See also 'unexpand'.",
    "expr": "Evaluate arithmetic and string expressions in a safe, side-effect-free AST subset. Read-only, no side effects. Supports +, -, *, /, % (arithmetic), comparisons, regex matching, and string operations. Returns JSON with the computed result. Use for calculations and conditional logic in agent workflows. Not for file-based predicate tests — use 'test' or '[' for path checks. See also 'test', 'factor'.",
    "factor": "Compute the prime factorization of given non-negative integers. Read-only, no side effects. Returns JSON with an array of prime factors for each input number. Use to decompose integers into prime components. Not for general arithmetic — use 'expr' for calculations. See also 'expr'.",
    "false": "Exit with status 1 (failure). Idempotent: always returns code 1, takes no arguments, has zero side effects. Returns JSON error envelope indicating failure on stderr. Use to explicitly signal error or failure conditions in scripts and agent flows. Not for a no-op success — use 'true'. See also 'true'.",
    "fmt": "Reflow paragraphs to a target character width, preserving paragraph boundaries (blank-line separated). Read-only, no side effects. Returns JSON with reflowed text by default; use --raw for plain output. Use to reformat prose without breaking paragraph structure. Not for hard line wrapping — use 'fold' to break at exact character positions without paragraph awareness. See also 'fold'.",
    "fold": "Wrap long input lines at a fixed character width, breaking at exact positions. Read-only, no side effects. Returns JSON with wrapped text by default; use --raw for plain output. Use for display-constrained formatting or terminal-width adaptation. Not for paragraph-aware reflowing — use 'fmt' to preserve paragraph structure. See also 'fmt'.",
    "ginstall": "Copy files and set attributes like permissions and ownership — GNU-compatible alias for 'install'. Destructive: creates or overwrites target files, creates directories with --directory/--parents, and changes file metadata. Default mode is 755. Use --dry_run to preview without touching the filesystem. Returns JSON with installation paths and status. Use when GNU install semantics or BSD-compatible behavior is needed. Not for simple copying — use 'cp' for copying without permission setting. Not for the standard install interface — use 'install'. See also 'install', 'cp'.",
    "groups": "Return group names and IDs for a specified user or the current process. Read-only, no side effects. Returns JSON with group list. Use to verify group membership for access control decisions. Not for full user identity inspection — use 'id' for UID/GID plus all groups. Not for current username — use 'whoami'. See also 'id', 'whoami'.",
    "hash": "Compute hash digests of files or stdin with selectable algorithm (MD5, SHA-1, SHA-2, BLAKE2b). Read-only, no side effects. Returns JSON with per-file digests and byte counts. Use when you need flexible algorithm selection from a single tool. Not for fixed-algorithm workflows — use dedicated tools ('md5sum', 'sha256sum', 'b2sum') for consistent output. See also 'md5sum', 'sha256sum', 'b2sum'.",
    "head": "Return the first N lines (default 10) of files or stdin as JSON. Read-only, no side effects. Returns JSON with line array by default; use --raw for plain text. Supports negative-N to skip all but the last N lines. Use to preview file beginnings or extract headers. Not for viewing file endings — use 'tail' for the last N lines. See also 'tail', 'cat'.",
    "hostid": "Return a deterministic host identifier in hexadecimal format. Read-only, no side effects. Returns JSON with the host ID. Use for stable machine identification. Not for the human-readable hostname — use 'hostname'. Not for full system info — use 'uname'. See also 'hostname', 'uname'.",
    "hostname": "Return the system hostname as JSON. Read-only, no side effects. Returns JSON with the hostname string. Use to identify the machine in network contexts. Not for numeric host ID — use 'hostid'. Not for full system info — use 'uname'. See also 'hostid', 'uname'.",
    "id": "Return user identity information: UID, GID, username, and all group memberships as JSON. Read-only, no side effects. Returns JSON with full user identity. Use for comprehensive user identity inspection and access control auditing. Not for quick username check — use 'whoami'. Not for just group listing — use 'groups'. See also 'whoami', 'groups'.",
    "install": "Copy files and set attributes (permissions, ownership) to destination. Destructive: creates files and directories, overwrites existing targets with --allow_overwrite, sets mode (default 755). Use --dry_run for safe preview. Returns JSON with installation paths and status. Use for software deployment scripts and Makefile install targets. Not for simple file copying without permission changes — use 'cp'. Not for GNU-install-compatible behavior — use 'ginstall'. See also 'cp', 'ginstall'.",
    "join": "Join two sorted files on a common field (default: first whitespace-separated field), performing an inner join. Read-only, no side effects. Requires pre-sorted input — use 'sort' first. Returns JSON with joined records. Use to combine related datasets by key. Not for unsorted input — results are wrong without prior sorting. Not for side-by-side merging without key matching — use 'paste'. See also 'paste', 'comm', 'sort'.",
    "kill": "Plan or send a signal to a process by PID. Potentially destructive: can terminate or alter process execution. Use --dry_run to preview the signal without sending. Requires --allow_signal for actual signal delivery; fails safely otherwise. Use to signal, terminate, or restart processes in agent workflows. Not for process listing — use 'ps' or 'pidof' externally. See also 'nohup'.",
    "link": "Create hard links to existing files with dry-run and overwrite protection. Destructive: creates new directory entries pointing to the same inode. Hard links cannot span filesystems. Use --dry_run to preview. Overwrite protection enabled by default. Returns JSON with link path and status. Use to create additional names for the same file content without copying data. Not for symbolic links — use 'ln --symbolic'. Not for copying content — use 'cp'. See also 'ln', 'cp'.",
    "ln": "Create hard or symbolic links with dry-run and overwrite protection. Destructive: creates filesystem links. Use --symbolic for symlinks (cross-filesystem, can point to directories). Overwrite protection enabled by default. Use --dry_run to preview. Returns JSON with link path and type. Use for creating filesystem aliases. Not for hard-link-only operations — use 'link' for guaranteed hard links. Not for copying — use 'cp'. See also 'link', 'cp'.",
    "logname": "Return the original login name of the current user (unaffected by su/sudo). Read-only, no side effects. Returns JSON with the login name. Use to determine the original session identity bypassing privilege escalation. Not for the effective user ID — use 'whoami'. See also 'whoami', 'id'.",
    "ls": "List directory contents as structured JSON with per-entry metadata (type, size, permissions, modification time). Read-only, no side effects. Supports recursive depth, hidden file inclusion, symlink following, result limiting, and NDJSON streaming for large directories. Use for programmatic directory inspection. Not for column-aligned output — use 'dir'. Not for verbose metadata — use 'vdir'. Not for single-file detail — use 'stat'. See also 'dir', 'vdir', 'stat'.",
    "md5sum": "Compute MD5 hash digests of files or stdin. Read-only, no side effects. Returns JSON with per-file hash values and byte counts. Use for fast non-cryptographic integrity checks and data deduplication. Not for security or cryptographic verification — MD5 is collision-broken; use 'sha256sum' or 'b2sum' for security. See also 'sha256sum', 'hash'.",
    "mkdir": "Create directories with parent-directory creation and dry-run support. Destructive: creates new directories on the filesystem. Use --dry_run to preview without creating. Use --parents to auto-create intermediate directories. Use --mode to set permissions. Returns JSON with created paths. Fails safely if the path already exists (unless forced). Use to create directory structures. Not for removing directories — use 'rmdir' for empty directories or 'rm' for non-empty. Not for temporary directories — use 'mktemp' for unique temp paths. See also 'rmdir', 'mktemp', 'touch'.",
    "mkfifo": "Create named pipes (FIFOs) for inter-process communication. Destructive: creates a special file that blocks readers until a writer connects (and vice versa). Fails safely if the path already exists (idempotent). Use --dry_run to preview without touching the filesystem. Use --mode to set permissions (default 666). Use --parents to auto-create missing parent directories. Returns JSON with the created path, mode, and status on success; on error, returns structured JSON with exit code and error message on stderr. Use when you need a FIFO pipe for shell-style IPC between processes. Not for creating regular files — use 'touch'. Not for regular directories — use 'mkdir'. Not for device nodes — use 'mknod'. See also 'mknod', 'mkdir', 'touch'.",
    "mknod": "Create device nodes (block or character special files) with dry-run support. Destructive: creates special device files. May require elevated privileges. Use --dry_run to preview. Returns JSON with the created node path and type. Use to create device files for hardware access. Not for FIFO pipes — use 'mkfifo' for named pipes. Not for regular files — use 'touch'. See also 'mkfifo'.",
    "mktemp": "Create temporary files or directories with unique, unpredictable names atomically to prevent race conditions. Destructive: creates files/dirs on the filesystem. Returns JSON with the created path. Supports prefix and suffix for naming control. Use for safe temporary workspace creation in agent workflows. Not for persistent directories — use 'mkdir'. See also 'mkdir'.",
    "mv": "Move or rename files and directories with dry-run and overwrite protection. Destructive: relocates files on the filesystem (or renames them). Overwrite protection enabled by default — use --allow_overwrite to replace existing targets. Use --dry_run to preview. Returns JSON with source and destination paths. Use to relocate or rename files. Not for creating copies — use 'cp' to duplicate. Not for creating links — use 'ln'. See also 'cp', 'ln'.",
    "nice": "Run a command with adjusted CPU scheduling priority (niceness). Executes the given command as a subprocess, captures bounded stdout/stderr, and enforces a safety timeout. Use --dry_run to preview without execution. Positive niceness lowers priority for background tasks; negative values may require elevated privileges. Use to reduce CPU impact of background work. Not for I/O buffering control — use 'stdbuf'. Not for hangup immunity — use 'nohup'. Not for time-bound execution — use 'timeout'. See also 'stdbuf', 'nohup', 'timeout'.",
    "nl": "Number input lines with configurable formatting (alignment, delimiter, starting number). Read-only, no side effects. Returns JSON with numbered lines by default; use --raw for plain text. Use to add line numbers for reference or debugging. Not for simple concatenation — use 'cat'. See also 'cat'.",
    "nohup": "Run a command immune to SIGHUP (hangup signals), ideal for long-running background tasks. Executes the given command and captures stdout/stderr. Requires --allow_nohup confirmation for safety. Use to run tasks that should survive terminal closure. Not for CPU priority adjustment — use 'nice'. Not for time-bounded execution — use 'timeout'. See also 'nice', 'timeout'.",
    "nproc": "Return the number of available CPU processing units. Read-only, no side effects. Returns JSON with the core count; use --raw for plain integer. Use to make parallelism decisions in agent workflows. Not for system runtime info — use 'uptime'. Not for architecture info — use 'arch' or 'uname'. See also 'uptime', 'arch'.",
    "numfmt": "Convert numbers between plain, SI (K, M, G), and IEC binary (Ki, Mi, Gi) unit systems. Read-only, no side effects. Parses human-readable strings with SI/IEC suffixes back to raw numbers. Returns JSON with the converted value by default; use --raw for plain output. Use to humanize byte counts or parse user-supplied size strings. Not for formatted string output — use 'printf' for general formatting. See also 'printf'.",
    "od": "Dump input bytes as structured rows in hexadecimal, octal, or decimal format. Read-only, no side effects. Returns JSON with formatted dump by default; use --raw for traditional octal display. Use to inspect raw binary content. Not for plain text viewing — use 'cat'. See also 'cat'.",
    "paste": "Merge corresponding lines from multiple files side by side, separated by a configurable delimiter (default tab). Read-only, no side effects. Returns JSON with merged lines by default; use --raw for plain output. Use to combine columns from separate files into a table. Not for key-based joining — use 'join' for field-matched merging. Not for simple concatenation — use 'cat'. See also 'join', 'cat'.",
    "pathchk": "Validate path name components for portability (length, character set, existence). Read-only, no side effects. Returns JSON with validation result. Use to verify paths before creating or using them. Not for path resolution — use 'realpath' to resolve to absolute canonical form. See also 'realpath'.",
    "pinky": "Print detailed user account information: login name, home directory, shell, and idle time. Read-only, no side effects. Returns JSON with user profile data. Use to inspect specific user account properties. Not for current user identity — use 'whoami' or 'id'. Not for session listing — use 'who' for active sessions. See also 'who', 'id'.",
    "pr": "Paginate text into deterministic pages with configurable headers, footers, and page dimensions. Read-only, no side effects. Returns JSON with paginated output by default; use --raw for plain text. Use for print-ready formatted output. Not for paragraph reflowing — use 'fmt'. Not for line wrapping — use 'fold'. See also 'fmt', 'fold'.",
    "printenv": "Return the value of a specific environment variable by name, or all variables if no name given. Read-only, no side effects. Returns JSON with the variable value. Use for direct lookup of known variable names. Not for listing all variables with filtering — use 'env' for pattern-based filtering. See also 'env'.",
    "printf": "Format and print text using printf-style conversion specifiers (%s, %d, %f, etc.). Read-only, no side effects. Returns JSON with the formatted string by default; use --raw for plain output. Use for precise control over number formatting, padding, and type conversion. Not for simple echo without formatting — use 'echo'. See also 'echo'.",
    "ptx": "Build a permuted (keyword-in-context) index from input text, showing each word in its surrounding context. Read-only, no side effects. Returns JSON with the index by default; use --raw for plain output. Use to create searchable cross-reference indices. Not for sorting or deduplication — use 'sort' and 'uniq'. See also 'sort'.",
    "pwd": "Print the current working directory as JSON. Read-only, no side effects. Returns JSON with the absolute directory path. Use to determine the active directory context before file operations. Not for path resolution — use 'realpath' to resolve symlinks and relative paths. See also 'ls', 'realpath'.",
    "readlink": "Read the target of symbolic links, or canonicalize paths with --canonicalize. Read-only, no side effects. Use --canonicalize to resolve every component of the path. Returns JSON with the resolved target or canonical path. Use to inspect symlink targets or normalize paths. Not for full path resolution with existence checks — use 'realpath' which always resolves to an absolute, existing path. See also 'realpath'.",
    "realpath": "Resolve file paths to their absolute canonical form, following all symlinks and resolving all relative components. Read-only, no side effects. Fails with a clear error if the target does not exist (use --no-symlinks to relax existence check). Returns JSON with the resolved absolute path. Use to normalize paths for comparison or before file operations. Not for reading symlink targets without full resolution — use 'readlink'. See also 'readlink'.",
    "rm": "Remove files or recursively delete directories with dry-run and safety protections. Destructive and irreversible: deleted data cannot be recovered. Use --dry_run to preview which files would be removed. Recursive directory removal requires --recursive. Sandbox checks prevent deletion outside the current working directory without explicit --allow_outside_cwd. Returns JSON with removed paths. Use to delete files and directories. Not for secure deletion — use 'shred' to overwrite before removal. Not for removing only empty directories — use 'rmdir'. See also 'rmdir', 'shred', 'unlink'.",
    "rmdir": "Remove empty directories with dry-run support. Destructive: deletes directories. Fails safely on non-empty directories (use 'rm --recursive' for those). Use --dry_run to preview. Returns JSON with the removed directory paths. Use to clean up empty directory trees. Not for removing directories with contents — use 'rm --recursive'. Not for file removal — use 'unlink' or 'rm'. See also 'rm', 'unlink'.",
    "runcon": "Plan or run a command under a specified SELinux security context. Potentially destructive: changes the security domain of the executed command. Use --dry_run to preview. Requires --allow_context confirmation. Use to test or enforce SELinux context transitions. Not for modifying file contexts — use 'chcon' for file labels. See also 'chcon'.",
    "schema": "Return the full aicoreutils JSON protocol specification: envelope structure, exit codes (0-10), output conventions, and command metadata. Read-only, no side effects. Use before invoking other tools to understand the response format and error semantics. Not for tool discovery — use 'tool-list' or 'catalog'. See also 'tool-list', 'catalog'.",
    "seq": "Print a sequence of numbers as JSON with configurable start, increment, and end values. Read-only, no side effects. Returns JSON with the number sequence array. Use to generate numeric sequences or ranges. Not for repeating a constant string — use 'yes' for fixed repetition. See also 'yes', 'printf'.",
    "sha1sum": "Compute SHA-1 hash digests of files or stdin. Read-only, no side effects. Returns JSON with per-file hash values. Use for basic integrity verification compatible with legacy systems. Not for security-critical applications — SHA-1 is cryptographically broken; use 'sha256sum' or 'b2sum'. See also 'sha256sum', 'hash'.",
    "sha224sum": "Compute SHA-224 hash digests of files or stdin. Read-only, no side effects. Returns JSON with per-file hash values. Use for cryptographic integrity verification with smaller digest size. Not for maximum security margin — use 'sha512sum' for highest strength. See also 'sha256sum', 'hash'.",
    "sha256sum": "Compute SHA-256 hash digests of files or stdin — the standard cryptographic hash. Read-only, no side effects. Returns JSON with per-file hash values. Use for cryptographic integrity verification and content addressing. This is the recommended default for security-sensitive hashing. Not for high-speed non-security use — use 'md5sum' or 'b2sum' for speed. See also 'sha512sum', 'hash', 'md5sum'.",
    "sha384sum": "Compute SHA-384 hash digests of files or stdin. Read-only, no side effects. Returns JSON with per-file hash values. Use for cryptographic integrity verification with higher security margin than SHA-256 (192-bit collision resistance). See also 'sha256sum', 'sha512sum', 'hash'.",
    "sha512sum": "Compute SHA-512 hash digests of files or stdin — the highest-strength SHA-2 variant. Read-only, no side effects. Returns JSON with per-file hash values. Use for maximum cryptographic security margin (256-bit collision resistance). Not for performance-sensitive use on 32-bit systems — use 'sha256sum'. See also 'sha256sum', 'hash'.",
    "shred": "Overwrite file contents multiple times with random data then optionally remove. Destructive and irreversible: shredded data is unrecoverable. Requires explicit --allow_destructive confirmation. Use --dry_run to preview. Use to securely erase sensitive files beyond forensic recovery. Not for simple deletion — use 'rm' for non-sensitive files. See also 'rm'.",
    "shuf": "Randomly permute input lines with optional deterministic seeding for reproducibility. Read-only, no side effects. Returns JSON with shuffled lines by default; use --raw for plain output. Set --seed for reproducible ordering. Use to randomize line order. Not for sorting — use 'sort' for ordered output. Not for deduplication — use 'uniq'. See also 'sort', 'uniq'.",
    "sleep": "Pause execution for a specified number of seconds, bounded by an upper safety limit. Blocks the calling process. Use --dry_run to preview the duration without actually sleeping. Use to introduce delays between operations. Not for time-bounded command execution — use 'timeout' to run a command with a deadline. See also 'timeout'.",
    "sort": "Sort text lines deterministically from files or stdin. Read-only, no side effects. Use --numeric for numerical sort, --reverse for descending order, --unique to remove duplicates, and --seed for deterministic tie-breaking. Returns JSON with sorted lines by default; use --raw for plain output. Use to order data for downstream processing. Not for deduplication of non-sorted data — pipe to 'uniq' for adjacent dedup. Not for randomizing — use 'shuf'. See also 'uniq', 'shuf'.",
    "split": "Split input into chunked output files by line count or byte size with dry-run and overwrite protection. Destructive: creates multiple output files. Default splits at 1000 lines per chunk. Use --dry_run to preview. Returns JSON with output file list and record counts. Use to partition large datasets. Not for content-based splitting — use 'csplit' to split at regex match points. See also 'csplit'.",
    "stat": "Return detailed file metadata: size, permissions, owner, timestamps (access, modification, change, birth), inode, and device as structured JSON. Read-only, no side effects. Use to inspect file attributes without reading file contents. Not for directory listing — use 'ls' for multi-file listings. See also 'ls', 'du'.",
    "stdbuf": "Run a command with controlled stdout/stderr/stdin buffering: 0=none (unbuffered), L=line-buffered, or a byte size. Executes as a subprocess, captures bounded stdout/stderr, and enforces a safety timeout. Use --dry_run to preview without execution. Defaults to system buffering when no mode is set. Use to diagnose buffering-related output delays or ordering issues in pipelines. Not for CPU priority control — use 'nice'. Not for time-bounded execution — use 'timeout'. See also 'nice', 'timeout'.",
    "stty": "Inspect or modify terminal device settings (baud rate, line discipline, control characters). Can change terminal behavior if --allow_change is enabled; defaults to read-only inspection. Returns JSON with terminal configuration. Use to query terminal state before operations that depend on it. Not for simple TTY detection — use 'tty' to check if stdin is a terminal. See also 'tty'.",
    "sum": "Compute legacy BSD-style 16-bit checksums and block counts for files or stdin. Read-only, no side effects. Returns JSON with checksum and block count. Use for compatibility with legacy BSD systems. Not for data integrity — CRC32 ('cksum') and cryptographic hashes ('sha256sum') are far more reliable. See also 'cksum', 'sha256sum'.",
    "sync": "Flush cached filesystem writes to persistent storage where supported. Read-only in interface but causes I/O: forces dirty buffers to disk. Returns JSON with sync status. Use to ensure data durability before critical operations like system shutdown. Not for general use before every file operation — most commands flush on close. See also 'dd'.",
    "tac": "Reverse the order of input lines (last line first). Read-only, no side effects. Returns JSON with reversed lines by default; use --raw for plain output. Use to invert line order for LIFO processing. Not for sorting — use 'sort --reverse' for reverse-sorted order. See also 'sort', 'cat'.",
    "tail": "Return the last N lines (default 10) of files or stdin as JSON. Read-only, no side effects. Returns JSON with line array by default; use --raw for plain text. Supports negative-N to skip the first N lines. Use to view recent file additions or check log tails. Not for viewing file beginnings — use 'head'. See also 'head', 'cat'.",
    "tee": "Read stdin and write simultaneously to files and stdout with dry-run and append support. Destructive: writes to specified output files. Use --dry_run to preview. Use --append to add to files instead of overwriting. Returns JSON with output paths and byte counts. Use to capture intermediate pipeline data while passing it through. Not for simple file writing without passthrough — use redirection or 'cp'. For secure overwriting use 'shred'. See also 'cat', 'echo'.",
    "test": "Evaluate file predicates (exists, is_file, is_dir, is_executable, is_symlink, is_readable, is_writable) and return structured JSON with the boolean result. Read-only, no side effects. Returns JSON indicating test result and exit code (0 for true, 1 for false). Use for conditional branching based on file properties in scripts. Not for detailed file inspection — use 'stat' for full metadata. See also 'stat', '['.",
    "timeout": "Run a command with a bounded time limit, automatically terminating it if it exceeds the duration. Captures stdout/stderr up to max_output_bytes. Returns JSON with command output and whether it timed out. Use to prevent runaway commands from blocking agent workflows. Not for introducing delays — use 'sleep' to pause. Not for CPU priority — use 'nice'. See also 'sleep', 'nice'.",
    "tool-list": "Return a compact tool index optimized for LLM function-calling context windows. Read-only, no side effects. Returns JSON with tool names, descriptions, and parameter schemas by default. Use --format=openai for OpenAI-compatible function definitions, --format=anthropic for Anthropic tool format. Use before agent planning to discover available capabilities. Not for human browsing — use 'catalog' for category-organized listing. See also 'catalog', 'coreutils'.",
    "touch": "Update file access and modification timestamps to the current time, or create empty files if they do not exist. Modifies filesystem metadata (timestamps), creates files when path does not exist. Returns JSON with the touched path. Use to refresh timestamps or ensure a file exists. Not for creating directories — use 'mkdir'. Not for changing file size — use 'truncate'. See also 'mkdir', 'truncate'.",
    "tr": "Translate or delete literal characters from files or stdin — character-by-character replacement (NO regex). Read-only, no side effects (reads input, writes to stdout). Use --delete to remove specific characters, --squeeze to collapse repeats. Returns JSON by default; use --raw for plain output. Use for simple character mapping. Not for regex-based substitution — use 'sed' externally. Not for column extraction — use 'cut'. See also 'cut', 'expand'.",
    "true": "Exit with status 0 (success). Idempotent: always succeeds, takes no arguments, has zero side effects. Returns JSON success envelope. Use to signal successful completion or as a placeholder in scripts. Not for failure signaling — use 'false'. See also 'false'.",
    "truncate": "Shrink or extend file sizes to an exact byte length with dry-run and overwrite protection. Destructive: modifies file content — shrinking discards data, extending fills with null bytes. Use --dry_run to preview. Returns JSON with old and new file size. Use to resize files programmatically. Not for timestamp-only updates — use 'touch'. Not for block-level copying — use 'dd'. See also 'touch', 'dd'.",
    "tsort": "Perform topological sort on whitespace-separated dependency pairs (partial order), detecting cycles. Read-only, no side effects. Returns JSON with the sorted order; reports cycles with specific node information on error. Use for dependency resolution and build-order calculation. Not for lexical sorting — use 'sort' for alphabetical or numerical ordering. See also 'sort'.",
    "tty": "Check if stdin is connected to a terminal and return the terminal device path. Read-only, no side effects. Returns JSON with the TTY path and connection status; exits non-zero if not a TTY. Use to detect interactive vs. piped execution contexts. Not for terminal configuration — use 'stty' for terminal settings. See also 'stty'.",
    "uname": "Return system identification: kernel name, hostname, kernel release, kernel version, and machine architecture as structured JSON. Read-only, no side effects. Use for cross-platform system fingerprinting. Not for single-field queries — use 'arch' for architecture only or 'hostname' for hostname only. See also 'arch', 'hostname'.",
    "unexpand": "Convert leading spaces to tab characters in files or stdin. Read-only, no side effects (does not modify files). Returns JSON by default; use --raw for plain output. Use to compress indentation for storage. Not for tabs to spaces — use 'expand' for the reverse operation. See also 'expand'.",
    "uniq": "Collapse adjacent duplicate lines, optionally counting occurrences or showing only unique/duplicate lines. Read-only, no side effects. Returns JSON by default; use --raw for plain output. Use to remove or count consecutive duplicates. IMPORTANT: only works on adjacent duplicates — pipe through 'sort' first for full deduplication. Not for standalone dedup without sorting — always combine with 'sort' for complete duplicate removal. See also 'sort'.",
    "unlink": "Remove a single file (not directories) with dry-run support. Destructive and irreversible. Fails safely on directories. Use --dry_run to preview. Returns JSON with the removed path. Use to delete individual files by name. Not for recursive directory removal — use 'rm --recursive'. Not for empty directories — use 'rmdir'. See also 'rm', 'rmdir'.",
    "uptime": "Return system uptime in seconds since boot. Read-only, no side effects. Returns JSON with uptime; use --raw for plain integer. Use to check system stability or time since last reboot. Not for current time — use 'date'. Not for CPU information — use 'nproc' for core count. See also 'date', 'nproc'.",
    "users": "List currently logged-in user names (one per unique user). Read-only, no side effects. Returns JSON with user list. Use for quick session presence check. Not for detailed session info — use 'who' for terminal, login time, and remote host per session. Not for user account details — use 'pinky'. See also 'who', 'pinky'.",
    "vdir": "List directory contents with verbose (long-format) output — alias for 'ls -l'. Read-only, no side effects. Returns JSON with extended per-entry metadata. Use when you need detailed file information in a listing. Not for compact listings — use 'ls' or 'dir' for concise output. Not for single-file detail — use 'stat' for the most complete metadata. See also 'ls', 'dir', 'stat'.",
    "wc": "Count bytes, characters, words, and lines in files or stdin, returning results as structured JSON. Read-only, no side effects. Returns per-file counts plus totals when multiple files are provided. Use to measure document size and complexity. Not for disk usage — use 'du' for file sizes on disk. Not for file metadata — use 'stat'. See also 'stat', 'du'.",
    "who": "Return active user sessions with terminal device, login time, and originating host. Read-only, no side effects. Returns JSON with session details. Use to audit active logins and session activity. Not for just usernames — use 'users' for a compact name list. Not for user account properties — use 'pinky' for home directory and shell. See also 'users', 'pinky'.",
    "whoami": "Return the effective user identity (username, UID, GID) of the current process as JSON. Read-only, no side effects. Use to determine which user the agent is running as before performing permission-sensitive operations. Not for the original login identity — use 'logname' to bypass su/sudo. Not for full identity details — use 'id' for all groups. See also 'id', 'logname'.",
    "yes": "Repeatedly print a given string (default 'y') to stdout, bounded by an optional count. Read-only, no side effects. Use to auto-answer interactive prompts expecting 'y' confirmation. Not for generating number sequences — use 'seq'. Not for formatted output — use 'printf'. See also 'seq', 'printf'.",
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


_READ_ONLY_TOOLS: set[str] = {
    "catalog",
    "schema",
    "coreutils",
    "tool-list",
    "pwd",
    "basename",
    "dirname",
    "realpath",
    "readlink",
    "test",
    "[",
    "ls",
    "dir",
    "vdir",
    "stat",
    "cat",
    "head",
    "tail",
    "wc",
    "md5sum",
    "sha1sum",
    "sha224sum",
    "sha256sum",
    "sha384sum",
    "sha512sum",
    "b2sum",
    "hash",
    "cksum",
    "sum",
    "sort",
    "comm",
    "join",
    "paste",
    "shuf",
    "tac",
    "nl",
    "fold",
    "fmt",
    "od",
    "numfmt",
    "tsort",
    "pr",
    "ptx",
    "uniq",
    "cut",
    "tr",
    "expand",
    "unexpand",
    "base64",
    "base32",
    "basenc",
    "date",
    "env",
    "printenv",
    "whoami",
    "groups",
    "id",
    "uname",
    "arch",
    "hostname",
    "hostid",
    "logname",
    "uptime",
    "tty",
    "users",
    "pinky",
    "who",
    "nproc",
    "df",
    "du",
    "dircolors",
    "seq",
    "printf",
    "echo",
    "pathchk",
    "factor",
    "expr",
    "true",
    "false",
    "yes",
}


_DESTRUCTIVE_TOOLS: set[str] = {
    "dd",
    "chroot",
    "kill",
    "nohup",
    "chcon",
    "runcon",
    "mkdir",
    "touch",
    "cp",
    "mv",
    "ln",
    "link",
    "chmod",
    "chown",
    "chgrp",
    "truncate",
    "mktemp",
    "mkfifo",
    "mknod",
    "install",
    "ginstall",
    "tee",
    "rmdir",
    "unlink",
    "rm",
    "shred",
    "csplit",
    "split",
    "sync",
    "sleep",
    "timeout",
    "stdbuf",
    "stty",
    "nice",
}


_WRITE_TOOLS: set[str] = {
    "dd",
    "mkdir",
    "touch",
    "cp",
    "mv",
    "ln",
    "link",
    "chmod",
    "chown",
    "chgrp",
    "truncate",
    "mktemp",
    "mkfifo",
    "mknod",
    "install",
    "ginstall",
    "tee",
    "rmdir",
    "unlink",
    "rm",
    "shred",
    "csplit",
    "split",
    "chcon",
}


_PROCESS_EXEC_TOOLS: set[str] = {
    "chroot",
    "nice",
    "nohup",
    "runcon",
    "stdbuf",
    "timeout",
}


_PLATFORM_SENSITIVE_TOOLS: set[str] = {
    "chcon",
    "chgrp",
    "chmod",
    "chown",
    "chroot",
    "groups",
    "id",
    "kill",
    "logname",
    "mkfifo",
    "mknod",
    "nice",
    "nohup",
    "nproc",
    "pinky",
    "runcon",
    "sleep",
    "stty",
    "sync",
    "tty",
    "users",
    "who",
}


_EXPLICIT_ALLOW_TOOLS: set[str] = {
    "chcon",
    "chroot",
    "kill",
    "nice",
    "nohup",
    "rm",
    "runcon",
    "shred",
    "stty",
}


_WORKSPACE_WRITE_TOOLS: set[str] = {
    "cp",
    "csplit",
    "ginstall",
    "install",
    "link",
    "ln",
    "mkdir",
    "mktemp",
    "split",
    "tee",
    "touch",
}


def tool_risk_level(name: str) -> str:
    """Return the single primary risk level for a command."""
    if name in _READ_ONLY_TOOLS:
        return "read-only"
    if name in _PROCESS_EXEC_TOOLS:
        return "process-exec"
    if name in {"rm", "shred", "unlink", "rmdir", "truncate", "dd", "kill", "chroot", "chcon", "runcon", "stty"}:
        return "destructive"
    if name in _WRITE_TOOLS:
        return "write"
    if name in _PLATFORM_SENSITIVE_TOOLS:
        return "platform-sensitive"
    return "unknown"


def tool_risk_categories(name: str) -> list[str]:
    """Return all risk categories that apply to a command."""
    categories: list[str] = []
    if name in _READ_ONLY_TOOLS:
        categories.append("read-only")
    if name in _WRITE_TOOLS:
        categories.append("write")
    if name in _DESTRUCTIVE_TOOLS:
        categories.append("destructive")
    if name in _PROCESS_EXEC_TOOLS:
        categories.append("process-exec")
    if name in _PLATFORM_SENSITIVE_TOOLS:
        categories.append("platform-sensitive")
    return categories or ["unknown"]


def tool_risk_metadata(name: str) -> dict[str, bool | str | list[str]]:
    """Return machine-readable risk metadata for external tool-list formats."""
    return {
        "riskLevel": tool_risk_level(name),
        "riskCategory": tool_risk_categories(name),
        "requiresExplicitAllow": name in _EXPLICIT_ALLOW_TOOLS,
    }


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

        desc = _COMMAND_DESCRIPTIONS.get(name, subparser.description or "")
        annotations: dict[str, bool | str | list[str]] = tool_risk_metadata(name)
        if name in _READ_ONLY_TOOLS:
            annotations["readOnlyHint"] = True
        if name in _DESTRUCTIVE_TOOLS:
            annotations["destructiveHint"] = True
        tools.append(
            {
                "name": name,
                "description": desc,
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
                "annotations": annotations,
            }
        )

    return tools


def _risk_extension(tool: dict[str, Any]) -> dict[str, bool | str | list[str]]:
    annotations = tool.get("annotations", {})
    return {
        "riskLevel": annotations.get("riskLevel", "unknown"),
        "riskCategory": annotations.get("riskCategory", ["unknown"]),
        "requiresExplicitAllow": bool(annotations.get("requiresExplicitAllow", False)),
    }


def tools_openai(tools: list[dict[str, Any]], *, include_risk: bool = False) -> list[dict[str, Any]]:
    """Convert tool schemas to OpenAI function-calling format."""
    result: list[dict[str, Any]] = []
    for tool in tools:
        item: dict[str, Any] = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["inputSchema"],
            },
        }
        if include_risk:
            item["x-aicoreutils-risk"] = _risk_extension(tool)
        result.append(item)
    return result


def tools_anthropic(tools: list[dict[str, Any]], *, include_risk: bool = False) -> list[dict[str, Any]]:
    """Convert tool schemas to Anthropic tool-use format."""
    result: list[dict[str, Any]] = []
    for tool in tools:
        item: dict[str, Any] = {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["inputSchema"],
        }
        if include_risk:
            item["x-aicoreutils-risk"] = _risk_extension(tool)
        result.append(item)
    return result

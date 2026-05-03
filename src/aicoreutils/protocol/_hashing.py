"""Hash / checksum utilities: MD5, SHA-1/2, BLAKE2b, BSD-style sum."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..core import HASH_CHUNK_SIZE, AgentError, ensure_exists

# 命令名 → hashlib 算法名 的映射表
# 用于 hash/md5sum/sha*sum/b2sum 命令的动态算法选择
HASH_ALGORITHMS: dict[str, str] = {
    "md5": "md5",
    "sha1": "sha1",
    "sha224": "sha224",
    "sha256": "sha256",
    "sha384": "sha384",
    "sha512": "sha512",
    "b2sum": "blake2b",  # BLAKE2b（SHA-3 竞赛入围算法）
    "blake2b": "blake2b",  # 别名
}


def digest_file(path: Path, algorithm: str, *, chunk_size: int = HASH_CHUNK_SIZE) -> str:
    """计算文件哈希摘要（分块读取，支持大文件）。

    默认块大小 1 MiB (HASH_CHUNK_SIZE)，平衡内存使用和 I/O 效率。
    """
    if algorithm not in HASH_ALGORITHMS:
        raise AgentError(
            "invalid_input",
            f"Unsupported hash algorithm: {algorithm}",
            suggestion=f"Use one of: {', '.join(sorted(HASH_ALGORITHMS))}.",
        )
    ensure_exists(path)
    if path.is_dir():
        raise AgentError("invalid_input", "Path is a directory, not a file.", path=str(path))
    digest = hashlib.new(HASH_ALGORITHMS[algorithm])
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def digest_bytes(data: bytes, algorithm: str) -> str:
    """计算内存中字节数据的哈希摘要。"""
    if algorithm not in HASH_ALGORITHMS:
        raise AgentError(
            "invalid_input",
            f"Unsupported hash algorithm: {algorithm}",
            suggestion=f"Use one of: {', '.join(sorted(HASH_ALGORITHMS))}.",
        )
    digest = hashlib.new(HASH_ALGORITHMS[algorithm])
    digest.update(data)
    return digest.hexdigest()


def simple_sum16(data: bytes) -> int:
    """BSD-style 16-bit checksum：所有字节求和后取低 16 位。

    用于 cksum/sum 命令的基础校验模式。
    """
    return sum(data) & 0xFFFF

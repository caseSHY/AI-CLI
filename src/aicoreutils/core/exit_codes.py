"""Core exit codes for aicoreutils.

语义退出码映射表。所有 aicoreutils 命令通过此表将语义错误码
转换为 POSIX 进程退出码。这不是 POSIX 标准码的全集，而是针对
Agent 调用场景精简的语义子集。

设计原则：
- 0 仅表示成功（ok），不用作其他语义。
- 1 是通用失败（谓词为假或一般错误）。
- 8 是安全保留码（unsafe_operation），所有沙箱拒绝均使用此码。
- 跳过了 9（kill 信号）因为 Agent 不应主动发送信号。
- 跳过了 11-63 保留给未来扩展。
"""

from __future__ import annotations

# 语义码 → POSIX 退出码映射
# 调用方通过 AgentError.exit_code 属性间接使用此表
EXIT: dict[str, int] = {
    "ok": 0,  # 成功完成
    "predicate_false": 1,  # 谓词为假（如 test 命令判断文件不存在）
    "general_error": 1,  # 一般错误（兜底）
    "usage": 2,  # 参数错误或用法错误
    "not_found": 3,  # 路径不存在
    "permission_denied": 4,  # 权限不足
    "invalid_input": 5,  # 输入数据无效（如 base64 解码失败）
    "conflict": 6,  # 目标冲突（如覆盖已存在文件但未授权）
    "partial_failure": 7,  # 部分成功、部分失败
    "unsafe_operation": 8,  # 被安全策略阻止（沙箱拒绝）
    "io_error": 10,  # I/O 错误（磁盘满、读取中断等）
}

"""CLI entry point for `python -m agentutils ...`.

当用户执行 `python -m agentutils ls .` 时，Python 会运行此文件。
它只是委托给 parser.main()，后者负责参数解析、命令分发和异常处理。
"""

from .parser import main

if __name__ == "__main__":
    # SystemExit 携带正确的退出码，确保 Agent 能通过 $? 判断成功/失败
    raise SystemExit(main())

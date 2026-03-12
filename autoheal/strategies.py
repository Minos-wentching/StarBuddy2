"""
自动修复策略库

修复链路：内置策略 → Gemini CLI → Claude Code CLI
所有 AI agent 的思维链和交互信息会实时打印到终端。
"""

import re
import subprocess
import sys
import shutil
import importlib.util
import time as _time
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent

# Python 标准库模块列表（部分）
STDLIB_MODULES = {
    "os", "sys", "re", "json", "math", "datetime", "time", "random",
    "collections", "functools", "itertools", "pathlib", "typing",
    "logging", "unittest", "io", "abc", "copy", "hashlib", "uuid",
    "asyncio", "threading", "multiprocessing", "subprocess", "shutil",
    "tempfile", "glob", "fnmatch", "pickle", "csv", "xml", "html",
    "http", "urllib", "email", "socket", "ssl", "signal", "contextlib",
    "dataclasses", "enum", "inspect", "textwrap", "string", "struct",
    "codecs", "base64", "binascii", "hmac", "secrets", "argparse",
    "configparser", "pprint", "traceback", "warnings", "weakref",
}


class RepairStrategy:
    """修复策略基类"""

    def can_handle(self, error_info: Dict[str, Any]) -> bool:
        raise NotImplementedError

    def repair(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class ImportErrorStrategy(RepairStrategy):
    """ImportError / ModuleNotFoundError 修复策略"""

    def can_handle(self, error_info: Dict[str, Any]) -> bool:
        return error_info.get("type") in ("IMPORT_ERROR", "MODULE_NOT_FOUND")

    def repair(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        message = error_info.get("message", "")
        match = re.search(r"No module named '([^']+)'", message)
        if not match:
            return {"success": False, "reason": "无法提取模块名"}

        module = match.group(1).split(".")[0]  # 取顶层包名

        if module in STDLIB_MODULES:
            return {"success": False, "reason": f"{module} 是标准库模块，无需安装"}

        logger.info(f"尝试安装缺失模块: {module}")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", module],
                capture_output=True, text=True, timeout=120,
                cwd=str(PROJECT_ROOT)
            )
            if result.returncode == 0:
                return {"success": True, "action": f"pip install {module}"}
            return {"success": False, "reason": result.stderr[:500]}
        except subprocess.TimeoutExpired:
            return {"success": False, "reason": "安装超时"}
        except Exception as e:
            return {"success": False, "reason": str(e)}


class SyntaxErrorStrategy(RepairStrategy):
    """SyntaxError 修复策略"""

    def can_handle(self, error_info: Dict[str, Any]) -> bool:
        return error_info.get("type") == "SYNTAX_ERROR"

    def repair(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        message = error_info.get("message", "")

        # 提取文件路径和行号
        file_match = re.search(r'File "([^"]+)", line (\d+)', message)
        if not file_match:
            return {"success": False, "reason": "无法提取文件路径和行号"}

        file_path = Path(file_match.group(1))
        line_num = int(file_match.group(2))

        if not file_path.exists():
            return {"success": False, "reason": f"文件不存在: {file_path}"}

        # 备份原文件
        backup_path = file_path.with_suffix(file_path.suffix + ".backup")
        shutil.copy2(file_path, backup_path)

        try:
            lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
            if line_num > len(lines):
                return {"success": False, "reason": f"行号 {line_num} 超出文件范围"}

            target_line = lines[line_num - 1]
            fixed = False

            # 修复缺少冒号
            if "expected ':'" in message or "expected :" in message:
                lines[line_num - 1] = target_line.rstrip("\n") + ":\n"
                fixed = True
            # 修复未闭合括号
            elif "unexpected EOF" in message or "')'" in message:
                lines[line_num - 1] = target_line.rstrip("\n") + ")\n"
                fixed = True
            # 修复未闭合字符串
            elif "unterminated string" in message:
                quote = "'" if "'" in target_line else '"'
                lines[line_num - 1] = target_line.rstrip("\n") + quote + "\n"
                fixed = True

            if fixed:
                new_content = "".join(lines)
                # 验证语法
                try:
                    compile(new_content, str(file_path), "exec")
                    file_path.write_text(new_content, encoding="utf-8")
                    return {"success": True, "action": f"修复 {file_path}:{line_num}"}
                except SyntaxError:
                    # 修复后仍有语法错误，恢复备份
                    shutil.copy2(backup_path, file_path)
                    return {"success": False, "reason": "修复后仍有语法错误"}

            return {"success": False, "reason": "无法自动修复此类语法错误"}

        except Exception as e:
            # 恢复备份
            if backup_path.exists():
                shutil.copy2(backup_path, file_path)
            return {"success": False, "reason": str(e)}


class FileNotFoundStrategy(RepairStrategy):
    """FileNotFoundError 修复策略"""

    def can_handle(self, error_info: Dict[str, Any]) -> bool:
        return error_info.get("type") == "FILE_NOT_FOUND"

    def repair(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        message = error_info.get("message", "")
        match = re.search(r"No such file or directory: '([^']+)'", message)
        if not match:
            return {"success": False, "reason": "无法提取文件路径"}

        missing_path = Path(match.group(1))

        try:
            # 创建父目录
            missing_path.parent.mkdir(parents=True, exist_ok=True)

            # 对配置文件生成模板内容
            suffix = missing_path.suffix.lower()
            if suffix == ".json":
                missing_path.write_text("{}", encoding="utf-8")
            elif suffix in (".yaml", ".yml"):
                missing_path.write_text("# auto-generated\n", encoding="utf-8")
            elif suffix == ".env":
                missing_path.write_text("# auto-generated\n", encoding="utf-8")
            else:
                missing_path.touch()

            return {"success": True, "action": f"创建文件: {missing_path}"}

        except Exception as e:
            return {"success": False, "reason": str(e)}


class GeminiStrategy(RepairStrategy):
    """Gemini CLI 修复策略"""

    def can_handle(self, error_info: Dict[str, Any]) -> bool:
        return shutil.which("gemini") is not None

    def repair(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._build_prompt(error_info)

        try:
            cmd = ["gemini", "-p", prompt]
            logger.info(f"调用 Gemini CLI 修复...")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300,
                cwd=str(PROJECT_ROOT)
            )
            # 实时打印输出
            if result.stdout:
                for line in result.stdout.splitlines():
                    print(f"  [Gemini] {line}")

            if result.returncode == 0:
                return {"success": True, "action": "Gemini CLI 修复", "output": result.stdout[:1000]}
            return {"success": False, "reason": result.stderr[:500]}

        except subprocess.TimeoutExpired:
            return {"success": False, "reason": "Gemini CLI 超时"}
        except Exception as e:
            return {"success": False, "reason": str(e)}

    def _build_prompt(self, error_info: Dict[str, Any]) -> str:
        return (
            f"你是一个自动修复 agent。后端容器日志中检测到以下错误，请直接修复源码。\n\n"
            f"错误类型: {error_info.get('type', 'UNKNOWN')}\n"
            f"错误信息: {error_info.get('message', '')}\n"
            f"文件路径: {error_info.get('file_path', '未知')}\n"
            f"行号: {error_info.get('line_number', '未知')}\n\n"
            f"请分析错误原因，找到对应的源码文件并直接修复。\n"
            f"源码在当前目录的 backend/ 下。\n"
            f"只修改必要的代码，不要做多余的重构。\n"
            f"修复完成后简要说明你做了什么。"
        )


class ClaudeCodeStrategy(RepairStrategy):
    """Claude Code CLI 修复策略（终极兜底）"""

    def can_handle(self, error_info: Dict[str, Any]) -> bool:
        return shutil.which("claude") is not None

    def repair(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._build_prompt(error_info)

        extra_env = dict(os.environ)
        for key in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL"):
            if key in os.environ:
                extra_env[key] = os.environ[key]

        try:
            cmd = ["claude", "--print", "--dangerously-skip-permissions", "-p", prompt]
            logger.info(f"调用 Claude Code CLI 修复...")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300,
                cwd=str(PROJECT_ROOT), env=extra_env
            )
            if result.stdout:
                for line in result.stdout.splitlines():
                    print(f"  [Claude] {line}")

            if result.returncode == 0:
                return {"success": True, "action": "Claude Code CLI 修复", "output": result.stdout[:1000]}
            return {"success": False, "reason": result.stderr[:500]}

        except subprocess.TimeoutExpired:
            return {"success": False, "reason": "Claude Code CLI 超时"}
        except Exception as e:
            return {"success": False, "reason": str(e)}

    def _build_prompt(self, error_info: Dict[str, Any]) -> str:
        return GeminiStrategy()._build_prompt(error_info)


import os


class RepairStrategyFactory:
    """修复策略工厂 — 三级修复链"""

    def __init__(self):
        self.builtin_strategies = [
            ImportErrorStrategy(),
            SyntaxErrorStrategy(),
            FileNotFoundStrategy(),
        ]
        self.ai_strategies = [
            GeminiStrategy(),
            ClaudeCodeStrategy(),
        ]

    def repair(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """按优先级尝试修复"""
        # 第一层：内置策略
        for strategy in self.builtin_strategies:
            if strategy.can_handle(error_info):
                logger.info(f"使用内置策略: {strategy.__class__.__name__}")
                result = strategy.repair(error_info)
                if result.get("success"):
                    return result
                logger.warning(f"内置策略失败: {result.get('reason')}")

        # 第二层/第三层：AI 策略
        for strategy in self.ai_strategies:
            if strategy.can_handle(error_info):
                logger.info(f"升级到 AI 策略: {strategy.__class__.__name__}")
                result = strategy.repair(error_info)
                if result.get("success"):
                    return result
                logger.warning(f"AI 策略失败: {result.get('reason')}")

        return {"success": False, "reason": "所有修复策略均失败"}


def repair_error(error_info: Dict[str, Any]) -> Dict[str, Any]:
    """便捷函数：修复错误"""
    factory = RepairStrategyFactory()
    return factory.repair(error_info)

"""
自动修复 Agent

支持两种监控模式：
- docker: 通过 Docker SDK 监控容器日志
- logfile: 直接监控本地日志文件（无需 Docker）

mode=auto 时自动检测：有 Docker 就用 Docker，否则回退到 logfile。
"""

import asyncio
import re
import json
import signal
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from .config import get_config
from .strategies import repair_error
from .dashboard import Dashboard, print_dashboard

logger = logging.getLogger(__name__)

ERROR_PATTERNS = []
HISTORY_FILE = Path(__file__).parent / "repair_history.json"


class LogSource:
    """日志源基类"""
    async def stream(self):
        raise NotImplementedError


class DockerLogSource(LogSource):
    """Docker 容器日志源"""

    def __init__(self, container_name: str = ""):
        self.container_name = container_name

    def _find_container(self):
        try:
            import docker
            client = docker.from_env()
            containers = client.containers.list()

            if self.container_name:
                for c in containers:
                    if self.container_name in c.name:
                        return c

            # 自动检测
            for c in containers:
                if "backend" in c.name:
                    return c
            for c in containers:
                if "app" in c.name:
                    return c
            if containers:
                return containers[0]
        except Exception as e:
            logger.error(f"Docker 连接失败: {e}")
        return None

    async def stream(self):
        container = self._find_container()
        if not container:
            logger.error("未找到可监控的容器")
            return

        logger.info(f"开始监控容器: {container.name}")
        for line in container.logs(stream=True, follow=True, tail=0):
            yield line.decode("utf-8", errors="replace").strip()


class LogFileSource(LogSource):
    """本地日志文件源"""

    def __init__(self, log_file: str):
        self.log_file = Path(log_file)

    async def stream(self):
        if not self.log_file.exists():
            logger.error(f"日志文件不存在: {self.log_file}")
            return

        with open(self.log_file, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)  # 跳到文件末尾
            while True:
                line = f.readline()
                if line:
                    yield line.strip()
                else:
                    await asyncio.sleep(0.5)


class AutoHealAgent:
    """自动修复 Agent"""

    def __init__(self):
        self.config = get_config()
        self.dashboard = Dashboard()
        self.running = False
        self._cooldown: Dict[str, float] = {}
        self._hourly_count = 0
        self._hourly_reset = datetime.now()
        self._compile_patterns()

    def _compile_patterns(self):
        """编译错误模式正则"""
        global ERROR_PATTERNS
        ERROR_PATTERNS = []
        for p in self.config.error_patterns:
            try:
                ERROR_PATTERNS.append({
                    "regex": re.compile(p["pattern"]),
                    "type": p["type"],
                    "severity": p.get("severity", "MEDIUM"),
                })
            except re.error as e:
                logger.warning(f"无效的正则模式 {p['pattern']}: {e}")

    def _detect_error(self, line: str) -> Optional[Dict[str, Any]]:
        """检测日志行中的错误"""
        for pattern in ERROR_PATTERNS:
            match = pattern["regex"].search(line)
            if match:
                return {
                    "type": pattern["type"],
                    "severity": pattern["severity"],
                    "message": line,
                    "matched": match.group(0),
                    "timestamp": datetime.now().isoformat(),
                }
        return None

    def _check_cooldown(self, error_type: str) -> bool:
        """检查冷却时间"""
        import time
        now = time.time()

        # 每小时限流
        if (datetime.now() - self._hourly_reset).total_seconds() > 3600:
            self._hourly_count = 0
            self._hourly_reset = datetime.now()

        if self._hourly_count >= self.config.max_repairs_per_hour:
            logger.warning("已达到每小时修复上限")
            return False

        # 同类错误冷却
        last_time = self._cooldown.get(error_type, 0)
        if now - last_time < self.config.cooldown_seconds:
            return False

        self._cooldown[error_type] = now
        self._hourly_count += 1
        return True

    async def _verify_health(self) -> bool:
        """修复后健康检查"""
        import httpx

        await asyncio.sleep(self.config.reload_wait)

        timeout = self.config.health_check_timeout
        interval = 2
        elapsed = 0

        async with httpx.AsyncClient() as client:
            while elapsed < timeout:
                try:
                    resp = await client.get(self.config.health_check_url, timeout=5)
                    if resp.status_code == 200:
                        logger.info("健康检查通过")
                        return True
                except Exception:
                    pass
                await asyncio.sleep(interval)
                elapsed += interval

        logger.warning("健康检查超时")
        return False

    async def _handle_error(self, error_info: Dict[str, Any]):
        """处理检测到的错误"""
        error_type = error_info["type"]

        if not self._check_cooldown(error_type):
            return

        logger.info(f"检测到错误 [{error_type}]: {error_info['message'][:100]}")
        self.dashboard.add_error(error_info)

        # 尝试修复
        result = repair_error(error_info)
        self.dashboard.add_repair_result(error_info, result)

        if result.get("success"):
            logger.info(f"修复成功: {result.get('action')}")
            await self._verify_health()
        else:
            logger.warning(f"修复失败: {result.get('reason')}")

    def _get_log_source(self) -> LogSource:
        """获取日志源"""
        mode = self.config.monitor_mode

        if mode == "logfile" or (mode == "auto" and self.config.log_file):
            return LogFileSource(self.config.log_file)

        # 默认尝试 Docker
        return DockerLogSource(self.config.container_name)

    async def start(self):
        """启动监控"""
        self.running = True
        source = self._get_log_source()

        logger.info(f"AutoHeal Agent 启动 (模式: {self.config.monitor_mode})")
        print_dashboard(self.dashboard)

        try:
            async for line in source.stream():
                if not self.running:
                    break

                error_info = self._detect_error(line)
                if error_info:
                    await self._handle_error(error_info)
        except asyncio.CancelledError:
            logger.info("监控已取消")
        except Exception as e:
            logger.error(f"监控异常: {e}")
        finally:
            self.running = False
            logger.info("AutoHeal Agent 已停止")

    def stop(self):
        """停止监控"""
        self.running = False


class Butler:
    """管家模式：一键启动容器 + 监控 + 自动修复"""

    def __init__(self):
        self.config = get_config()
        self.agent = AutoHealAgent()

    async def start(self):
        """启动管家模式"""
        import subprocess

        logger.info("Butler 模式启动...")

        # 1. 启动容器
        logger.info("启动 Docker 容器...")
        try:
            subprocess.run(
                f"{self.config.compose_cmd} up -d --build".split(),
                cwd=str(self.config.project_root),
                check=True,
            )
            logger.info("容器启动成功")
        except subprocess.CalledProcessError as e:
            logger.error(f"容器启动失败: {e}")
            return

        # 2. 等待健康检查
        logger.info("等待后端就绪...")
        healthy = await self.agent._verify_health()
        if not healthy:
            logger.warning("后端未就绪，但继续监控...")

        # 3. 开始监控
        await self.agent.start()

    async def stop(self):
        """停止管家模式"""
        import subprocess

        self.agent.stop()

        logger.info("停止 Docker 容器...")
        try:
            subprocess.run(
                f"{self.config.compose_cmd} down".split(),
                cwd=str(self.config.project_root),
                check=True,
            )
            logger.info("容器已停止")
        except subprocess.CalledProcessError as e:
            logger.error(f"容器停止失败: {e}")

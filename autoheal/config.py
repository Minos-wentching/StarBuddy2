"""
自动修复系统配置

集中管理所有监控和修复配置。
支持环境变量覆盖和配置文件加载。
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class AutoHealConfig:
    """自动修复系统配置"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.error_patterns_file = self.project_root / "error_patterns.json"

        # 监控配置
        self.monitor_mode = os.environ.get("AUTOHEAL_MODE", "auto")  # docker/logfile/auto
        self.log_file = os.environ.get("AUTOHEAL_LOG_FILE", "")
        self.container_name = os.environ.get("AUTOHEAL_CONTAINER", "")

        # 修复配置
        self.max_repairs_per_hour = int(os.environ.get("AUTOHEAL_MAX_REPAIRS", "10"))
        self.cooldown_seconds = int(os.environ.get("AUTOHEAL_COOLDOWN", "60"))
        self.repair_timeout = int(os.environ.get("AUTOHEAL_REPAIR_TIMEOUT", "300"))
        self.max_repair_attempts = int(os.environ.get("AUTOHEAL_MAX_ATTEMPTS", "3"))

        # 健康检查
        self.health_check_url = os.environ.get("AUTOHEAL_HEALTH_URL", "http://localhost:8000/health")
        self.health_check_timeout = int(os.environ.get("AUTOHEAL_HEALTH_TIMEOUT", "20"))
        self.reload_wait = int(os.environ.get("AUTOHEAL_RELOAD_WAIT", "4"))

        # AI 工具路径
        self.gemini_cmd = os.environ.get("GEMINI_CMD", "gemini")
        self.claude_cmd = os.environ.get("CLAUDE_CMD", "claude")

        # Docker Compose
        self.compose_cmd = self._detect_compose_cmd()

        # 加载错误模式
        self.error_patterns = self._load_error_patterns()

        # 安全边界
        self.allowed_dirs = ["backend/", "frontend/"]
        self.forbidden_files = [".env", "secrets", "credentials"]
        self.max_file_size = 1024 * 1024  # 1MB

    def _detect_compose_cmd(self) -> str:
        """检测可用的 Docker Compose 命令"""
        import shutil
        if shutil.which("docker-compose"):
            return "docker-compose"
        return "docker compose"

    def _load_error_patterns(self) -> List[Dict[str, Any]]:
        """加载错误模式配置"""
        try:
            if self.error_patterns_file.exists():
                with open(self.error_patterns_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("error_patterns", [])
        except Exception as e:
            logger.error(f"加载错误模式失败: {e}")
        return []

    def to_dict(self) -> Dict[str, Any]:
        """导出配置为字典"""
        return {
            "project_root": str(self.project_root),
            "monitor_mode": self.monitor_mode,
            "max_repairs_per_hour": self.max_repairs_per_hour,
            "cooldown_seconds": self.cooldown_seconds,
            "health_check_url": self.health_check_url,
            "compose_cmd": self.compose_cmd,
            "error_patterns_count": len(self.error_patterns),
        }


_config: Optional[AutoHealConfig] = None


def get_config() -> AutoHealConfig:
    """获取全局配置（单例）"""
    global _config
    if _config is None:
        _config = AutoHealConfig()
    return _config

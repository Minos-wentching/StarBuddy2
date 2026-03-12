"""自动修复系统 (AutoHeal)

监控应用日志，自动检测并修复常见错误。
支持 Docker 容器监控和本地日志文件监控两种模式。
"""

__version__ = "1.1.0"

from .agent import AutoHealAgent, Butler
from .dashboard import Dashboard, print_dashboard
from .config import AutoHealConfig, get_config
from .strategies import RepairStrategyFactory, repair_error

__all__ = [
    "AutoHealAgent",
    "Butler",
    "Dashboard",
    "print_dashboard",
    "AutoHealConfig",
    "get_config",
    "RepairStrategyFactory",
    "repair_error",
]

"""
监控仪表板

提供自动修复系统的实时监控界面。
修复了成功率计算 bug：add_repair_result 后立即重算衍生指标。
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)

DASHBOARD_DIR = Path(__file__).parent
HISTORY_FILE = DASHBOARD_DIR / "dashboard_history.json"


class Dashboard:
    """监控仪表板"""

    def __init__(self):
        self.start_time = time.time()
        self.errors_detected = 0
        self.errors_repaired = 0
        self.errors_failed = 0
        self.repair_history: List[Dict[str, Any]] = []
        self.active_errors: List[Dict[str, Any]] = []
        self._load_history()

    def _load_history(self):
        """加载历史记录"""
        try:
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.repair_history = data.get("history", [])
                self.errors_detected = data.get("errors_detected", 0)
                self.errors_repaired = data.get("errors_repaired", 0)
                self.errors_failed = data.get("errors_failed", 0)
        except Exception as e:
            logger.error(f"加载仪表板历史失败: {e}")

    def _save_history(self):
        """保存历史记录"""
        try:
            data = {
                "history": self.repair_history[-100:],
                "errors_detected": self.errors_detected,
                "errors_repaired": self.errors_repaired,
                "errors_failed": self.errors_failed,
                "last_updated": datetime.now().isoformat(),
            }
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存仪表板历史失败: {e}")

    def add_error(self, error_info: Dict[str, Any]):
        """记录检测到的错误"""
        self.errors_detected += 1
        self.active_errors.append({
            **error_info,
            "detected_at": datetime.now().isoformat(),
        })

    def add_repair_result(self, error_info: Dict[str, Any], result: Dict[str, Any]):
        """记录修复结果"""
        success = result.get("success", False)
        if success:
            self.errors_repaired += 1
        else:
            self.errors_failed += 1

        record = {
            "error_type": error_info.get("type", "UNKNOWN"),
            "error_message": error_info.get("message", "")[:200],
            "success": success,
            "action": result.get("action", ""),
            "reason": result.get("reason", ""),
            "timestamp": datetime.now().isoformat(),
        }
        self.repair_history.append(record)

        # 从活跃错误中移除
        self.active_errors = [
            e for e in self.active_errors
            if e.get("message") != error_info.get("message")
        ]

        self._save_history()

    @property
    def success_rate(self) -> float:
        """计算修复成功率"""
        total = self.errors_repaired + self.errors_failed
        if total == 0:
            return 0.0
        return self.errors_repaired / total * 100

    @property
    def uptime(self) -> str:
        """计算运行时间"""
        elapsed = time.time() - self.start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def get_status(self) -> Dict[str, Any]:
        """获取仪表板状态"""
        return {
            "uptime": self.uptime,
            "errors_detected": self.errors_detected,
            "errors_repaired": self.errors_repaired,
            "errors_failed": self.errors_failed,
            "success_rate": f"{self.success_rate:.1f}%",
            "active_errors": len(self.active_errors),
            "recent_repairs": self.repair_history[-5:],
        }

    def get_report(self, hours: int = 24) -> Dict[str, Any]:
        """生成报告"""
        cutoff = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff.isoformat()

        recent = [
            r for r in self.repair_history
            if r.get("timestamp", "") >= cutoff_str
        ]

        # 按错误类型统计
        by_type: Dict[str, Dict[str, int]] = {}
        for r in recent:
            t = r.get("error_type", "UNKNOWN")
            if t not in by_type:
                by_type[t] = {"total": 0, "success": 0, "failed": 0}
            by_type[t]["total"] += 1
            if r.get("success"):
                by_type[t]["success"] += 1
            else:
                by_type[t]["failed"] += 1

        return {
            "period_hours": hours,
            "total_repairs": len(recent),
            "successful": sum(1 for r in recent if r.get("success")),
            "failed": sum(1 for r in recent if not r.get("success")),
            "by_type": by_type,
        }


def print_dashboard(dashboard: Optional[Dashboard] = None):
    """打印仪表板状态"""
    if dashboard is None:
        dashboard = Dashboard()

    status = dashboard.get_status()
    print("\n" + "=" * 50)
    print("  AutoHeal 监控仪表板")
    print("=" * 50)
    print(f"  运行时间:   {status['uptime']}")
    print(f"  检测错误:   {status['errors_detected']}")
    print(f"  修复成功:   {status['errors_repaired']}")
    print(f"  修复失败:   {status['errors_failed']}")
    print(f"  成功率:     {status['success_rate']}")
    print(f"  活跃错误:   {status['active_errors']}")
    print("=" * 50)

    if status["recent_repairs"]:
        print("\n  最近修复:")
        for r in status["recent_repairs"]:
            icon = "✓" if r.get("success") else "✗"
            print(f"    {icon} [{r.get('error_type')}] {r.get('action') or r.get('reason', '')[:50]}")

    print()

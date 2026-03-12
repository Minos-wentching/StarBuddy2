"""
配置验证工具
"""

import logging
from typing import Dict, Any
from ..api_config import config

logger = logging.getLogger(__name__)


class ConfigValidator:
    """配置验证器"""

    @staticmethod
    def validate_all() -> Dict[str, Any]:
        """验证所有关键配置"""
        results = {
            "database": ConfigValidator.validate_database(),
            "auth": ConfigValidator.validate_auth(),
            "external_apis": ConfigValidator.validate_external_apis(),
            "thresholds": ConfigValidator.validate_thresholds(),
            "storage": ConfigValidator.validate_storage(),
        }

        # 检查是否有严重错误
        has_critical_errors = any(
            result.get("status") == "error" and result.get("critical", False)
            for result in results.values()
        )

        return {
            "overall_status": "error" if has_critical_errors else "ok",
            "results": results,
            "environment": config.ENVIRONMENT,
        }

    @staticmethod
    def validate_database() -> Dict[str, Any]:
        """验证数据库配置"""
        try:
            # 检查数据库URL格式
            if not config.DATABASE_URL:
                return {
                    "status": "error",
                    "critical": True,
                    "message": "DATABASE_URL不能为空",
                }

            # 生产环境建议使用PostgreSQL
            if config.is_production and config.DATABASE_URL.startswith("sqlite"):
                return {
                    "status": "warning",
                    "critical": False,
                    "message": "生产环境建议使用PostgreSQL而非SQLite",
                }

            return {"status": "ok", "message": "数据库配置有效"}

        except Exception as e:
            return {"status": "error", "critical": True, "message": str(e)}

    @staticmethod
    def validate_auth() -> Dict[str, Any]:
        """验证认证配置"""
        try:
            # 检查密钥（从DASHSCOPE_API_KEY环境变量读取）
            if not config.SECRET_KEY:
                if config.is_production:
                    return {
                        "status": "error",
                        "critical": True,
                        "message": "生产环境必须通过DASHSCOPE_API_KEY环境变量设置安全密钥",
                    }
                else:
                    return {
                        "status": "warning",
                        "critical": False,
                        "message": "开发环境未设置DASHSCOPE_API_KEY，将使用自动生成的密钥",
                    }

            # 检查JWT配置
            if not config.ALGORITHM:
                return {"status": "error", "critical": True, "message": "ALGORITHM不能为空"}

            if config.ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
                return {
                    "status": "error",
                    "critical": True,
                    "message": "ACCESS_TOKEN_EXPIRE_MINUTES必须大于0",
                }

            return {"status": "ok", "message": "认证配置有效"}

        except Exception as e:
            return {"status": "error", "critical": True, "message": str(e)}

    @staticmethod
    def validate_external_apis() -> Dict[str, Any]:
        """验证外部API配置"""
        results = []

        # 检查DashScope API密钥
        apis_to_check = [
            ("情绪分析", config.DASHSCOPE_EMOTION_API_KEY, config.DASHSCOPE_EMOTION_URL),
            ("对话生成", config.DASHSCOPE_DIALOGUE_API_KEY, config.DASHSCOPE_DIALOGUE_URL),
            ("视频生成", config.DASHSCOPE_API_KEY, config.DASHSCOPE_VIDEO_URL),
        ]

        for api_name, api_key, api_url in apis_to_check:
            if not api_key:
                results.append(
                    {
                        "api": api_name,
                        "status": "warning",
                        "message": f"{api_name} API密钥未设置，相关功能将不可用",
                    }
                )
            elif not api_url:
                results.append(
                    {
                        "api": api_name,
                        "status": "error",
                        "critical": False,
                        "message": f"{api_name} API URL未设置",
                    }
                )
            else:
                results.append(
                    {"api": api_name, "status": "ok", "message": f"{api_name}配置有效"}
                )

        # 检查是否有严重错误
        has_critical_errors = any(
            r.get("status") == "error" and r.get("critical", False) for r in results
        )

        return {
            "status": "error" if has_critical_errors else "ok",
            "apis": results,
            "message": "外部API配置检查完成",
        }

    @staticmethod
    def validate_thresholds() -> Dict[str, Any]:
        """验证人格切换阈值配置"""
        try:
            thresholds = config.get_persona_thresholds()

            # 检查阈值范围
            for name, value in thresholds.items():
                if not 0.0 <= value <= 1.0:
                    return {
                        "status": "error",
                        "critical": True,
                        "message": f"阈值 {name}={value} 必须在0.0到1.0之间",
                    }

            # 检查逻辑一致性
            if thresholds["exiles"] <= thresholds["calm"]:
                return {
                    "status": "warning",
                    "critical": False,
                    "message": "Exiles阈值应大于平静阈值以保证状态切换",
                }

            if thresholds["firefighters"] <= thresholds["calm"]:
                return {
                    "status": "warning",
                    "critical": False,
                    "message": "Firefighters阈值应大于平静阈值以保证状态切换",
                }

            return {"status": "ok", "message": "阈值配置有效", "thresholds": thresholds}

        except Exception as e:
            return {"status": "error", "critical": True, "message": str(e)}

    @staticmethod
    def validate_storage() -> Dict[str, Any]:
        """验证存储配置"""
        try:
            # 检查ChromaDB存储路径
            if not config.CHROMA_PERSIST_DIR:
                return {
                    "status": "error",
                    "critical": True,
                    "message": "CHROMA_PERSIST_DIR不能为空",
                }

            # 检查会话配置
            if config.SESSION_TIMEOUT_MINUTES <= 0:
                return {
                    "status": "error",
                    "critical": True,
                    "message": "SESSION_TIMEOUT_MINUTES必须大于0",
                }

            if config.MAX_SESSIONS_PER_USER <= 0:
                return {
                    "status": "error",
                    "critical": True,
                    "message": "MAX_SESSIONS_PER_USER必须大于0",
                }

            # 检查版本存档配置
            if config.SNAPSHOT_INTERVAL_MESSAGES <= 0:
                return {
                    "status": "error",
                    "critical": True,
                    "message": "SNAPSHOT_INTERVAL_MESSAGES必须大于0",
                }

            if config.MAX_SNAPSHOTS_PER_SESSION <= 0:
                return {
                    "status": "error",
                    "critical": True,
                    "message": "MAX_SNAPSHOTS_PER_SESSION必须大于0",
                }

            return {"status": "ok", "message": "存储配置有效"}

        except Exception as e:
            return {"status": "error", "critical": True, "message": str(e)}


def log_config_summary():
    """记录配置摘要"""

    logger.info("=== Inner Mirror 配置摘要 ===")
    logger.info(f"应用: {config.APP_NAME} v{config.APP_VERSION}")
    logger.info(f"环境: {config.ENVIRONMENT}")
    logger.info(f"日志级别: {config.LOG_LEVEL}")

    # 数据库信息（隐藏密码）
    db_url = config.DATABASE_URL
    if "@" in db_url:
        # 隐藏密码
        parts = db_url.split("@")
        if ":" in parts[0]:
            protocol_auth = parts[0].split(":")
            if len(protocol_auth) > 2:
                # 格式: postgresql://user:password@host/db
                protocol_auth[2] = "***"
                db_url = ":".join(protocol_auth) + "@" + parts[1]
    logger.info(f"数据库: {db_url}")

    # 人格阈值
    thresholds = config.get_persona_thresholds()
    logger.info(f"人格阈值: {thresholds}")

    # 外部API状态
    emotion_configured = bool(config.DASHSCOPE_EMOTION_API_KEY)
    dialogue_configured = bool(config.DASHSCOPE_DIALOGUE_API_KEY)
    video_configured = bool(config.DASHSCOPE_API_KEY)

    logger.info(f"情绪分析API: {'已配置' if emotion_configured else '未配置'}")
    logger.info(f"对话生成API: {'已配置' if dialogue_configured else '未配置'}")
    logger.info(f"视频生成API: {'已配置' if video_configured else '未配置'}")

    # 验证配置
    validation_result = ConfigValidator.validate_all()
    if validation_result["overall_status"] == "error":
        logger.error("配置验证失败，请检查以下问题:")
        for category, result in validation_result["results"].items():
            if result["status"] == "error":
                logger.error(f"  {category}: {result['message']}")
            elif result["status"] == "warning":
                logger.warning(f"  {category}: {result['message']}")
    else:
        logger.info("配置验证通过")

    logger.info("=== 配置摘要结束 ===")


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    log_config_summary()
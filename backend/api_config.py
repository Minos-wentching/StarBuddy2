"""
Inner Mirror 集中配置管理系统

统一管理所有API密钥、模型参数、人格切换阈值等配置。
支持环境变量注入，便于魔塔创空间Secret管理。
"""

import os
import secrets
import warnings
import hashlib
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class APIConfig(BaseSettings):
    """主配置类"""

    # ==================== 基础配置 ====================
    # 应用名称和版本
    APP_NAME: str = "Inner Mirror"
    APP_VERSION: str = "1.0.0"

    # 环境
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    # CORS配置
    ALLOWED_ORIGINS: str = Field(
        default="",
        env="ALLOWED_ORIGINS",
        description="允许的CORS来源，多个用逗号分隔。留空时由运行环境决定（开发环境放开，生产环境仅同源）。"
    )

    # 日志级别
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # ==================== 数据库配置 ====================
    DATABASE_URL: str = Field(
        default="sqlite:///./data/inner_mirror.db",
        env="DATABASE_URL"
    )

    # ==================== JWT认证配置 ====================
    SECRET_KEY: str = Field(
        default="",  # 从SECRET_KEY环境变量读取，如果没有则使用DASHSCOPE_API_KEY或自动生成
        env="SECRET_KEY"
    )
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=240, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # ==================== DashScope API配置 ====================
    DASHSCOPE_API_KEY: str = Field(default="", env="DASHSCOPE_API_KEY")
    DASHSCOPE_BASE_URL: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        env="DASHSCOPE_BASE_URL"
    )

    # 情绪分析API配置
    # 使用统一的DASHSCOPE_API_KEY
    DASHSCOPE_EMOTION_API_KEY: str = Field(
        default="",
        env="DASHSCOPE_API_KEY"
    )
    DASHSCOPE_EMOTION_URL: str = Field(
        default="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        env="DASHSCOPE_EMOTION_URL"
    )
    DASHSCOPE_EMOTION_MODEL: str = Field(
        default="qwen-plus",
        env="DASHSCOPE_EMOTION_MODEL"
    )

    # 对话生成API配置
    # 使用统一的DASHSCOPE_API_KEY
    DASHSCOPE_DIALOGUE_API_KEY: str = Field(
        default="",
        env="DASHSCOPE_API_KEY"
    )
    DASHSCOPE_DIALOGUE_URL: str = Field(
        default="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        env="DASHSCOPE_DIALOGUE_URL"
    )
    DASHSCOPE_DIALOGUE_MODEL: str = Field(
        default="qwen-max",
        env="DASHSCOPE_DIALOGUE_MODEL"
    )

    # ==================== 对话模型（OpenAI 兼容）多提供方配置 ====================
    DIALOGUE_PROVIDER: str = Field(
        default="",
        env="DIALOGUE_PROVIDER",
        description="对话模型提供方：deepseek|dashscope。留空自动选择（优先 deepseek，其次 dashscope）。"
    )
    DIALOGUE_API_TIMEOUT_SECONDS: int = Field(
        default=45,
        ge=5,
        le=300,
        env="DIALOGUE_API_TIMEOUT_SECONDS",
        description="对话 API 超时时间（秒）。"
    )
    DIALOGUE_API_MAX_RETRIES: int = Field(
        default=1,
        ge=0,
        le=5,
        env="DIALOGUE_API_MAX_RETRIES",
        description="对话 API 最大重试次数（OpenAI SDK 的 max_retries）。"
    )

    # DeepSeek（OpenAI 兼容）
    DEEPSEEK_API_KEY: str = Field(default="", env="DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com/v1", env="DEEPSEEK_BASE_URL")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat", env="DEEPSEEK_MODEL")

    # 意象绘图/图像生成API配置
    # 使用统一的DASHSCOPE_API_KEY
    DASHSCOPE_VIDEO_URL: str = Field(
        default="https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
        env="DASHSCOPE_VIDEO_URL"
    )
    DASHSCOPE_VIDEO_MODEL: str = Field(
        default="z-image-turbo",
        env="DASHSCOPE_VIDEO_MODEL"
    )

    # ==================== 人格切换阈值配置 ====================
    EXILES_THRESHOLD: float = Field(default=0.7, ge=0.0, le=1.0, env="EXILES_THRESHOLD")
    FIREFIGHTERS_THRESHOLD: float = Field(default=0.7, ge=0.0, le=1.0, env="FIREFIGHTERS_THRESHOLD")
    LEGACY_ID_THRESHOLD: Optional[float] = Field(default=None, ge=0.0, le=1.0, env="ID_THRESHOLD")
    LEGACY_SUPEREGO_THRESHOLD: Optional[float] = Field(default=None, ge=0.0, le=1.0, env="SUPEREGO_THRESHOLD")
    CALM_THRESHOLD: float = Field(default=0.3, ge=0.0, le=1.0, env="CALM_THRESHOLD")
    COUNCIL_TRIGGER_RATIO: float = Field(default=0.5, ge=0.0, le=1.0, env="COUNCIL_TRIGGER_RATIO")
    
    # Multiego 兼容配置
    INTENSITY_SWITCH_THRESHOLD: float = Field(default=0.7, env="INTENSITY_SWITCH_THRESHOLD")
    INTENSITY_RETURN_THRESHOLD: float = Field(default=0.67, env="INTENSITY_RETURN_THRESHOLD")
    INTENSITY_DECAY_RATE: float = Field(default=0.08, env="INTENSITY_DECAY_RATE")
    COUNCIL_NEGOTIATION_ROUNDS: int = Field(default=1, env="COUNCIL_NEGOTIATION_ROUNDS")
    MAX_PERSONA_TURNS: int = Field(default=5, env="MAX_PERSONA_TURNS")
    HEALING_MILESTONE_THRESHOLD: float = Field(default=3.0, env="HEALING_MILESTONE_THRESHOLD")

    # ==================== 情绪衰减率配置 ====================
    EMOTION_DECAY_RATE: float = Field(default=0.05, gt=0.0, le=1.0, env="EMOTION_DECAY_RATE")
    EMOTION_HISTORY_SIZE: int = Field(default=100, env="EMOTION_HISTORY_SIZE")

    # ==================== ChromaDB配置 ====================
    CHROMA_PERSIST_DIR: str = Field(
        default="./chroma_storage",
        env="CHROMA_PERSIST_DIR"
    )
    CHROMA_COLLECTION_NAME: str = Field(
        default="inner_mirror_memories",
        env="CHROMA_COLLECTION_NAME"
    )
    ANONYMIZED_TELEMETRY: bool = Field(
        default=False,
        env="ANONYMIZED_TELEMETRY"
    )

    # ==================== Embedding 模型配置 ====================
    EMBEDDING_MODEL: str = Field(
        default="AI-ModelScope/all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL"
    )
    EMBEDDING_CACHE_DIR: str = Field(
        default="./data/embedding_cache",
        env="EMBEDDING_CACHE_DIR"
    )

    # ==================== SSE配置 ====================
    SSE_HEARTBEAT_INTERVAL: int = Field(default=30, env="SSE_HEARTBEAT_INTERVAL")
    SSE_RECONNECT_TIMEOUT: int = Field(default=5000, env="SSE_RECONNECT_TIMEOUT")

    # ==================== 本地 LLM（免 API Key，可选） ====================
    LOCAL_LLM_PROVIDER: str = Field(
        default="",
        env="LOCAL_LLM_PROVIDER",
        description="本地 LLM 提供方：ollama|none。留空表示仅在缺少 DASHSCOPE_API_KEY 时尝试使用 ollama。"
    )
    OLLAMA_BASE_URL: str = Field(default="http://127.0.0.1:11434", env="OLLAMA_BASE_URL")
    OLLAMA_MODEL: str = Field(default="qwen2.5:7b", env="OLLAMA_MODEL")

    # ==================== 魔塔免费额度配置 ====================
    MODEL_SCOPE_MAX_REQUESTS_PER_DAY: int = Field(default=1000, env="MODEL_SCOPE_MAX_REQUESTS_PER_DAY")
    MODEL_SCOPE_RATE_LIMIT_PER_MINUTE: int = Field(default=10, env="MODEL_SCOPE_RATE_LIMIT_PER_MINUTE")

    # ==================== 会话配置 ====================
    SESSION_TIMEOUT_MINUTES: int = Field(default=60, env="SESSION_TIMEOUT_MINUTES")
    MAX_SESSIONS_PER_USER: int = Field(default=5, env="MAX_SESSIONS_PER_USER")

    # ==================== 版本存档配置 ====================
    SNAPSHOT_INTERVAL_MESSAGES: int = Field(default=10, env="SNAPSHOT_INTERVAL_MESSAGES")
    MAX_SNAPSHOTS_PER_SESSION: int = Field(default=100, env="MAX_SNAPSHOTS_PER_SESSION")

    # ==================== 自动修复监控配置 ====================
    AUTOHEAL_ENABLED: bool = Field(default=False, env="AUTOHEAL_ENABLED")
    AUTOHEAL_CONTAINER_NAME: str = Field(default="backend", env="AUTOHEAL_CONTAINER_NAME")
    AUTOHEAL_HEALTH_CHECK_URL: str = Field(
        default="http://localhost:8000/health",
        env="AUTOHEAL_HEALTH_CHECK_URL"
    )
    AUTOHEAL_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=10, env="AUTOHEAL_MAX_ATTEMPTS")
    AUTOHEAL_POLL_INTERVAL: int = Field(default=1, ge=1, le=60, env="AUTOHEAL_POLL_INTERVAL")
    AUTOHEAL_LOG_LEVEL: str = Field(default="INFO", env="AUTOHEAL_LOG_LEVEL")
    AUTOHEAL_NOTIFICATION_ENABLED: bool = Field(default=False, env="AUTOHEAL_NOTIFICATION_ENABLED")

    # ==================== 验证器 ====================
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        allowed = ["development", "testing", "production"]
        if v not in allowed:
            raise ValueError(f"环境必须是以下之一: {allowed}")
        return v

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"日志级别必须是以下之一: {allowed}")
        return v.upper()

    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL不能为空")
        return v

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v, values):
        import stat
        import time

        # 获取环境，优先使用values中的值，其次使用环境变量
        environment = values.get("ENVIRONMENT") or os.environ.get("ENVIRONMENT", "development")

        # 显式提供则直接使用
        if v:
            return v

        # 兼容：用 DASHSCOPE_API_KEY 派生稳定密钥（适配 ModelScope/多副本场景）
        # 注意：不直接复用明文 API Key，而是做一次哈希派生。
        dashscope_key = (os.environ.get("DASHSCOPE_API_KEY") or "").strip()
        if dashscope_key:
            derived = hashlib.sha256(f"inner-mirror-jwt:{dashscope_key}".encode("utf-8")).hexdigest()
            return derived

        # 兜底：从持久化文件读取或生成随机密钥
        if environment == "production":
            warnings.warn(
                "⚠️  生产环境未设置 SECRET_KEY/DASHSCOPE_API_KEY，将自动生成并持久化。"
                "强烈建议通过环境变量设置 SECRET_KEY 以确保安全与多副本一致性。",
                UserWarning
            )
        else:
            warnings.warn(
                "⚠️  未设置 SECRET_KEY/DASHSCOPE_API_KEY，将自动生成并持久化 SECRET_KEY。",
                UserWarning
            )

        # 默认写入 /app/data/.secret_key（本项目约定的持久化目录），避免写到代码目录导致重部署失效。
        app_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
        data_dir = os.path.join(app_dir, "data")
        key_file = os.path.join(data_dir, ".secret_key")

        try:
            os.makedirs(data_dir, exist_ok=True)
        except Exception:
            # 如果无法创建 data 目录，回退到 backend 目录
            key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".secret_key")

        if os.path.exists(key_file):
            try:
                with open(key_file, "r") as f:
                    persisted_key = f.read().strip()
                if persisted_key:
                    return persisted_key
            except Exception:
                pass

        # 多进程/多副本启动时，避免各进程各自生成不同 SECRET_KEY 导致 JWT 签名不一致。
        # 使用原子创建（O_EXCL）保证只有一个进程负责生成，其它进程读取同一份持久化密钥。
        random_key = secrets.token_urlsafe(32)
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            fd = os.open(key_file, flags, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(random_key)

            try:
                os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
            except Exception:
                # chmod 失败不影响功能（某些文件系统不支持）
                pass

            warnings.warn(
                f"已自动生成并持久化 SECRET_KEY 到 {key_file}。",
                UserWarning
            )
            return random_key

        except FileExistsError:
            # 其他进程已生成，等待其写入完成后读取。
            for _ in range(8):
                try:
                    with open(key_file, "r") as f:
                        persisted_key = f.read().strip()
                    if persisted_key:
                        return persisted_key
                except Exception:
                    pass
                time.sleep(0.05)

            warnings.warn(
                f"SECRET_KEY 文件已存在但读取失败，将使用临时密钥（多进程可能导致令牌失效）。path={key_file}",
                UserWarning
            )
            return random_key

        except Exception:
            warnings.warn(
                f"无法持久化 SECRET_KEY 到文件，将使用临时密钥（重启/重部署后令牌将失效）。path={key_file}",
                UserWarning
            )
            return random_key

    # ==================== 计算属性 ====================
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def allowed_origins_list(self) -> list[str]:
        """解析ALLOWED_ORIGINS字符串为列表"""
        if not self.ALLOWED_ORIGINS:
            return []
        # 按逗号分割，去除空格，过滤空值
        origins = [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        return [origin for origin in origins if origin]

    @property
    def dashscope_emotion_headers(self) -> Dict[str, str]:
        """DashScope情绪分析API请求头"""
        return {
            "Authorization": f"Bearer {self.DASHSCOPE_EMOTION_API_KEY}",
            "Content-Type": "application/json"
        }

    @property
    def dashscope_dialogue_headers(self) -> Dict[str, str]:
        """DashScope对话生成API请求头"""
        return {
            "Authorization": f"Bearer {self.DASHSCOPE_DIALOGUE_API_KEY}",
            "Content-Type": "application/json"
        }

    @property
    def dashscope_video_headers(self) -> Dict[str, str]:
        """DashScope视频生成API请求头"""
        return {
            "Authorization": f"Bearer {self.DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }

    @property
    def ID_THRESHOLD(self) -> float:
        """兼容旧命名：优先使用旧环境变量值，否则回退到 EXILES_THRESHOLD。"""
        return self.LEGACY_ID_THRESHOLD if self.LEGACY_ID_THRESHOLD is not None else self.EXILES_THRESHOLD

    @property
    def SUPEREGO_THRESHOLD(self) -> float:
        """兼容旧命名：优先使用旧环境变量值，否则回退到 FIREFIGHTERS_THRESHOLD。"""
        return self.LEGACY_SUPEREGO_THRESHOLD if self.LEGACY_SUPEREGO_THRESHOLD is not None else self.FIREFIGHTERS_THRESHOLD

    def get_persona_thresholds(self) -> Dict[str, float]:
        """获取人格切换阈值配置"""
        return {
            "exiles": self.EXILES_THRESHOLD,
            "firefighters": self.FIREFIGHTERS_THRESHOLD,
            "calm": self.CALM_THRESHOLD,
            "council_trigger": self.COUNCIL_TRIGGER_RATIO
        }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例
config = APIConfig()


def get_config() -> APIConfig:
    """获取配置实例（用于依赖注入）"""
    return config


if __name__ == "__main__":
    # 测试配置加载
    print(f"应用: {config.APP_NAME} v{config.APP_VERSION}")
    print(f"环境: {config.ENVIRONMENT}")
    print(f"数据库: {config.DATABASE_URL}")
    print(f"人格阈值: {config.get_persona_thresholds()}")

    # 检查关键配置
    if not config.DASHSCOPE_API_KEY:
        print("警告: DASHSCOPE_API_KEY 未设置（所有服务将无法工作）")
    if not config.DASHSCOPE_EMOTION_API_KEY:
        print("警告: DASHSCOPE_EMOTION_API_KEY 未设置")
    if not config.DASHSCOPE_DIALOGUE_API_KEY:
        print("警告: DASHSCOPE_DIALOGUE_API_KEY 未设置")
    if not config.SECRET_KEY and config.is_production:
        print("错误: 生产环境必须通过DASHSCOPE_API_KEY环境变量设置安全密钥")

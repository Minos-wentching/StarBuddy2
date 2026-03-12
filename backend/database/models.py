"""
SQLAlchemy 数据库模型
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .database import Base


def generate_uuid():
    """生成UUID"""
    return str(uuid.uuid4())


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    settings = Column(JSON, default=dict)  # 用户个性化设置
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """用户会话模型"""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(255), unique=True, index=True, nullable=False)

    # 会话状态
    current_persona = Column(String(50), default="manager")
    emotion_intensity = Column(Float, default=0.0)
    emotion_history = Column(JSON, default=list)  # 情绪历史记录
    persona_state = Column(JSON, default=dict)    # 完整人格状态

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # 关系
    user = relationship("User", back_populates="sessions")
    snapshots = relationship("Snapshot", back_populates="session", cascade="all, delete-orphan")
    councils = relationship("Council", back_populates="session", cascade="all, delete-orphan")


class Snapshot(Base):
    """版本快照模型"""
    __tablename__ = "snapshots"

    id = Column(String(64), primary_key=True)  # 版本哈希
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)

    # 快照数据
    state_data = Column(JSON, nullable=False)  # 完整状态数据
    meta_data = Column(JSON, nullable=False)    # 元数据
    parent_hash = Column(String(64), nullable=True)  # 父版本哈希（用于版本树）

    # 标签和分类
    tags = Column(JSON, default=list)
    persona = Column(String(50))
    emotion_intensity = Column(Float)
    message_count = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    session = relationship("Session", back_populates="snapshots")


class Council(Base):
    """内心议会记录模型"""
    __tablename__ = "councils"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)

    # 议会数据
    debate_data = Column(JSON, nullable=False)  # 完整辩论数据
    conclusion = Column(Text)                   # Counselor整合结论
    rounds = Column(Integer, default=0)         # 辩论轮数
    status = Column(String(20), default="active")  # active, completed, failed

    # 参与者表现
    id_performance = Column(JSON, default=dict)      # Exiles 表现数据（兼容旧字段名）
    superego_performance = Column(JSON, default=dict) # Firefighters 表现数据（兼容旧字段名）

    # 时间戳
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # 关系
    session = relationship("Session", back_populates="councils")


class DialogueHistory(Base):
    """对话历史模型"""
    __tablename__ = "dialogue_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)

    # 对话内容
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    persona = Column(String(50), nullable=False)  # 响应的人格

    # 情绪数据
    emotion_intensity = Column(Float)
    emotion_analysis = Column(JSON, default=dict)

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)

    # 索引
    __table_args__ = (
        Index('idx_session_created', 'session_id', 'created_at'),
    )


class SystemMetrics(Base):
    """系统指标模型"""
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # 使用统计
    total_users = Column(Integer, default=0)
    active_sessions = Column(Integer, default=0)
    total_dialogues = Column(Integer, default=0)
    total_councils = Column(Integer, default=0)

    # API使用
    dashscope_requests = Column(Integer, default=0)
    dashscope_errors = Column(Integer, default=0)

    # 性能指标
    avg_response_time = Column(Float, default=0.0)
    error_rate = Column(Float, default=0.0)

    # 时间戳
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    period = Column(String(20))  # hourly, daily, weekly


class Memory(Base):
    """记忆模型（LLM 提取式 RAG）"""
    __tablename__ = "memories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(100), index=True, nullable=False)
    session_id = Column(String(36), index=True, nullable=True)
    content = Column(Text, nullable=False)
    memory_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class HealingImage(Base):
    """疗愈相册图片模型"""
    __tablename__ = "healing_images"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(Text)
    diary_text = Column(Text)
    persona = Column(String(50))
    feedback = Column(Text, nullable=True)  # 用户对日记的反馈（追加模式）
    core_belief_ref = Column(String(50), nullable=True)  # 关联的核心信念 ID
    created_at = Column(DateTime, default=datetime.utcnow)


class DriftBottle(Base):
    """漂流瓶模型"""
    __tablename__ = "drift_bottles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    persona_type = Column(String(50), nullable=False)  # exiles / firefighters
    persona_portrait = Column(Text, default="")
    diary_text = Column(Text, default="")
    message = Column(Text, default="")
    status = Column(String(20), default="drifting")  # drifting, picked
    created_at = Column(DateTime, default=datetime.utcnow)
    picked_at = Column(DateTime, nullable=True)


# 创建索引
from sqlalchemy import Index
Index('idx_session_token', Session.session_token)
Index('idx_session_user', Session.user_id)
Index('idx_snapshot_session', Snapshot.session_id)
Index('idx_snapshot_created', Snapshot.created_at)
Index('idx_council_session', Council.session_id)
Index('idx_dialogue_session', DialogueHistory.session_id)
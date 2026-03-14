"""
Pydantic 数据模式

用于请求验证和响应序列化
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, AliasChoices, ConfigDict


# ==================== 枚举 (移植自 Multiego models.py) ====================

class AgentRole(str, Enum):
    """Agent 角色枚举"""
    COUNSELOR = "counselor"
    MANAGER = "manager"
    EXILES = "exiles"
    FIREFIGHTERS = "firefighters"


class SessionPhase(str, Enum):
    """会话阶段枚举 (移植自 Multiego models.py)"""
    INTAKE = "intake"                   # 用户输入 / 对话
    ANALYSIS = "analysis"               # Counselor 分析
    DECISION = "decision"               # Manager 决策
    NEGOTIATION = "negotiation"         # 内心议会博弈
    PERSONALITY_TAKEOVER = "takeover"   # 次人格占据
    DIARY_WRITING = "diary_writing"     # 日记撰写 + 图像生成
    FEEDBACK = "feedback"               # 用户反馈
    SAVE_BLOCK = "save_block"           # 阶段性存档


# ==================== 基础模式 ====================
class Token(BaseModel):
    """JWT令牌响应"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """令牌数据"""
    user_id: Optional[int] = None
    username: Optional[str] = None


# ==================== 用户相关模式 ====================
class UserBase(BaseModel):
    """用户基础信息"""
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    """用户创建请求（仅用户名）"""
    pass


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str


class QuickLoginRequest(BaseModel):
    """快速登录请求（仅用户名）"""
    username: str = Field(..., min_length=3, max_length=50)


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str


class UserResponse(UserBase):
    """用户响应"""
    id: int
    is_active: bool
    settings: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """用户更新请求"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    settings: Optional[Dict[str, Any]] = None


# ==================== 用户端（孤独症患者端）设置 ====================
class PatientProfile(BaseModel):
    """用户端档案（用于引导页展示/存储的名字）"""
    display_name: str = Field("", max_length=50)


class PatientProfileUpdate(BaseModel):
    """更新用户端档案"""
    display_name: str = Field(..., min_length=1, max_length=50)


class PatientTheme(BaseModel):
    """用户端主题设置"""
    baseColor: str = Field("#0B1B3A", min_length=4, max_length=32)
    enableTransition: bool = False
    transitionToColor: Optional[str] = Field(None, min_length=4, max_length=32)
    transitionDurationSec: int = Field(30, ge=1, le=600)

    model_config = ConfigDict(extra="forbid")


class PatientSettings(BaseModel):
    """用户端设置：指令列表与主题"""
    instructions: List[str] = Field(default_factory=list)
    theme: PatientTheme = Field(default_factory=PatientTheme)

    model_config = ConfigDict(extra="forbid")


class PatientSettingsUpdate(BaseModel):
    """更新用户端设置"""
    instructions: List[str] = Field(default_factory=list)
    theme: PatientTheme = Field(default_factory=PatientTheme)

    model_config = ConfigDict(extra="forbid")


# ==================== 会话相关模式 ====================
class SessionBase(BaseModel):
    """会话基础信息"""
    current_persona: str = "manager"
    emotion_intensity: float = Field(0.0, ge=0.0, le=1.0)


class SessionCreate(BaseModel):
    """会话创建请求"""
    session_name: Optional[str] = None


class SessionResponse(BaseModel):
    """会话响应"""
    id: str
    user_id: int
    current_persona: str
    emotion_intensity: float
    is_active: bool
    created_at: datetime
    last_activity: datetime

    class Config:
        from_attributes = True


# ==================== 对话相关模式 ====================
class DialogueMessage(BaseModel):
    """对话消息"""
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: str


class DialogueResponse(BaseModel):
    """对话响应"""
    response: str
    persona: str
    emotion_intensity: float = Field(..., ge=0.0, le=1.0)
    council_active: bool = False
    council_task_id: Optional[str] = None
    version_info: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==================== 内心议会模式 ====================
class CouncilStart(BaseModel):
    """启动议会请求"""
    session_id: str
    topic: str
    max_rounds: int = Field(5, ge=1, le=10)


class CouncilRound(BaseModel):
    """议会轮次"""
    round_number: int
    exiles_argument: str
    firefighters_argument: str
    counselor_analysis: Optional[str] = None


class CouncilResponse(BaseModel):
    """议会响应"""
    council_id: str
    session_id: str
    status: str
    current_round: int
    total_rounds: int
    rounds: List[CouncilRound] = []
    conclusion: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


# ==================== 版本存档模式 ====================
class SnapshotCreate(BaseModel):
    """快照创建请求"""
    session_id: str
    state_data: Dict[str, Any]
    tags: Optional[List[str]] = None


class SnapshotResponse(BaseModel):
    """快照响应"""
    id: str
    session_id: str
    persona: str
    emotion_intensity: float
    message_count: int
    tags: List[str]
    created_at: datetime
    # 兼容历史字段 meta_data，同时对外统一返回 metadata
    meta_data: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("meta_data", "metadata"),
        serialization_alias="metadata",
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class VersionTree(BaseModel):
    """版本树"""
    session_id: str
    snapshots: List[SnapshotResponse]
    branches: Dict[str, List[str]]  # 分支名 -> 版本哈希列表


# ==================== 人格状态模式 ====================
class PersonaState(BaseModel):
    """人格状态"""
    current_persona: str
    persona_changed: bool = False
    trigger_council: bool = False
    emotion_intensity: float = Field(..., ge=0.0, le=1.0)
    switch_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EmotionAnalysis(BaseModel):
    """情绪分析结果"""
    intensity: float = Field(..., ge=0.0, le=1.0)
    dominant_emotion: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    components: Dict[str, float] = {}  # 情绪成分分解


# ==================== 心理分析模式 ====================
class CoreBelief(BaseModel):
    """核心信念 (移植自 Multiego models.py)"""
    belief_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    content: str              # 信念内容，如 "我不值得被爱"
    valence: float = Field(0.0, ge=-1.0, le=1.0)     # 正 / 负极性 [-1, 1]
    intensity: float = Field(5.0, ge=0.0, le=10.0)   # 情感强度 [0, 10]
    origin_event: str = ""   # 溯源事件描述
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def decay(self, amount: float = 0.5) -> None:
        """随疗愈推进，强度衰减 (移植自 Multiego)"""
        self.intensity = max(0.0, self.intensity - amount)
        self.updated_at = datetime.utcnow()


class DiaryEntry(BaseModel):
    """次人格撰写的日记条目 (移植自 Multiego)"""
    entry_id: str = Field(default="")
    author: str  # exiles / firefighters
    text: str
    image_path: Optional[str] = None
    image_url: Optional[str] = None
    feedback: Optional[str] = None
    core_belief_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DiaryFeedbackRequest(BaseModel):
    """日记反馈请求"""
    diary_id: str
    feedback: str


class DiaryResponse(BaseModel):
    """日记响应"""
    id: int
    session_id: str
    author: str
    text: str
    image_url: Optional[str] = None
    feedback: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CounselorReport(BaseModel):
    """心理分析报告"""
    core_beliefs: List[CoreBelief] = []
    intensity_scores: Dict[str, float] = {}
    trigger_event: str = ""
    emotional_summary: str = ""
    raw_analysis: Optional[str] = None

class CouncilUtterance(BaseModel):
    """议会发言"""
    speaker: str  # exiles, firefighters
    content: str
    round_number: int

class CouncilResult(BaseModel):
    """议会最终结果 (移植自 Multiego models.py)"""
    council_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    topic: str
    utterances: List[CouncilUtterance] = []
    counselor_summary: str = ""        # Counselor 的文学化总结
    diary_text: str = ""               # 写入日记的文本
    resolved: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ==================== Manager 决策 (移植自 Multiego models.py) ====================

class ManagerDecision(BaseModel):
    """Manager Agent 的决策输出 (移植自 Multiego models.py)"""
    target_agent: AgentRole            # 应激活哪个次人格
    reasoning: str = ""                # 推理过程
    council_topic: str = ""            # 提交给议会的议题
    events: str = ""                   # 发生人格转换时的事件描述
    character_profile: str = ""        # 目标人格人设描述
    should_save_block: bool = False    # 是否达到阶段性成就
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OnboardingAnswers(BaseModel):
    """首次登录问卷答案"""
    question_1: str = Field(..., min_length=1, max_length=2000)
    question_2: str = Field(..., min_length=1, max_length=2000)


class OnboardingParseRequest(BaseModel):
    """首次登录问卷解析请求"""
    answers: OnboardingAnswers
    session_id: Optional[str] = None


class OnboardingParseResponse(BaseModel):
    """首次登录问卷解析响应"""
    completed: bool = True
    exiles_system_prompt: str
    firefighters_system_prompt: str
    trauma_hypothesis: str = ""
    user_core_info: List[str] = []
    core_beliefs: List[str] = []
    profile_digest: str = ""
    persona_portraits: Dict[str, str] = {}
    profile_version: int = 1
    profile_confirmed: bool = False


class OnboardingArchiveItem(BaseModel):
    """人格画像存档条目"""
    profile_version: int
    created_at: str
    profile_digest: str = ""
    trauma_hypothesis: str = ""
    user_core_info: List[str] = []
    core_beliefs: List[str] = []
    persona_portraits: Dict[str, str] = {}
    profile_confirmed: bool = False


class OnboardingArchiveListResponse(BaseModel):
    """人格画像存档列表响应"""
    current_version: int = 1
    total: int = 0
    archives: List[OnboardingArchiveItem] = []


class OnboardingRestoreRequest(BaseModel):
    """恢复画像版本请求"""
    profile_version: int = Field(..., ge=1)
    session_id: Optional[str] = None


class OnboardingRestoreResponse(BaseModel):
    """恢复画像版本响应"""
    restored: bool = True
    profile_version: int
    profile_confirmed: bool = False
    profile_digest: str = ""
    persona_portraits: Dict[str, str] = {}


# ==================== 用户 Block / 快照 (移植自 Multiego models.py) ====================

class UserBlock(BaseModel):
    """阶段性存档快照 (移植自 Multiego models.py)"""
    block_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    version: int = 1
    parent_version: Optional[int] = None   # Lineage 链
    core_beliefs: List[CoreBelief] = Field(default_factory=list)
    intensity_scores: Dict[str, float] = Field(default_factory=dict)
    diary_entries: List[DiaryEntry] = Field(default_factory=list)
    memory_collection_name: str = ""       # ChromaDB collection 版本快照名
    summary: str = ""                      # 本阶段总结
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ==================== SSE事件模式 ====================
class SSEEvent(BaseModel):
    """SSE事件"""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PersonaSwitchEvent(BaseModel):
    """人格切换事件"""
    persona: str
    intensity: float
    reason: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EmotionUpdateEvent(BaseModel):
    """情绪更新事件"""
    intensity: float
    dominant_emotion: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CouncilUpdateEvent(BaseModel):
    """议会更新事件"""
    council_id: str
    round: int
    total_rounds: int
    arguments: Dict[str, str]  # exiles, firefighters arguments
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==================== 健康检查模式 ====================
class HealthCheck(BaseModel):
    """健康检查响应"""
    status: str
    app: str
    version: str
    environment: str
    database: Optional[Dict[str, Any]] = None
    external_apis: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==================== 错误响应模式 ====================
class ErrorResponse(BaseModel):
    """错误响应"""
    detail: str
    error: Optional[str] = None
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

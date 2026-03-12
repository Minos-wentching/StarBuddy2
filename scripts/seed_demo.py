"""
演示数据填充脚本

用法: python scripts/seed_demo.py
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ.setdefault("DATABASE_URL", "sqlite:///./data/inner_mirror.db")
os.environ.setdefault("SECRET_KEY", "demo-secret-key")
os.environ.setdefault("CHROMA_PERSIST_DIR", "./chroma_storage")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from backend.database.database import Base
from backend.database.models import (
    User, Session, DialogueHistory, Council, HealingImage, generate_uuid
)
from backend.auth.security import create_access_token


async def seed():
    db_path = project_root / "data"
    db_path.mkdir(exist_ok=True)

    engine = create_async_engine(
        "sqlite+aiosqlite:///./data/inner_mirror.db",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        # 检查是否已有 demo 用户
        result = await db.execute(select(User).where(User.username == "demo"))
        existing = result.scalar_one_or_none()
        if existing:
            print("demo 用户已存在，跳过")
            return

        # 1. 创建 demo 用户
        print("创建 demo 用户...")
        user = User(username="demo", is_active=True, settings={})
        db.add(user)
        await db.flush()

        # 2. 创建会话
        print("创建演示会话...")
        session_id = str(uuid.uuid4())
        token = create_access_token({"user_id": user.id, "username": "demo"})
        session = Session(
            id=session_id,
            user_id=user.id,
            session_token=token,
            current_persona="manager",
            emotion_intensity=0.0,
            emotion_history=[],
            persona_state={},
        )
        db.add(session)
        await db.flush()

        # 3. 填充对话记录
        print("填充对话记录...")
        now = datetime.utcnow()
        dialogues = [
            {
                "message": "最近工作压力很大，总觉得自己做不好",
                "response": "我听到你了。工作压力确实会让人感到疲惫和自我怀疑。能告诉我更多关于这种感觉吗？是什么时候开始的？",
                "persona": "manager",
                "emotion_intensity": 0.5,
                "offset_min": 0,
            },
            {
                "message": "我害怕失败，害怕被别人看不起",
                "response": "我好害怕...每次想到可能会失败，心里就像有个小孩在哭泣。我不想被抛弃，不想被看不起。这种恐惧从小就跟着我，像影子一样甩不掉...",
                "persona": "exiles",
                "emotion_intensity": 0.85,
                "offset_min": 3,
            },
            {
                "message": "我知道我不应该这么想，但是控制不了",
                "response": "你不应该这么脆弱。看看别人，谁不是咬着牙在坚持？你需要更加自律，更加努力。这些软弱的想法只会拖累你。",
                "persona": "firefighters",
                "emotion_intensity": 0.82,
                "offset_min": 6,
            },
            {
                "message": "他们之间好像在争吵",
                "response": "【议会辩论已触发】\n\n本我与超我之间存在冲突。本我渴望被接纳和理解，而超我要求完美和自律。让我们通过内心议会来整合这两种声音。",
                "persona": "manager",
                "emotion_intensity": 0.78,
                "offset_min": 9,
            },
            {
                "message": "议会的结论是什么？",
                "response": "通过分析你的对话，我发现了一个核心信念：「我必须完美才值得被爱」。这个信念可能源于早期经历中对认可的渴望。事实上，你的价值不取决于你的表现。允许自己不完美，恰恰是自我接纳的开始。",
                "persona": "counselor",
                "emotion_intensity": 0.6,
                "offset_min": 15,
            },
            {
                "message": "我好像明白了一些",
                "response": "很高兴你有了这样的觉察。认识到内心不同声音的存在，本身就是一种成长。你的本我需要被倾听，你的超我也有它的善意。关键是找到它们之间的平衡。",
                "persona": "manager",
                "emotion_intensity": 0.35,
                "offset_min": 18,
            },
        ]

        for d in dialogues:
            entry = DialogueHistory(
                session_id=session_id,
                message=d["message"],
                response=d["response"],
                persona=d["persona"],
                emotion_intensity=d["emotion_intensity"],
                emotion_analysis={"dominant_emotion": "anxious"},
                created_at=now + timedelta(minutes=d["offset_min"]),
            )
            db.add(entry)

        # 4. 创建议会记录
        print("创建议会辩论记录...")
        council = Council(
            id=str(uuid.uuid4()),
            session_id=session_id,
            debate_data={
                "rounds": [
                    {
                        "round": 1,
                        "exiles_argument": "我只是想被爱，被接纳。为什么每次犯错都要被批评？我已经很努力了...",
                        "firefighters_argument": "努力不够就是不够。你看看那些成功的人，哪个不是对自己严格要求？放纵自己只会让你更失败。",
                    },
                    {
                        "round": 2,
                        "exiles_argument": "可是我好累...我不想再假装坚强了。我需要休息，需要有人告诉我'你已经做得很好了'。",
                        "firefighters_argument": "休息是弱者的借口。但...也许我对你太严厉了。我只是不想你受伤，不想你经历失败的痛苦。",
                    },
                    {
                        "round": 3,
                        "exiles_argument": "我知道你是为了保护我。但你的方式让我更痛苦了。我们能不能找到一种更温柔的方式？",
                        "firefighters_argument": "也许...我可以试着不那么苛刻。保护你不一定要通过批评。我们可以一起设定合理的目标。",
                    },
                ],
                "topic": "对失败的恐惧与自我价值",
            },
            conclusion="本我和超我达成了初步共识：追求进步而非完美，允许脆弱的存在，用鼓励代替批评。核心信念'我必须完美才值得被爱'需要被重新审视。",
            rounds=3,
            status="completed",
            id_performance={"empathy": 0.9, "authenticity": 0.85},
            superego_performance={"logic": 0.8, "flexibility": 0.7},
            started_at=now + timedelta(minutes=10),
            completed_at=now + timedelta(minutes=14),
        )
        db.add(council)

        # 5. 创建疗愈日记
        print("创建疗愈日记...")
        diaries = [
            {
                "diary_text": "在黑暗的森林里，有一个小小的光点。那是内心深处未曾熄灭的希望。即使周围都是阴影，那束光依然温暖而坚定。它在说：你值得被爱，不是因为你完美，而是因为你存在。",
                "persona": "exiles",
                "image_url": "/placeholder/healing_forest_light.png",
            },
            {
                "diary_text": "两个声音终于坐下来对话了。一个带着泪水，一个放下了盔甲。他们发现，原来彼此都在用自己的方式守护着同一颗心。和解不是妥协，而是理解。",
                "persona": "counselor",
                "image_url": "/placeholder/healing_two_voices.png",
            },
        ]

        for d in diaries:
            img = HealingImage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                image_url=d["image_url"],
                diary_text=d["diary_text"],
                persona=d["persona"],
            )
            db.add(img)

        await db.commit()
        print("\n演示数据填充完成!")
        print(f"  用户名: demo")
        print(f"  会话ID: {session_id}")
        print(f"  对话记录: {len(dialogues)} 条")
        print(f"  议会辩论: 1 场 (3 轮)")
        print(f"  疗愈日记: {len(diaries)} 篇")


if __name__ == "__main__":
    asyncio.run(seed())

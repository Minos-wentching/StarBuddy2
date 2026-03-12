"""
认证服务

用户认证、注册、会话管理等业务逻辑
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from ..database.models import User, Session as UserSession
from ..models.schemas import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class AuthService:
    """认证服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, username: str) -> User:
        """创建新用户（仅用户名）"""
        try:
            # 检查用户名是否已存在
            existing_user = await self.get_user_by_username(username)
            if existing_user:
                raise ValueError("该用户名已被使用")

            # 创建用户
            user = User(
                username=username,
                is_active=True,
                settings={},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

            logger.info(f"用户创建成功: {username}")
            return user

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"创建用户时数据库完整性错误: {e}")
            raise ValueError("用户创建失败，可能已存在重复数据")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建用户失败: {e}")
            raise

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """通过ID获取用户"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_user(self, user_id: int, updates: Dict[str, Any]) -> Optional[User]:
        """更新用户信息"""
        try:
            # 获取用户
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            # 处理更新
            update_data = {}
            for key, value in updates.items():
                if value is not None:
                    if key == "username":
                        # 用户名需要验证唯一性
                        existing = await self.get_user_by_username(value)
                        if existing and existing.id != user_id:
                            raise ValueError("该用户名已被其他用户使用")
                        update_data["username"] = value
                    elif key not in ["email", "password"]:
                        # 跳过邮箱和密码字段，只允许更新其他字段
                        update_data[key] = value

            if not update_data:
                return user  # 没有实际更新

            # 更新数据库
            update_data["updated_at"] = datetime.utcnow()
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(**update_data)
            )
            await self.db.commit()

            # 重新获取用户以返回更新后的数据
            await self.db.refresh(user)
            logger.info(f"用户信息更新成功: {user.username}")
            return user

        except ValueError as e:
            await self.db.rollback()
            logger.warning(f"用户更新验证失败: {user_id}, 错误: {e}")
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"用户更新失败: {user_id}, 错误: {e}")
            raise

    async def update_last_login(self, user_id: int) -> bool:
        """更新用户最后登录时间"""
        try:
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(updated_at=datetime.utcnow())
            )
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新最后登录时间失败: {user_id}, 错误: {e}")
            return False

    async def deactivate_user(self, user_id: int) -> bool:
        """停用用户账户"""
        try:
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(is_active=False, updated_at=datetime.utcnow())
            )
            await self.db.commit()
            logger.info(f"用户账户已停用: {user_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"停用用户失败: {user_id}, 错误: {e}")
            return False

    async def create_session(self, user_id: int, session_data: Dict[str, Any]) -> Optional[UserSession]:
        """创建用户会话"""
        try:
            import uuid
            from datetime import datetime

            # 生成会话令牌
            session_token = str(uuid.uuid4())

            # 创建会话记录
            session = UserSession(
                user_id=user_id,
                session_token=session_token,
                current_persona=session_data.get("current_persona", "manager"),
                emotion_intensity=session_data.get("emotion_intensity", 0.0),
                persona_state=await self._build_initial_persona_state(user_id, session_data.get("persona_state", {})),
                is_active=True,
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )

            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)

            logger.info(f"创建用户会话: user_id={user_id}, session_id={session.id}")
            return session
        except Exception as e:
            logger.error(f"创建会话失败: {user_id}, 错误: {e}")
            return None

    async def _build_initial_persona_state(self, user_id: int, base_state: Dict[str, Any]) -> Dict[str, Any]:
        """基于用户设置构建会话初始 persona_state"""
        state = dict(base_state or {})
        state.setdefault("self_presence_clarity", 0.6)
        state.setdefault("self_presence_compassion", 0.6)
        state.setdefault("self_presence_trend", "stable")
        user = await self.get_user_by_id(user_id)
        if not user:
            return state

        settings = user.settings or {}
        onboarding = settings.get("ifs_onboarding", {})

        if settings.get("ifs_onboarding_completed"):
            state["onboarding_completed"] = True
            state["exiles_system_prompt"] = onboarding.get("exiles_system_prompt", "")
            state["firefighters_system_prompt"] = onboarding.get("firefighters_system_prompt", "")
            state["onboarding_profile"] = {
                "profile_digest": onboarding.get("profile_digest", ""),
                "trauma_hypothesis": onboarding.get("trauma_hypothesis", ""),
                "user_core_info": onboarding.get("user_core_info", []),
                "core_beliefs": onboarding.get("core_beliefs", []),
                "profile_version": onboarding.get("profile_version", 1),
                "profile_confirmed": onboarding.get("profile_confirmed", False),
            }
            state["persona_portraits"] = onboarding.get("persona_portraits", {})
        return state

    async def get_user_sessions(self, user_id: int) -> list:
        """获取用户的所有会话"""
        try:
            # 查询用户的所有活跃会话
            stmt = select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            ).order_by(UserSession.last_activity.desc())

            result = await self.db.execute(stmt)
            sessions = result.scalars().all()

            logger.info(f"获取用户会话: user_id={user_id}, 数量={len(sessions)}")
            return sessions
        except Exception as e:
            logger.error(f"获取用户会话失败: {user_id}, 错误: {e}")
            return []


async def example_usage():
    """示例用法"""
    from ..database.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        service = AuthService(db)

        # 创建用户
        user = await service.create_user(username="testuser")
        print(f"创建的用户: {user.username}")

        # 获取用户
        db_user = await service.get_user_by_id(user.id)
        print(f"获取的用户: {db_user.username}")

        # 通过用户名获取用户
        user_by_name = await service.get_user_by_username("testuser")
        print(f"通过用户名获取: {user_by_name.username if user_by_name else 'None'}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
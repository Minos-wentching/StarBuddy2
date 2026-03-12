"""
版本存档服务

管理心理状态版本快照，支持Git式操作
"""

import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import chromadb
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from ..api_config import config
from ..models.schemas import SnapshotResponse, VersionTree

logger = logging.getLogger(__name__)

# 模块级单例：共享 ChromaDB 客户端，避免每次请求都创建 PersistentClient
_chroma_client: Optional[chromadb.ClientAPI] = None
_chroma_collection = None


def _get_shared_chroma():
    """获取或创建共享的 ChromaDB 客户端和集合（单例）"""
    global _chroma_client, _chroma_collection
    if _chroma_client is not None and _chroma_collection is not None:
        return _chroma_client, _chroma_collection
    try:
        _chroma_client = chromadb.PersistentClient(
            path=config.CHROMA_PERSIST_DIR
        )
        _chroma_collection = _chroma_client.get_or_create_collection(
            name="inner_mirror_snapshots",
            metadata={"description": "Inner Mirror心理状态快照"}
        )
        logger.info(f"ChromaDB 共享客户端初始化完成: {config.CHROMA_PERSIST_DIR}")
    except Exception as e:
        logger.error(f"ChromaDB 共享客户端初始化失败: {e}")
        _chroma_client = None
        _chroma_collection = None
    return _chroma_client, _chroma_collection


class VersionService:
    """版本存档服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.chroma_client, self.collection = _get_shared_chroma()

    def _generate_hash(self, data: Dict[str, Any]) -> str:
        """生成版本哈希"""
        # 序列化数据
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)

        # 计算SHA-256哈希
        hash_obj = hashlib.sha256(data_str.encode('utf-8'))
        return hash_obj.hexdigest()[:16]  # 取前16位作为简化哈希

    async def create_snapshot(
        self,
        session_id: str,
        state_data: Dict[str, Any],
        tags: List[str] = None
    ) -> SnapshotResponse:
        """创建版本快照"""
        try:
            if not self.collection:
                raise ValueError("ChromaDB未初始化")

            # 生成版本哈希
            version_hash = self._generate_hash(state_data)

            # 提取元数据
            persona = state_data.get("persona", "unknown")
            emotion_intensity = state_data.get("emotion_intensity", 0.0)
            message_count = state_data.get("message_count", 0)

            # 构建元数据
            metadata = {
                "session_id": session_id,
                "persona": persona,
                "emotion_intensity": emotion_intensity,
                "message_count": message_count,
                "tags": tags or [],
                "created_at": datetime.utcnow().isoformat(),
                "version_hash": version_hash
            }

            # 存储到ChromaDB
            self.collection.add(
                documents=[json.dumps(state_data, ensure_ascii=False)],
                metadatas=[metadata],
                ids=[version_hash]
            )

            logger.info(f"快照创建: {version_hash}, 会话: {session_id}")

            return SnapshotResponse(
                id=version_hash,
                session_id=session_id,
                persona=persona,
                emotion_intensity=emotion_intensity,
                message_count=message_count,
                tags=tags or [],
                created_at=datetime.fromisoformat(metadata["created_at"]),
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"创建快照失败: {e}")
            raise

    async def get_snapshot(self, snapshot_id: str) -> Optional[SnapshotResponse]:
        """获取快照详情"""
        try:
            if not self.collection:
                return None

            # 从ChromaDB查询
            results = self.collection.get(
                ids=[snapshot_id],
                include=["documents", "metadatas"]
            )

            if not results["ids"]:
                return None

            metadata = results["metadatas"][0]
            document = results["documents"][0]

            return SnapshotResponse(
                id=snapshot_id,
                session_id=metadata["session_id"],
                persona=metadata["persona"],
                emotion_intensity=metadata["emotion_intensity"],
                message_count=metadata["message_count"],
                tags=metadata.get("tags", []),
                created_at=datetime.fromisoformat(metadata["created_at"]),
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"获取快照失败: {snapshot_id}, 错误: {e}")
            return None

    async def get_version_tree(self, session_id: str) -> VersionTree:
        """获取版本树"""
        try:
            if not self.collection:
                return VersionTree(
                    session_id=session_id,
                    snapshots=[],
                    branches={}
                )

            # 查询该会话的所有快照
            results = self.collection.get(
                where={"session_id": session_id},
                include=["metadatas"]
            )

            # 转换快照
            snapshots = []
            for i, metadata in enumerate(results["metadatas"]):
                snapshot = SnapshotResponse(
                    id=results["ids"][i],
                    session_id=session_id,
                    persona=metadata["persona"],
                    emotion_intensity=metadata["emotion_intensity"],
                    message_count=metadata["message_count"],
                    tags=metadata.get("tags", []),
                    created_at=datetime.fromisoformat(metadata["created_at"]),
                    metadata=metadata
                )
                snapshots.append(snapshot)

            # 按时间排序
            snapshots.sort(key=lambda x: x.created_at)

            # 构建分支（简化版：按标签分组）
            branches = {}
            for snapshot in snapshots:
                for tag in snapshot.tags:
                    if tag not in branches:
                        branches[tag] = []
                    branches[tag].append(snapshot.id)

            # 默认分支
            if "main" not in branches:
                branches["main"] = [s.id for s in snapshots]

            return VersionTree(
                session_id=session_id,
                snapshots=snapshots,
                branches=branches
            )

        except Exception as e:
            logger.error(f"获取版本树失败: {session_id}, 错误: {e}")
            return VersionTree(
                session_id=session_id,
                snapshots=[],
                branches={}
            )

    async def list_snapshots(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
        filters: Dict[str, Any] = None
    ) -> List[SnapshotResponse]:
        """列出快照"""
        try:
            if not self.collection:
                return []

            # 构建查询条件
            where_clause = {"session_id": session_id}

            if filters:
                if "persona" in filters:
                    where_clause["persona"] = filters["persona"]
                if "tags" in filters:
                    # ChromaDB支持数组查询
                    pass  # 简化处理

            # 查询
            results = self.collection.get(
                where=where_clause,
                limit=limit,
                offset=offset,
                include=["metadatas"]
            )

            # 转换结果
            snapshots = []
            for i, metadata in enumerate(results["metadatas"]):
                snapshot = SnapshotResponse(
                    id=results["ids"][i],
                    session_id=session_id,
                    persona=metadata["persona"],
                    emotion_intensity=metadata["emotion_intensity"],
                    message_count=metadata["message_count"],
                    tags=metadata.get("tags", []),
                    created_at=datetime.fromisoformat(metadata["created_at"]),
                    metadata=metadata
                )

                # 应用强度过滤
                if filters:
                    if "min_intensity" in filters:
                        if snapshot.emotion_intensity < filters["min_intensity"]:
                            continue
                    if "max_intensity" in filters:
                        if snapshot.emotion_intensity > filters["max_intensity"]:
                            continue
                    if "tags" in filters and filters["tags"]:
                        # 检查是否包含所有指定标签
                        if not all(tag in snapshot.tags for tag in filters["tags"]):
                            continue

                snapshots.append(snapshot)

            return snapshots

        except Exception as e:
            logger.error(f"列出快照失败: {session_id}, 错误: {e}")
            return []

    async def restore_snapshot(self, session_id: str, snapshot_id: str) -> bool:
        """恢复到指定快照"""
        try:
            if not self.collection:
                logger.error("ChromaDB未初始化")
                return False

            # 获取快照文档和元数据
            results = self.collection.get(
                ids=[snapshot_id],
                include=["documents", "metadatas"]
            )

            if not results["ids"]:
                logger.error(f"快照不存在: {snapshot_id}")
                return False

            document = results["documents"][0]
            metadata = results["metadatas"][0]
            snapshot_session_id = metadata.get("session_id")
            if snapshot_session_id != session_id:
                logger.warning(
                    f"拒绝跨会话恢复: snapshot={snapshot_id}, snapshot_session={snapshot_session_id}, target_session={session_id}"
                )
                return False

            # 解析状态数据
            state_data = json.loads(document)

            # 更新会话状态
            from ..database.models import Session
            from sqlalchemy import update

            # 构建会话更新数据
            update_data = {
                "current_persona": state_data.get("persona", "manager"),
                "emotion_intensity": state_data.get("emotion_intensity", 0.0),
                "persona_state": state_data.get("persona_state", {}),
                "last_activity": datetime.utcnow()
            }

            # 如果有情绪历史，也更新
            if "emotion_history" in state_data:
                update_data["emotion_history"] = state_data["emotion_history"]

            # 执行更新
            stmt = (
                update(Session)
                .where(Session.id == session_id)
                .values(**update_data)
            )
            await self.db.execute(stmt)
            await self.db.commit()

            # 创建恢复点快照（可选）
            # 可以记录恢复操作
            logger.info(f"快照恢复完成: {session_id} -> {snapshot_id}")
            return True

        except Exception as e:
            logger.error(f"恢复快照失败: {snapshot_id}, 错误: {e}")
            await self.db.rollback()
            return False

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """删除快照"""
        try:
            if not self.collection:
                return False

            # 从ChromaDB删除
            self.collection.delete(ids=[snapshot_id])

            logger.info(f"快照删除: {snapshot_id}")
            return True

        except Exception as e:
            logger.error(f"删除快照失败: {snapshot_id}, 错误: {e}")
            return False

    async def create_branch(
        self,
        session_id: str,
        branch_name: str,
        from_snapshot: str = None
    ) -> Dict[str, Any]:
        """创建分支"""
        try:
            if not self.collection:
                raise ValueError("ChromaDB未初始化")

            # 检查是否已存在同名分支（通过标签检查）
            existing_results = self.collection.get(
                where={"session_id": session_id, "tags": {"$contains": [f"branch:{branch_name}"]}},
                include=["metadatas"]
            )
            if existing_results["ids"]:
                logger.warning(f"分支已存在: {branch_name}")
                # 仍然返回分支信息

            base_snapshot = None
            base_snapshot_id = None
            if from_snapshot:
                # 获取基础快照
                base_snapshot = await self.get_snapshot(from_snapshot)
                if not base_snapshot:
                    raise ValueError(f"基础快照不存在: {from_snapshot}")
                if base_snapshot.session_id != session_id:
                    raise ValueError("基础快照不属于当前会话")
                base_snapshot_id = from_snapshot

                # 为快照添加分支标签
                metadata = base_snapshot.meta_data
                tags = metadata.get("tags", [])
                if f"branch:{branch_name}" not in tags:
                    tags.append(f"branch:{branch_name}")
                    # 更新快照标签
                    self.collection.update(
                        ids=[from_snapshot],
                        metadatas=[{**metadata, "tags": tags}]
                    )
                    logger.info(f"快照 {from_snapshot} 添加分支标签: {branch_name}")
                else:
                    logger.info(f"快照 {from_snapshot} 已有分支标签: {branch_name}")

            # 创建分支元数据
            branch = {
                "name": branch_name,
                "session_id": session_id,
                "from_snapshot": base_snapshot_id,
                "created_at": datetime.utcnow().isoformat(),
                "snapshot_count": 1 if base_snapshot_id else 0,
                "tag": f"branch:{branch_name}"
            }

            logger.info(f"分支创建: {branch_name}, 会话: {session_id}")
            return branch

        except Exception as e:
            logger.error(f"创建分支失败: {branch_name}, 错误: {e}")
            raise

    async def list_branches(self, session_id: str) -> List[Dict[str, Any]]:
        """列出分支"""
        try:
            # 获取版本树
            tree = await self.get_version_tree(session_id)

            # 从标签中提取分支
            branches = []
            for branch_name, snapshot_ids in tree.branches.items():
                branch = {
                    "name": branch_name,
                    "session_id": session_id,
                    "snapshot_count": len(snapshot_ids),
                    "latest_snapshot": snapshot_ids[-1] if snapshot_ids else None
                }
                branches.append(branch)

            return branches

        except Exception as e:
            logger.error(f"列出分支失败: {session_id}, 错误: {e}")
            return []


async def example_usage():
    """示例用法"""
    from ..database.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        service = VersionService(db)

        # 创建快照
        snapshot = await service.create_snapshot(
            session_id="test_session",
            state_data={
                "persona": "manager",
                "emotion_intensity": 0.5,
                "message": "测试消息",
                "response": "测试响应"
            },
            tags=["test", "initial"]
        )

        print(f"快照创建: {snapshot.id}")
        print(f"人格: {snapshot.persona}")
        print(f"强度: {snapshot.emotion_intensity}")

        # 获取版本树
        tree = await service.get_version_tree("test_session")
        print(f"快照数量: {len(tree.snapshots)}")
        print(f"分支: {list(tree.branches.keys())}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())

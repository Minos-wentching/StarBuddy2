"""
ChromaDB 向量记忆管理系统
基于 Multiego/memory.py，适配 FastAPI 异步后端。
负责记忆的嵌入存储、检索与版本快照。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime
from threading import Lock
from typing import Optional, List, Dict, Any

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer
from chromadb.errors import DuplicateIDError

from ..api_config import config

logger = logging.getLogger(__name__)

_embedding_model: Optional[SentenceTransformer] = None
_embedding_lock = Lock()


def _load_embedding_model() -> SentenceTransformer:
    """
    加载 embedding 模型，优先级：
    1. 已有本地目录 (config.EMBEDDING_CACHE_DIR)
    2. ModelScope snapshot_download
    3. 通过 huggingface_hub + hf-mirror 下载到本地目录
    4. 回退至 SentenceTransformer 默认下载
    """
    global _embedding_model
    with _embedding_lock:
        if _embedding_model is not None:
            return _embedding_model

        local_dir = config.EMBEDDING_CACHE_DIR
        model_id = config.EMBEDDING_MODEL

        # ① 本地目录已存在，尝试直接加载
        if os.path.isdir(local_dir) and os.listdir(local_dir):
            logger.info("尝试加载本地嵌入模型目录: %s", local_dir)
            try:
                # 尝试加载根目录
                _embedding_model = SentenceTransformer(local_dir)
                logger.info("从根目录成功加载嵌入模型")
                return _embedding_model
            except Exception as e:
                logger.warning("从根目录加载失败 (%s)，尝试查找模型子目录", e)
                # 尝试查找可能的模型子目录
                for root, dirs, files in os.walk(local_dir):
                    # 检查是否有config.json文件
                    if "config.json" in files:
                        try:
                            model_path = root
                            logger.info("尝试从子目录加载模型: %s", model_path)
                            _embedding_model = SentenceTransformer(model_path)
                            logger.info("从子目录成功加载嵌入模型: %s", model_path)
                            return _embedding_model
                        except Exception as sub_e:
                            logger.warning("子目录加载失败: %s", sub_e)
                            continue
                logger.info("未找到有效的模型文件，继续下载流程")

        # ② ModelScope snapshot_download
        try:
            from modelscope import snapshot_download as ms_download
            os.makedirs(local_dir, exist_ok=True)
            model_dir = ms_download(
                "AI-ModelScope/all-MiniLM-L6-v2",
                revision="master",
                cache_dir=local_dir,
            )
            logger.info("Embedding model resolved via ModelScope: %s", model_dir)
            _embedding_model = SentenceTransformer(model_dir)
            return _embedding_model
        except Exception as e:
            logger.warning("ModelScope download failed (%s), trying hf-mirror", e)

        # ③ 通过 hf-mirror 下载
        try:
            from huggingface_hub import snapshot_download
            os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
            os.makedirs(os.path.dirname(local_dir), exist_ok=True)
            logger.info("Downloading embedding model from hf-mirror to %s ...", local_dir)
            snapshot_download(
                repo_id=model_id,
                local_dir=local_dir,
                ignore_patterns=["*.msgpack", "*.h5", "*.ot"],
            )
            _embedding_model = SentenceTransformer(local_dir)
            return _embedding_model
        except Exception as e:
            logger.warning("hf-mirror download failed (%s), falling back to default", e)

        # ④ 回退
        logger.info("Falling back to SentenceTransformer(%s)", model_id)
        _embedding_model = SentenceTransformer(model_id)
        return _embedding_model


def preload_embedding_model() -> SentenceTransformer:
    """显式预加载 embedding 模型，用于冷启动加速。"""
    return _load_embedding_model()


from starlette.concurrency import run_in_threadpool

def _embed_texts_sync(texts: list[str]) -> list[list[float]]:
    """对输入文本做本地 embedding (同步方法)"""
    if not texts:
        logger.debug("_embed_texts_sync: empty texts, returning []")
        return []
    model = _load_embedding_model()
    sanitized = [str(t) for t in texts]
    arr = np.asarray(model.encode(sanitized, normalize_embeddings=True), dtype=np.float64)
    if arr.ndim == 0:
        logger.debug("_embed_texts_sync: arr.ndim == 0, returning []")
        return []
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    result = arr.tolist()
    logger.debug(f"_embed_texts_sync: input {len(texts)} texts, output shape {len(result)}x{len(result[0]) if result else 0}")
    return result

async def _embed_texts(texts: list[str]) -> list[list[float]]:
    """异步执行 embedding"""
    return await run_in_threadpool(_embed_texts_sync, texts)


class MemoryStore:
    """基于 ChromaDB 的记忆存储，移植自 Multiego/memory.py"""
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MemoryStore, cls).__new__(cls)
        return cls._instance

    def __init__(
        self,
        persist_dir: str = None,
        collection_name: str = None,
    ):
        if MemoryStore._initialized:
            return
        
        persist_dir = persist_dir or config.CHROMA_PERSIST_DIR
        collection_name = collection_name or config.CHROMA_COLLECTION_NAME
        os.makedirs(config.EMBEDDING_CACHE_DIR, exist_ok=True)
        os.environ.setdefault("MS_CACHE_HOME", config.EMBEDDING_CACHE_DIR)
        os.makedirs(persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._collection_name = collection_name
        self._llm_client = None  # 由外部注入 AsyncOpenAI client
        MemoryStore._initialized = True
        logger.info("MemoryStore initialized: %s", collection_name)

    def set_llm_client(self, client):
        """注入 AsyncOpenAI 客户端，用于关键词提取"""
        self._llm_client = client

    def _safe_n_results(self, n: int) -> int:
        try:
            count = self._collection.count()
        except Exception:
            count = 0
        return min(n, count) if count > 0 else 0

    @staticmethod
    def _build_where_filter(filters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """构建兼容 Chroma 的 where 过滤器。

        Chroma 新版对 where 的校验要求顶层只有一个操作符：
        - 单条件：{"field": value}
        - 多条件：{"$and": [{"field1": value1}, {"field2": value2}]}
        """
        source = filters or {}
        normalized = {k: v for k, v in source.items() if v is not None}
        if not normalized:
            return None
        if len(normalized) == 1:
            key, value = next(iter(normalized.items()))
            return {key: value}
        return {"$and": [{k: v} for k, v in normalized.items()]}

    @staticmethod
    def _new_unique_id(prefix: str) -> str:
        """生成高熵唯一 ID，避免并发/批内冲突"""
        return f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:10]}"

    def _add_with_duplicate_retry(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> List[str]:
        """写入 ChromaDB，若出现重复 ID 则重建 ID 后重试一次"""
        try:
            self._collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
            return ids
        except DuplicateIDError:
            rebuilt_ids = [self._new_unique_id(idv.split("_")[0] if idv else "doc") for idv in ids]
            self._collection.add(ids=rebuilt_ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
            logger.warning("Duplicate IDs detected; rebuilt %d ids and retried", len(rebuilt_ids))
            return rebuilt_ids

    def _is_duplicate(
        self,
        doc_text: str,
        doc_type: str,
        threshold: float = 0.92,
        user_id: Optional[int] = None,
    ) -> bool:
        """检查向量库中是否已存在高度相似的文档"""
        try:
            n = self._safe_n_results(1)
            if n == 0:
                return False
            embedding = _embed_texts_sync([doc_text])
            if not embedding:
                return False
            where_filter = self._build_where_filter({
                "type": doc_type,
                "user_id": user_id,
            })
            results = self._collection.query(
                query_embeddings=embedding, n_results=n,
                where=where_filter,
            )
            if results and results["distances"] and results["distances"][0]:
                similarity = 1.0 - results["distances"][0][0]
                if similarity >= threshold:
                    logger.debug(
                        "Duplicate detected (similarity=%.3f, type=%s, user_id=%s)",
                        similarity,
                        doc_type,
                        user_id,
                    )
                    return True
        except Exception as e:
            logger.debug("Dedup check failed: %s", e)
        return False

    # ──────── 写入 ────────

    def store_report(self, report_data: Dict[str, Any], user_input: str = "", user_id: Optional[int] = None) -> list[str]:
        """
        将 Counselor 分析报告嵌入向量库。
        每个 CoreBelief 作为一条记录存储，内置去重。
        """
        ids, documents, metadatas, embeddings = [], [], [], []
        now = datetime.now()
        used_ids = set()

        core_beliefs = report_data.get("core_beliefs", [])
        trigger = report_data.get("trigger_event", "")

        for belief in core_beliefs:
            doc_text = (
                f"Core Belief: {belief.get('content', '')}\n"
                f"Valence: {belief.get('valence', 0)}\n"
                f"Intensity: {belief.get('intensity', 0)}\n"
                f"Origin: {belief.get('origin_event', '')}\n"
                f"Trigger: {trigger}\nUser said: {user_input}"
            )
            if self._is_duplicate(doc_text, "core_belief", user_id=user_id):
                continue
            raw_bid = str(belief.get("belief_id", "") or "").strip()
            bid = raw_bid or hashlib.md5(doc_text.encode()).hexdigest()[:8]
            doc_id = self._new_unique_id(f"belief_{bid}")
            while doc_id in used_ids:
                doc_id = self._new_unique_id(f"belief_{bid}")
            used_ids.add(doc_id)
            ids.append(doc_id)
            documents.append(doc_text)
            # 构建元数据，包含用户ID
            belief_metadata = {
                "belief_id": bid, "intensity": belief.get("intensity", 0),
                "valence": belief.get("valence", 0), "trigger": trigger,
                "timestamp": now.isoformat(), "type": "core_belief",
            }
            if user_id is not None:
                belief_metadata["user_id"] = user_id
            metadatas.append(belief_metadata)
            emb = _embed_texts_sync([doc_text])
            if emb:
                embeddings.append(emb[0])

            trauma_text = str(belief.get("origin_event", "") or trigger or user_input).strip()
            if trauma_text:
                trauma_doc_text = (
                    f"Trauma Event: {trauma_text}\n"
                    f"Trigger: {trigger}\n"
                    f"Belief: {belief.get('content', '')}\n"
                    f"User said: {user_input}"
                )
                trauma_id = self._new_unique_id(f"event_{bid}")
                while trauma_id in used_ids:
                    trauma_id = self._new_unique_id(f"event_{bid}")
                used_ids.add(trauma_id)
                ids.append(trauma_id)
                documents.append(trauma_doc_text)

                trauma_metadata = {
                    "event_id": trauma_id,
                    "belief_id": bid,
                    "trigger_event": str(trigger or ""),
                    "trauma_event": trauma_text,
                    "source_type": "memory_extract",
                    "intensity": belief.get("intensity", 0),
                    "timestamp": now.isoformat(),
                    "type": "trauma_event",
                }
                if user_id is not None:
                    trauma_metadata["user_id"] = user_id
                metadatas.append(trauma_metadata)
                emb = _embed_texts_sync([trauma_doc_text])
                if emb:
                    embeddings.append(emb[0])

        # 存入情感概要
        summary = report_data.get("emotional_summary", "")
        if summary:
            summary_text = f"Emotional Summary: {summary}\nTrigger: {trigger}\nUser said: {user_input}"
            if not self._is_duplicate(summary_text, "emotional_summary", user_id=user_id):
                summary_id = self._new_unique_id("summary")
                while summary_id in used_ids:
                    summary_id = self._new_unique_id("summary")
                used_ids.add(summary_id)
                ids.append(summary_id)
                documents.append(summary_text)
                # 构建情感概要元数据
                summary_metadata = {"type": "emotional_summary", "timestamp": now.isoformat()}
                if user_id is not None:
                    summary_metadata["user_id"] = user_id
                metadatas.append(summary_metadata)
                emb = _embed_texts_sync([summary_text])
                if emb:
                    embeddings.append(emb[0])

        if ids:
            if len(embeddings) != len(documents):
                embeddings = _embed_texts_sync(documents)
            if embeddings and len(embeddings) == len(documents):
                logger.debug(f"store_report: embeddings type {type(embeddings)}, length {len(embeddings)}, first element type {type(embeddings[0]) if embeddings else None}")
                ids = self._add_with_duplicate_retry(ids, documents, metadatas, embeddings)
                logger.info("Stored %d memory entries", len(ids))
        return ids

    def store_diary(self, diary_text: str, author: str, belief_ref: str = "", user_id: Optional[int] = None) -> str:
        """存储日记条目到向量库"""
        now = datetime.now()
        doc_id = self._new_unique_id(f"diary_{author}")
        embeddings = _embed_texts_sync([diary_text])
        if not embeddings:
            logger.warning("Failed to embed diary entry; skip store")
            return ""
        logger.debug(f"store_diary: embeddings type {type(embeddings)}, length {len(embeddings)}")
        # 构建日记元数据
        diary_metadata = {
            "type": "diary", "author": author,
            "belief_ref": belief_ref, "timestamp": now.isoformat(),
        }
        if user_id is not None:
            diary_metadata["user_id"] = user_id

        written_ids = self._add_with_duplicate_retry(
            ids=[doc_id],
            documents=[diary_text],
            metadatas=[diary_metadata],
            embeddings=embeddings,
        )
        doc_id = written_ids[0]
        return doc_id

    def store_memory(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """存储通用记忆（如对话历史）"""
        metadata = metadata or {}
        now = datetime.now()
        doc_id = self._new_unique_id("memory")
        
        # 补充元数据
        if "type" not in metadata:
            metadata["type"] = "dialogue_history"
        metadata["timestamp"] = now.isoformat()
        
        embeddings = _embed_texts_sync([content])
        if not embeddings:
            logger.warning("Failed to embed memory entry; skip store")
            return ""
            
        logger.debug(f"store_memory: embeddings type {type(embeddings)}, length {len(embeddings)}")
        written_ids = self._add_with_duplicate_retry(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata],
            embeddings=embeddings,
        )
        doc_id = written_ids[0]
        return doc_id

    # ──────── 检索 ────────

    def retrieve_relevant(self, query: str, n_results: int = 5, user_id: Optional[int] = None) -> list[dict]:
        """根据语义相似度检索相关记忆"""
        n = self._safe_n_results(n_results)
        if n == 0:
            return []
        query_embedding = _embed_texts_sync([query])
        if not query_embedding:
            return []
        where_filter = self._build_where_filter({"user_id": user_id})

        results = self._collection.query(
            query_embeddings=query_embedding,
            n_results=n,
            where=where_filter,
        )
        entries = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                entries.append({
                    "id": results["ids"][0][i] if results["ids"] else "",
                    "document": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                })
        return entries

    # ──────── 混合检索（向量 + 关键词 + RRF 融合）────────

    _KW_CACHE_MAXSIZE = 500

    async def _extract_keywords(self, query: str) -> list[str]:
        """用 LLM 提取查询关键词"""
        cache_key = hashlib.md5(query.encode()).hexdigest()
        if not hasattr(self, "_kw_cache"):
            self._kw_cache: dict[str, list[str]] = {}
        if cache_key in self._kw_cache:
            # 将命中的 key 移到末尾（LRU 策略）
            self._kw_cache[cache_key] = self._kw_cache.pop(cache_key)
            return self._kw_cache[cache_key]

        if not self._llm_client:
            return []
        try:
            resp = await self._llm_client.chat.completions.create(
                model=config.DASHSCOPE_DIALOGUE_MODEL,
                messages=[
                    {"role": "system", "content": (
                        "你是一个数据库搜索专家。请从用户的输入中提取1-3个核心关键词"
                        "（实体、事件、情感、特定名词）。\n"
                        '输出严格JSON格式: {"keywords": ["kw1", "kw2"]}'
                    )},
                    {"role": "user", "content": query[:300]},
                ],
                max_tokens=50,
            )
            raw = resp.choices[0].message.content
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                keywords = json.loads(json_match.group()).get("keywords", [])
            else:
                keywords = []
            # LRU 淘汰：超过 maxsize 时移除最早的条目
            if len(self._kw_cache) >= self._KW_CACHE_MAXSIZE:
                self._kw_cache.pop(next(iter(self._kw_cache)))
            self._kw_cache[cache_key] = keywords
            return keywords
        except Exception as e:
            logger.warning("Keyword extraction failed: %s", e)
            return []

    async def hybrid_search(self, query: str, n_results: int = 5, user_id: Optional[int] = None) -> list[dict]:
        """混合检索：向量相似度 + 关键词匹配 + RRF 融合排序"""
        # 1) 向量检索
        vec_hits = []
        try:
            vec_n = self._safe_n_results(n_results * 2)
            query_embedding = await _embed_texts([query])
            if vec_n > 0 and query_embedding:
                where_filter = self._build_where_filter({"user_id": user_id})

                vec_res = self._collection.query(
                    query_embeddings=query_embedding, n_results=vec_n,
                    where=where_filter,
                )
                if vec_res and vec_res["ids"] and vec_res["ids"][0]:
                    for i in range(len(vec_res["ids"][0])):
                        vec_hits.append({
                            "id": vec_res["ids"][0][i],
                            "document": vec_res["documents"][0][i],
                            "metadata": vec_res["metadatas"][0][i] if vec_res["metadatas"] else {},
                        })
        except Exception as e:
            logger.warning("Vector search failed: %s", e)

        # 2) 关键词检索
        kw_hits = []
        keywords = await self._extract_keywords(query)
        for kw in keywords:
            try:
                where_filter = self._build_where_filter({"user_id": user_id})

                kw_res = self._collection.get(
                    where=where_filter,
                    where_document={"$contains": kw},
                    include=["documents", "metadatas"],
                )
                if kw_res and kw_res["ids"]:
                    for i in range(len(kw_res["ids"])):
                        kw_hits.append({
                            "id": kw_res["ids"][i],
                            "document": kw_res["documents"][i] if kw_res["documents"] else "",
                            "metadata": kw_res["metadatas"][i] if kw_res["metadatas"] else {},
                        })
            except Exception:
                pass

        # 3) RRF 融合
        scores: dict[str, float] = {}
        data_map: dict[str, dict] = {}
        k = 60

        def _process(lst):
            for rank, item in enumerate(lst):
                doc_id = item["id"]
                if doc_id not in scores:
                    scores[doc_id] = 0.0
                    data_map[doc_id] = item
                scores[doc_id] += 1.0 / (rank + k)

        _process(vec_hits)
        _process(kw_hits)

        sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
        return [data_map[did] for did in sorted_ids[:n_results]]

    @staticmethod
    def format_rag_context(results: list[dict]) -> str:
        """将检索结果格式化为可注入 prompt 的文本"""
        if not results:
            return ""
        lines = ["【相关历史记忆】"]
        for item in results:
            doc = item.get("document", "")
            meta = item.get("metadata", {})
            ts = meta.get("timestamp", "")
            doc_type = meta.get("type", "")
            prefix = f"[{doc_type}]" if doc_type else ""
            line = f"- {prefix} {doc.strip()}  ({ts})" if ts else f"- {prefix} {doc.strip()}"
            lines.append(line)
        return "\n".join(lines)

    def get_all_beliefs(self, user_id: Optional[int] = None) -> list[dict]:
        """获取所有核心信念记录"""
        where_filter = self._build_where_filter({
            "type": "core_belief",
            "user_id": user_id,
        })

        results = self._collection.get(where=where_filter)
        entries = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"]):
                entries.append({
                    "id": results["ids"][i],
                    "document": doc,
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                })
        return entries

    def get_all_trauma_events(self, user_id: Optional[int] = None) -> list[dict]:
        """获取所有 trauma_event 记录"""
        where_filter = self._build_where_filter({
            "type": "trauma_event",
            "user_id": user_id,
        })

        results = self._collection.get(where=where_filter)
        entries = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"]):
                entries.append({
                    "id": results["ids"][i],
                    "document": doc,
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                })
        return entries

    # ──────── 快照 ────────

    def create_snapshot(self, snapshot_name: str) -> str:
        """创建当前 collection 的快照"""
        snap_name = f"{self._collection_name}_snapshot_{snapshot_name}"
        snap_col = self._client.get_or_create_collection(
            name=snap_name, metadata={"hnsw:space": "cosine"},
        )
        # 防止重复写入同一 snapshot collection 导致 ID 冲突
        try:
            existing_snap = snap_col.get()
            if existing_snap and existing_snap.get("ids"):
                snap_col.delete(ids=existing_snap["ids"])
        except Exception:
            pass
        all_data = self._collection.get(include=["embeddings", "documents", "metadatas"])
        if all_data and all_data["ids"]:
            snap_col.add(
                ids=all_data["ids"], documents=all_data["documents"],
                metadatas=all_data["metadatas"], embeddings=all_data["embeddings"],
            )
        logger.info("Created memory snapshot: %s", snap_name)
        return snap_name

    def load_snapshot(self, snapshot_collection_name: str) -> None:
        """加载历史快照到主 collection（覆盖）"""
        snap_col = self._client.get_collection(name=snapshot_collection_name)
        snap_data = snap_col.get(include=["embeddings", "documents", "metadatas"])
        existing = self._collection.get()
        if existing and existing["ids"]:
            self._collection.delete(ids=existing["ids"])
        if snap_data and snap_data["ids"]:
            self._collection.add(
                ids=snap_data["ids"], documents=snap_data["documents"],
                metadatas=snap_data["metadatas"], embeddings=snap_data["embeddings"],
            )
        logger.info("Loaded snapshot: %s", snapshot_collection_name)

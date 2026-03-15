"""
外部API服务

封装DashScope等外部API调用
"""

import logging
import json
import httpx
import asyncio
from typing import Dict, Any, Optional, List, Union, Generator
from openai import AsyncOpenAI
from ..api_config import config

# 外部 API 调用配置
API_TIMEOUT_SECONDS = int(getattr(config, "DIALOGUE_API_TIMEOUT_SECONDS", 45) or 45)
API_MAX_RETRIES = int(getattr(config, "DIALOGUE_API_MAX_RETRIES", 1) or 1)
API_RETRY_BACKOFF_BASE = 1.0  # 指数退避基础秒数
from .prompts import (
    MANAGER_CHAT_PROMPT, EXILES_SYSTEM_PROMPT, FIREFIGHTERS_SYSTEM_PROMPT,
    COUNSELOR_SYSTEM_PROMPT, EXILES_COUNCIL_PROMPT, FIREFIGHTERS_COUNCIL_PROMPT,
    COUNSELOR_COUNCIL_SUMMARY_PROMPT,
)

logger = logging.getLogger(__name__)


class ExternalAPIService:
    """外部API服务，基于 OpenAI 兼容协议调用 DashScope"""

    def __init__(self):
        # 初始化 OpenAI 异步客户端（OpenAI 兼容协议）
        provider = (getattr(config, "DIALOGUE_PROVIDER", "") or "").strip().lower()
        deepseek_key = str(getattr(config, "DEEPSEEK_API_KEY", "") or "").strip()
        dashscope_key = str(config.DASHSCOPE_DIALOGUE_API_KEY or config.DASHSCOPE_API_KEY or "").strip()

        selected = provider
        if not selected:
            selected = "deepseek" if deepseek_key else ("dashscope" if dashscope_key else "")

        api_key = ""
        base_url = ""
        model = ""

        if selected == "deepseek":
            api_key = deepseek_key
            base_url = str(getattr(config, "DEEPSEEK_BASE_URL", "") or "https://api.deepseek.com/v1").strip()
            model = str(getattr(config, "DEEPSEEK_MODEL", "") or "deepseek-chat").strip()
        elif selected == "dashscope":
            api_key = dashscope_key
            base_url = str(getattr(config, "DASHSCOPE_BASE_URL", "") or "https://dashscope.aliyuncs.com/compatible-mode/v1").strip()
            model = str(getattr(config, "DASHSCOPE_DIALOGUE_MODEL", "") or "qwen-max").strip()
        else:
            api_key = ""
            base_url = ""
            model = ""

        self.dialogue_provider = selected or "none"
        self.dialogue_model = model

        if api_key and base_url:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=API_TIMEOUT_SECONDS,
                max_retries=API_MAX_RETRIES,
            )
            logger.info("ExternalAPIService initialized: provider=%s base_url=%s timeout=%ss retries=%s", self.dialogue_provider, base_url, API_TIMEOUT_SECONDS, API_MAX_RETRIES)
        else:
            self.client = None
            logger.warning("No external dialogue API key configured; will try local LLM (if configured) or use mock responses")

        provider = (getattr(config, "LOCAL_LLM_PROVIDER", "") or "").strip().lower()
        self.local_provider = provider or ("ollama" if not api_key else "none")
        self.ollama_base_url = (getattr(config, "OLLAMA_BASE_URL", "") or "http://127.0.0.1:11434").rstrip("/")
        self.ollama_model = getattr(config, "OLLAMA_MODEL", "") or "qwen2.5:7b"

        # 图像生成仍使用 httpx (DashScope 专有 API)
        # z-image-turbo 同步生成可能需要更长时间
        self.httpx_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0)
        )

    async def generate_dialogue_response(
        self,
        persona: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False
    ) -> Union[str, Generator[str, None, None]]:
        """生成对话响应"""
        if not self.client:
            if self.local_provider == "ollama":
                try:
                    if stream:
                        return self._generate_local_stream(persona, message, context=context, history=history, system_prompt=system_prompt)
                    return await self._generate_ollama_response(persona, message, context=context, history=history, system_prompt=system_prompt)
                except Exception as e:
                    logger.warning(f"Local LLM failed, falling back to mock response: {e}")
            logger.info(f"Using mock response for {persona} because DASHSCOPE_API_KEY is not set")
            return await self._generate_mock_response(persona, message)

        try:
            model = self.dialogue_model or "qwen-max"
            
            # 构建消息列表
            messages = []
            
            # 1. 系统提示词
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                persona_prompts = {
                    "manager": MANAGER_CHAT_PROMPT,
                    "exiles": EXILES_SYSTEM_PROMPT,
                    "firefighters": FIREFIGHTERS_SYSTEM_PROMPT,
                    "counselor": COUNSELOR_SYSTEM_PROMPT,
                }
                messages.append({"role": "system", "content": persona_prompts.get(persona, persona_prompts["manager"])})

            # 2. 上下文信息
            if context:
                messages.append({
                    "role": "system", 
                    "content": f"当前上下文背景: {json.dumps(context, ensure_ascii=False)}"
                })

            # 3. 历史记录
            if history:
                messages.extend(history)

            # 4. 当前消息
            messages.append({"role": "user", "content": message})

            if stream:
                return self._generate_stream(model, messages)

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7 if persona == "exiles" else 0.5,
                top_p=0.8,
            )
            
            result = response.choices[0].message.content or ""
            logger.debug(f"Dialogue generated: persona={persona}, length={len(result)}")
            return result

        except Exception as e:
            logger.error(f"Dialogue generation failed: {e}")
            return await self._generate_mock_response(persona, message)

    async def _generate_stream(self, model: str, messages: List[Dict[str, str]]):
        """流式生成"""
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True
            )
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error(f"Stream generation failed: {e}")
            yield " (连接中断) "

    async def generate_council_debate(
        self,
        persona: str,
        topic: str,
        round_number: int,
        history_text: str
    ) -> str:
        """生成议会辩论论点，使用 Multiego 的 agent-specific council prompts"""
        if persona == "exiles":
            system_prompt = EXILES_COUNCIL_PROMPT.format(topic=topic, dialogue=history_text)
        elif persona == "firefighters":
            system_prompt = FIREFIGHTERS_COUNCIL_PROMPT.format(topic=topic, dialogue=history_text)
        else:
            system_prompt = f"作为{persona}，请就'{topic}'发表看法。"

        return await self.generate_dialogue_response(
            persona, f"第{round_number}轮，请发言。",
            system_prompt=system_prompt
        )

    async def generate_counselor_insight(
        self,
        topic: str,
        debate_history: str
    ) -> str:
        """生成Counselor整合洞察，使用 Multiego 的 COUNSELOR_COUNCIL_SUMMARY_PROMPT"""
        system_prompt = COUNSELOR_COUNCIL_SUMMARY_PROMPT.format(
            topic=topic, dialogue=debate_history
        )
        return await self.generate_dialogue_response(
            "counselor", "请提供你的观察和建议。",
            system_prompt=system_prompt
        )

    async def _httpx_request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """带重试的 httpx 请求"""
        last_exc = None
        for attempt in range(API_MAX_RETRIES):
            try:
                response = await getattr(self.httpx_client, method)(url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                last_exc = e
                if attempt < API_MAX_RETRIES - 1:
                    wait = API_RETRY_BACKOFF_BASE * (2 ** attempt)
                    logger.warning(f"HTTP request failed (attempt {attempt + 1}/{API_MAX_RETRIES}): {e}, retrying in {wait}s")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"HTTP request failed after {API_MAX_RETRIES} attempts: {e}")
        raise last_exc

    async def generate_imagery(
        self,
        description: str,
        size: str = "1024*1024"
    ) -> Optional[Dict[str, Any]]:
        """生成意象图像 (使用 DashScope z-image-turbo 同步 API)"""
        if not config.DASHSCOPE_API_KEY:
            logger.warning("[ImageGen] DASHSCOPE_API_KEY not set, skipping imagery generation")
            return None

        try:
            combined_prompt = f" {description}, 意识流，人脸被柔和的模糊或遮挡。以物象为主体。"

            payload = {
                "model": "z-image-turbo",
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"text": combined_prompt},
                            ],
                        }
                    ]
                },
                "parameters": {
                    "prompt_extend": False,
                    "size": size,
                },
            }

            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.DASHSCOPE_API_KEY}",
            }

            logger.info("[ImageGen] Posting to DashScope model=%s size=%s", payload["model"], size)

            response = await self._httpx_request_with_retry("post", url, headers=headers, json=payload)
            raw = response.text
            logger.info("[ImageGen] Response (first 300): %s", raw[:300])
            data = response.json()

            output = data.get("output", {})
            # z-image-turbo 返回结构: output.choices[0].message.content[i]
            choices = output.get("choices", [])
            if choices:
                content_list = choices[0].get("message", {}).get("content", [])
                results = []
                for item in content_list:
                    # 格式1: {"image": "url_or_base64"}
                    if "image" in item:
                        results.append({"url": item["image"]})
                    # 格式2: {"image_url": {"url": "https://..."}}
                    elif "image_url" in item:
                        img_val = item["image_url"]
                        if isinstance(img_val, dict):
                            results.append({"url": img_val.get("url", "")})
                        else:
                            results.append({"url": img_val})
                if results:
                    logger.info("[ImageGen] Extracted %d image(s) from response", len(results))
                    return {"results": results}

            # 兼容旧格式 wanx 等 (fallback)
            if "results" in output:
                return output

            logger.warning("[ImageGen] No image found in response: %s", raw[:300])
            return None
        except Exception as e:
            logger.error("[ImageGen] Request failed: %s", e)
            return None

    async def _generate_mock_response(self, persona: str, message: str) -> str:
        """降级方案"""
        snippet = str(message or "").strip()
        if len(snippet) > 70:
            snippet = snippet[:70].rstrip() + "…"

        if persona == "manager":
            return f"我听到了：{snippet}\n如果愿意的话，你能说说此刻最明显的感觉是什么吗？"
        if persona == "exiles":
            return f"我听到了：{snippet}\n这听起来真的很难受。你希望先被怎么安慰一下？"
        if persona == "firefighters":
            return f"我听到了：{snippet}\n我们先把节奏放慢一点：先呼气，再说下一句。"
        if persona == "counselor":
            return f"我听到了：{snippet}\n我们可以先做一个小的结构化回顾：触发点→感受→反应→结果。"
        return f"我听到了：{snippet}"

    async def _generate_ollama_response(
        self,
        persona: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """使用 Ollama 本地模型生成回复（免 API Key，需本机安装 Ollama 并拉取模型）"""
        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            persona_prompts = {
                "manager": MANAGER_CHAT_PROMPT,
                "exiles": EXILES_SYSTEM_PROMPT,
                "firefighters": FIREFIGHTERS_SYSTEM_PROMPT,
                "counselor": COUNSELOR_SYSTEM_PROMPT,
            }
            messages.append({"role": "system", "content": persona_prompts.get(persona, persona_prompts["manager"])})

        if context:
            messages.append({"role": "system", "content": f"当前上下文背景: {json.dumps(context, ensure_ascii=False)}"})

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": message})

        url = f"{self.ollama_base_url}/api/chat"
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7 if persona == "exiles" else 0.5,
            },
        }

        # Ollama local call: keep short timeout to avoid hanging the whole request.
        async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=2.0)) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = (((data or {}).get("message") or {}).get("content") or "").strip()
        return content or await self._generate_mock_response(persona, message)

    async def _generate_local_stream(
        self,
        persona: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
    ):
        """本地模型流式回退：当前以分段 yield 的方式模拟 stream。"""
        text = await self._generate_ollama_response(persona, message, context=context, history=history, system_prompt=system_prompt)
        # Yield in small chunks for UI smoothness
        chunk_size = 24
        for i in range(0, len(text), chunk_size):
            yield text[i:i + chunk_size]

    async def close(self):
        """关闭客户端"""
        await self.httpx_client.aclose()



async def example_usage():
    """示例用法"""
    service = ExternalAPIService()

    # 测试对话生成
    response = await service.generate_dialogue_response(
        persona="manager",
        message="我今天感到有些焦虑",
        context={"previous_topic": "工作压力"}
    )

    print(f"对话响应: {response}")

    # 测试API状态
    status = await service.check_api_status()
    print(f"API状态: {status}")

    await service.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())

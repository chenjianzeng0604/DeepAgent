import os
import logging
import json
from typing import Dict, Any, Optional, List, AsyncGenerator
import time
import asyncio
import openai
from src.prompts.prompt_templates import PromptTemplates
from src.config.app_config import app_config
import tiktoken

logger = logging.getLogger(__name__)

class LLMClient:
    """
    LLM客户端，封装对LLM API的调用
    """
    
    def __init__(self, api_key: str, model: str = "deepseek-r1", api_base: str = None,
                temperature: float = 0.7, max_tokens: int = 4096, use_tool_model: str = None):
        self.api_key = api_key
        self.model = model
        self.api_base = api_base
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.use_tool_model = use_tool_model
        self._init_client()
        self.token_limit = self._get_model_token_limit(model)
        logger.info(f"使用模型 {model}，token限制: {self.token_limit}")
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
    def _get_model_token_limit(self, model: str) -> int:
        """获取模型的token限制"""
        model_limits = {
            "qwen2.5-72b-instruct": 128000,
            "qwen-turbo-latest": 1000000,
            "qwq-32b": 128000,
            "deepseek-r1": 64000
        }
        return model_limits.get(model.lower(), 64000)
    
    def count_tokens(self, text: str) -> int:
        """计算文本的token数量"""
        if not text:
            return 0
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"计算token数量时出错: {e}，使用估算方法")
            chinese_count = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
            return chinese_count * 2 + (len(text) - chinese_count)
            
    def _truncate_prompt(self, prompt: str, system_message: str = None, model: str = None) -> str:
        """截断prompt以确保不超过模型token限制"""
        system_tokens = self.count_tokens(system_message) if system_message else 0
        available_tokens = self._get_model_token_limit(model) - system_tokens
        prompt_tokens = self.count_tokens(prompt)
        if prompt_tokens > available_tokens:
            truncation_ratio = available_tokens / prompt_tokens
            logger.warning(f"输入过长 ({prompt_tokens} tokens)，截断至 {available_tokens} tokens (比例: {truncation_ratio:.2f})")
            truncated_length = int(len(prompt) * truncation_ratio * 0.9)
            prompt = prompt[:truncated_length] + "\n\n[注：由于内容过长，部分输入已被截断]"
        return prompt
    
    def _init_client(self):
        """初始化API客户端"""
        try:
            openai.api_key = self.api_key
            if "dashscope" in self.api_base:
                if self.api_base.endswith('/'):
                    self.api_base = self.api_base[:-1]
                if "/chat/completions" in self.api_base:
                    self.api_base = self.api_base.replace("/chat/completions", "")
                if self.api_base.endswith('v1'):
                    self.api_base = f"{self.api_base}/"
                logger.info(f"检测到DashScope API，使用基础URL: {self.api_base}")
            openai.base_url = self.api_base
            logger.info(f"初始化LLM客户端，模型: {self.model}")
        except Exception as e:
            logger.error(f"初始化OpenAI客户端时出错: {e}", exc_info=True)
    
    async def generate(self, prompt: str, max_tokens: Optional[int] = None, 
                     temperature: Optional[float] = None, 
                     tools: Optional[List[Dict[str, Any]]] = None,
                     system_message: Optional[str] = None,
                     model: Optional[str] = None,
                     use_tool_model: Optional[str] = None) -> str:
        """
        生成文本
        
        Args:
            prompt: 提示词
            max_tokens: 最大生成长度，None表示使用默认值
            temperature: 温度参数，None表示使用默认值
            tools: 可用工具列表
            system_message: 系统消息
            
        Returns:
            str: 生成的文本
        """
        if not model:
            model = self.model
        prompt = self._truncate_prompt(prompt, system_message, model)
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        max_retries = 2
        retry_delay = 2
        if not use_tool_model:
            use_tool_model = self.use_tool_model
        
        for attempt in range(max_retries):
            try:
                params = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature if temperature is not None else self.temperature,
                    "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
                }
                if tools:
                    params["model"] = use_tool_model
                    params["tools"] = tools
                if "dashscope" in self.api_base:
                    params["stream"] = True
                    full_response = ""
                    logger.info(f"流式等待: {openai.base_url} {model}")
                    stream_resp = openai.chat.completions.create(**params)
                    for chunk in stream_resp:
                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
                            content = chunk.choices[0].delta.content
                            full_response += content
                    return full_response
                else:
                    logger.info(f"同步: {openai.base_url} {model}")
                    response = openai.chat.completions.create(**params)
                    return response.choices[0].message.content
            except Exception as e:
                logger.error(f"调用LLM API时出错 (尝试 {attempt+1}/{max_retries}): {e}", exc_info=True)
                if attempt < max_retries - 1:
                    sleep_time = retry_delay * (2 ** attempt)
                    logger.info(f"等待 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
                else:
                    logger.error("达到最大重试次数，无法获取LLM响应")
                    raise
    
    async def generate_with_streaming(self, prompt: str,
                                    max_tokens: Optional[int] = None,
                                    temperature: Optional[float] = None,
                                    system_message: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        流式生成文本
        
        Args:
            prompt: 提示词
            max_tokens: 最大生成长度
            temperature: 温度
            system_message: 系统消息
            
        Returns:
            AsyncGenerator[str, None]: 生成的文本流
        """
        prompt = self._truncate_prompt(prompt, system_message, self.model)
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "stream": True
        }
        logger.info(f"流式输出: {openai.base_url} {self.model}")
        try:
            stream_resp = openai.chat.completions.create(**params)
            for chunk in stream_resp:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta:
                        yield {
                            "content": delta.content if hasattr(delta, 'content') else "",
                            "reasoning_content": delta.reasoning_content if hasattr(delta, 'reasoning_content') else ""
                        }
        except Exception as e:
            logger.error(f"流式生成文本时出错: {e}", exc_info=True)
            try:
                logger.info("尝试使用非流式方式生成...")
                non_streaming_response = await self.generate(prompt, max_tokens, temperature, None, system_message)
                yield {
                    "content": non_streaming_response,
                    "reasoning_content": ""
                }
            except Exception as e2:
                logger.error(f"非流式生成文本时出错: {e2}", exc_info=True)

llm_client = LLMClient(api_key=app_config.llm.api_key, 
                       model=app_config.llm.model, 
                       api_base=app_config.llm.api_base)
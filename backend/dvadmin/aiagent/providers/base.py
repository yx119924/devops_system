# -*- coding: utf-8 -*-
"""供应商抽象基类：把不同厂商收敛到同一个 chat / test 接口。

新增厂商只需继承 BaseProvider 并在 get_provider() 里登记，Agent 侧不用改。
"""
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """模型请求调用某个工具。"""
    id: str
    name: str
    arguments: dict


@dataclass
class ChatResult:
    """一次模型调用的结果。"""
    content: str = ""
    tool_calls: list = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency: float = 0.0
    raw: dict = field(default_factory=dict)


class ProviderError(Exception):
    """调用大模型失败。message 是中文，可直接展示给用户。"""


class BaseProvider:
    def __init__(self, config):
        # config 是 AiProviderConfig 实例（已解密能力由 get_api_key 提供）
        self.config = config

    def chat(self, messages, tools=None, temperature=None, max_tokens=None):
        """发一轮对话。messages 为 OpenAI 格式，tools 为 function calling 定义。

        :return: ChatResult
        :raises ProviderError: 网络/鉴权/超时/格式异常
        """
        raise NotImplementedError

    def test(self):
        """连接测试。:return: dict(ok, latency, model, reply, error)"""
        raise NotImplementedError

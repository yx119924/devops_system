# -*- coding: utf-8 -*-
"""
OpenAI 兼容协议的供应商实现。

★ 刻意**不引入 openai SDK**，只用 requests 直调 `/chat/completions`：
  本项目的铁律是「requirements 变更必须重建 django + celery 两个镜像」，
  而重建 + docker save + 传输的代价远大于这几十行 HTTP 调用。
  零新依赖 = 上这个功能不用换后端镜像。

DeepSeek / 通义 / Kimi / 智谱 / 本地 vLLM、Ollama(OpenAI 兼容模式) 都走这一份实现。

----------------------------------------------------------------------
★ 2026-09-23 增补：DeepSeek V4 系列「思考模式」的处理（均为实测结论）

  1) `deepseek-chat` / `deepseek-reasoner` 已被官方于 2026-07-24 弃用；
     现役模型名 = `deepseek-flash`（快而省）与 `deepseek-v4-pro`（重推理）。
     ★ 模型名**大小写敏感**：填成 `DeepSeek-chat` 会直接 400。
  2) V4 系列**默认开启思考模式** —— 先输出 `reasoning_content`，再输出 `content`。
     实测 `max_tokens=16` 时 16 个 token 全被思考吃掉：`content` 为空、
     `finish_reason=length`。表现为「测试连接成功但回答是空的」，
     正式问答则像「AI 没反应」。max_tokens 给小了尤其危险。
  3) 关闭思考的唯一有效写法是 `"thinking": {"type": "disabled"}`
     （实测有效：prompt_tokens 35 → 9、正文正常）。
     `thinking_disabled` / `chat_template_kwargs` 两种写法**实测无效**，不要用。
  4) 该参数是 DeepSeek 专有的。为了不打坏其它 OpenAI 兼容服务：
     只对 `deepseek*` 模型发送；且若上游仍返回 400，**自动去掉该参数重发一次**。
  5) `tool_calls`（function calling）实测可用，故「智能问答」的 Agent 主链路不受以上影响。
----------------------------------------------------------------------
"""
import json
import logging
import time

import requests

from dvadmin.aiagent.providers.base import BaseProvider, ChatResult, ProviderError, ToolCall

logger = logging.getLogger(__name__)

# 连接超时固定 10s（快速失败）；读超时用配置里的 timeout
CONNECT_TIMEOUT = 10
MAX_ERROR_BODY = 300
# 连接测试用的 max_tokens。
# ★ 不能用原来的 16：思考模型会把这 16 个 token 全花在 reasoning_content 上，正文为空。
#   实测 max_tokens=128 时 reasoning≈53 + 正文 2，稳过；关思考后只需 1 个 token。
TEST_MAX_TOKENS = 128


class OpenAICompatProvider(BaseProvider):

    # ---------- 内部工具 ----------

    def _endpoint(self):
        base = (self.config.base_url or "").strip().rstrip("/")
        if not base:
            raise ProviderError("接口地址（base_url）未配置")
        if not base.startswith("http"):
            raise ProviderError("接口地址必须以 http:// 或 https:// 开头")
        return base + "/chat/completions"

    def _headers(self):
        key = self.config.get_api_key()
        if not key:
            raise ProviderError("该配置尚未填写 API Key")
        return {
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        }

    def _timeout(self):
        try:
            return max(5, int(self.config.timeout or 60))
        except (TypeError, ValueError):
            return 60

    def _thinking_disabled(self):
        """本次请求是否显式关闭思考模式。

        - **只对 DeepSeek 系模型**（`deepseek*`）下手，避免把 DeepSeek 专有参数
          发给通义 / Kimi / 本地 Ollama 等其它 OpenAI 兼容服务。
        - 配置对象将来若带 `enable_thinking=True`（重推理场景需要思考过程），
          则尊重配置。这里用 `getattr` 取默认 False ——
          所以「字段还没加」与「字段已加且为 False」行为完全一致。
        """
        if getattr(self.config, "enable_thinking", False):
            return False
        return (self.config.model or "").strip().lower().startswith("deepseek")

    def _build_payload(self, messages, tools, temperature, max_tokens, disable_thinking=None):
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature if temperature is None else temperature,
            "stream": False,
        }
        limit = max_tokens if max_tokens is not None else self.config.max_tokens
        if limit:
            payload["max_tokens"] = int(limit)
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if disable_thinking is None:
            disable_thinking = self._thinking_disabled()
        if disable_thinking:
            # 见文件头 3)：DeepSeek V4 关思考的唯一有效写法
            payload["thinking"] = {"type": "disabled"}
        return payload

    def _post(self, url, headers, payload, timeout):
        """发一次请求；把 requests 的各类异常统一翻译成中文 ProviderError。"""
        try:
            return requests.post(url, headers=headers, json=payload,
                                 timeout=(CONNECT_TIMEOUT, timeout))
        except requests.exceptions.Timeout:
            raise ProviderError("调用大模型超时（%ss），可到「模型配置」调大超时时间" % timeout)
        except requests.exceptions.SSLError as exc:
            raise ProviderError("HTTPS 证书校验失败，请检查网络代理：%s" % exc)
        except requests.exceptions.ConnectionError as exc:
            raise ProviderError("无法连接大模型接口（域名解析或网络不通）：%s" % exc)
        except requests.exceptions.RequestException as exc:
            raise ProviderError("调用大模型失败：%s" % exc)

    @staticmethod
    def _raise_for_status(resp):
        """把 HTTP 错误码翻译成用户能看懂的中文。"""
        code = resp.status_code
        if code < 400:
            return
        body = (resp.text or "")[:MAX_ERROR_BODY]
        table = {
            400: "请求被拒绝（400），通常是模型名不对或参数不合法",
            401: "API Key 无效或已过期（401）",
            402: "账户余额不足（402），请先充值",
            403: "无权访问该模型（403），请确认账号已开通",
            404: "接口地址不对（404），请检查 base_url 是否包含 /v1 之类的路径前缀",
            422: "参数校验失败（422）",
            429: "请求过于频繁或超出配额（429），请稍后重试",
        }
        hint = table.get(code)
        if code >= 500:
            hint = "大模型服务端异常（%s），请稍后重试" % code
        raise ProviderError("%s。接口返回：%s" % (hint or ("接口返回 %s" % code), body))

    # ---------- 对外接口 ----------

    def chat(self, messages, tools=None, temperature=None, max_tokens=None):
        url = self._endpoint()
        headers = self._headers()
        timeout = self._timeout()
        disable_thinking = self._thinking_disabled()

        started = time.time()
        resp = self._post(
            url, headers,
            self._build_payload(messages, tools, temperature, max_tokens,
                                disable_thinking=disable_thinking),
            timeout)

        # ★ 兜底：上游（某些中转站 / 网关）不认 DeepSeek 专有的 thinking 参数时会回 400。
        #   这时去掉该参数原样重发一次 —— 让「关思考」只是优化，不会把功能打挂。
        if resp.status_code == 400 and disable_thinking:
            logger.warning("上游拒绝 thinking 参数，去掉后重试一次：%s",
                           (resp.text or "")[:200])
            retry = self._post(
                url, headers,
                self._build_payload(messages, tools, temperature, max_tokens,
                                    disable_thinking=False),
                timeout)
            if retry.status_code < 400:
                resp = retry

        latency = round(time.time() - started, 2)
        self._raise_for_status(resp)

        try:
            data = resp.json()
        except ValueError:
            raise ProviderError("接口返回的不是 JSON，可能 base_url 指到了错误的服务：%s"
                                % (resp.text or "")[:MAX_ERROR_BODY])

        choices = data.get("choices") or []
        if not choices:
            message = (data.get("error") or {}).get("message") or "接口未返回 choices"
            raise ProviderError("大模型没有返回内容：%s" % message)

        message = choices[0].get("message") or {}
        finish_reason = choices[0].get("finish_reason") or ""
        usage = data.get("usage") or {}

        calls = []
        for item in (message.get("tool_calls") or []):
            fn = item.get("function") or {}
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
            except ValueError:
                # 模型偶尔会给出不合法 JSON，当作空参数并透传原文，交给 Agent 侧提示重试
                args = {"_raw": raw_args}
            calls.append(ToolCall(id=item.get("id") or "", name=fn.get("name") or "", arguments=args))

        content = message.get("content") or ""
        reasoning = (message.get("reasoning_content") or "").strip()

        # ★ 思考模型的坑：正文可能全在 reasoning_content 里、content 为空。
        #   此时**不能静默返回空串** —— 那会表现为「AI 没反应」，现场无从定位。
        #   换成可操作的中文提示。判据：只有「既没有正文、也没有工具调用」才算异常
        #   （模型只回 tool_calls 而不写客套话，属正常情况）。
        if not content.strip() and not calls:
            if reasoning:
                raise ProviderError(
                    "模型只返回了思考过程、正文为空（finish_reason=%s）。"
                    "通常是「最大输出 token」太小、思考还没结束就被截断："
                    "请到「模型配置」把「最大输出 token」调大，或改用不思考的模型。"
                    % (finish_reason or "unknown"))
            if finish_reason == "length":
                raise ProviderError(
                    "模型输出被「最大输出 token」截断且没有正文（finish_reason=length），"
                    "请到「模型配置」把「最大输出 token」调大。")

        return ChatResult(
            content=content,
            tool_calls=calls,
            prompt_tokens=usage.get("prompt_tokens") or 0,
            completion_tokens=usage.get("completion_tokens") or 0,
            total_tokens=usage.get("total_tokens") or 0,
            latency=latency,
            raw=data,
        )

    def test(self):
        """最小成本连通性测试：只让它回一个词。

        ★ max_tokens 必须给足（TEST_MAX_TOKENS）：思考模型会先把 token 花在
          reasoning_content 上，给小了正文就是空的 ——
          「测试连接」会「成功但回答没内容」，等于没测到东西。
        """
        try:
            result = self.chat(
                messages=[{"role": "user", "content": "只回复两个字：正常"}],
                tools=None,
                temperature=0,
                max_tokens=TEST_MAX_TOKENS,
            )
        except ProviderError as exc:
            return {"ok": False, "latency": 0, "model": self.config.model,
                    "reply": "", "error": str(exc)}
        return {
            "ok": True,
            "latency": result.latency,
            "model": self.config.model,
            "reply": (result.content or "").strip()[:80],
            "tokens": result.total_tokens,
            "error": "",
        }


def get_provider(config):
    """按 provider_type 返回对应实现。当前只有一种，留好扩展点。"""
    ptype = (getattr(config, "provider_type", "") or "openai_compat").lower()
    if ptype == "openai_compat":
        return OpenAICompatProvider(config)
    raise ProviderError("暂不支持的接口类型：%s" % ptype)

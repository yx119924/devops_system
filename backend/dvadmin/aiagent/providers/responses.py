# -*- coding: utf-8 -*-
"""OpenAI **Responses API**（`POST /v1/responses`）供应商实现。

----------------------------------------------------------------------
★ 为什么需要这个文件（2026-10-13 / 14 真机实证）

  公司 codex 网关（New API，`agent-team-api.myrilink.cn`）上的 `gpt-5.6-sol`
  **只开了 `openai-response` 端点**：
      POST /v1/chat/completions → 503 `No available channel … endpoint: openai`
      POST /v1/responses        → 200  ✅
      POST /v1/messages         → 503 `No available channel … endpoint: anthropic`
  网关是按「令牌分组 × 模型名 × **端点类型**」三要素路由渠道的，
  所以「模型名对、地址对、Key 对」也照样 503 —— 病根是**协议不对**。

★★ 实测结论（`deploy/_diag/_probe_responses_tools.py` 真机跑出来的，不是照抄官方文档）

  | 用例 | 结果 |
  |---|---|
  | P1 纯文本 | OK，正文在 `output[0].content[0].text`（`type == "output_text"`） |
  | P2 `instructions` + `temperature=0` | OK，两者都被接受 |
  | P3 tools 用**扁平**格式 | OK，返回 `{"type":"function_call","call_id":…,"name":…,"arguments":"{…}"}` |
  | P4 回传 `function_call_output` | OK ★ 关键：Agent 多轮工具调用走得通 |
  | P5 `input` 数组 + assistant 字符串 content | OK |

  其它要点：
    · `arguments` 是 **JSON 字符串**（与 chat completions 一致，不是对象）
    · 配对键是 **`call_id`**（不是 item 自己的 `id`）
    · usage 字段名是 `input_tokens` / `output_tokens` / `total_tokens`
      （**不是** chat 的 `prompt_tokens` / `completion_tokens`）
    · 实测**没有** `reasoning` item（`reasoning_tokens: 0`），但解析时仍做忽略容错
    · `base_url` 填到 `/v1` 为止，本类会拼 `/responses`
----------------------------------------------------------------------

★★ 设计约束：**`agent.py` 一行都不用改。**

  `base.py::BaseProvider.chat(messages, tools, temperature, max_tokens) -> ChatResult`
  是稳定契约，而 `agent.py` 全程只说 OpenAI-Chat 格式 ⇒
  **协议翻译全部关在本文件内部**：

      入：chat 格式 `messages` ──→ Responses 的 `input` + `instructions`
      出：Responses 的 `output[]` ──→ `ChatResult`

  继承 `OpenAICompatProvider` 只是为了复用 `_headers` / `_timeout` / `_post` /
  `_raise_for_status` 这几个**与协议无关**的零件（错误码文案也就两处一致），
  真正不同的三处全部覆盖：`_endpoint` / `_build_payload` / `chat` 的响应解析。
"""
import json
import time

from dvadmin.aiagent.providers.base import ChatResult, ProviderError, ToolCall
from dvadmin.aiagent.providers.openai_compat import (
    MAX_ERROR_BODY, OpenAICompatProvider)


class OpenAIResponsesProvider(OpenAICompatProvider):
    """`POST /v1/responses`（OpenAI Responses API）。"""

    # ---------------------------------------------------------------- 端点

    def _endpoint(self):
        base = (self.config.base_url or "").strip().rstrip("/")
        if not base:
            raise ProviderError("接口地址（base_url）未配置")
        if not base.startswith("http"):
            raise ProviderError("接口地址必须以 http:// 或 https:// 开头")
        return base + "/responses"

    # ---------------------------------------------------- messages → input

    def _translate_input(self, messages):
        """OpenAI-Chat 格式 `messages` → `(instructions, input_items)`。

        ★★ 顺序**原样保留**，一个都不能省：`function_call` 与它对应的
        `function_call_output` 是**按 `call_id` 配对**的，
        打乱顺序、或只留一半，上游直接报协议错误
        （`agent.py` 里 `_trim_messages()` 那段注释讲的就是同一件事）。

        映射规则（P4 / P5 实测确认）：

            {"role": "system",    "content": str}  →  instructions
            {"role": "user",      "content": str}  →  {"role": "user", "content": str}
            {"role": "assistant", "content": str,  →  有正文才给 {"role": "assistant", …}；
                                  "tool_calls":[…]}   每个 tool_call 给一个
                                                      {"type": "function_call", "call_id": …}
            {"role": "tool", "tool_call_id": str,  →  {"type": "function_call_output",
                           "content": str}             "call_id": …, "output": str}
        """
        instructions = []
        items = []

        for msg in (messages or []):
            role = msg.get("role")
            content = msg.get("content")

            if role == "system":
                if content:
                    instructions.append(content if isinstance(content, str)
                                        else json.dumps(content, ensure_ascii=False))
                continue

            if role == "user":
                items.append({"role": "user",
                              "content": content if isinstance(content, str)
                              else json.dumps(content, ensure_ascii=False)})
                continue

            if role == "assistant":
                # 正文非空才产出 message —— 纯工具调用轮次没有正文，产出空 message
                # 反而可能被上游判为非法（P3 的响应里就只有 function_call，没有 message）
                if isinstance(content, str) and content.strip():
                    items.append({"role": "assistant", "content": content})
                for call in (msg.get("tool_calls") or []):
                    fn = call.get("function") or {}
                    items.append({
                        "type": "function_call",
                        "call_id": call.get("id") or "",
                        "name": fn.get("name") or "",
                        # ★ 保持**字符串**形态，别 json.loads 再 dumps —— 上游要的就是字符串
                        "arguments": fn.get("arguments") or "{}",
                    })
                continue

            if role == "tool":
                items.append({
                    "type": "function_call_output",
                    "call_id": msg.get("tool_call_id") or "",
                    "output": content if isinstance(content, str)
                    else json.dumps(content, ensure_ascii=False),
                })
                continue

            # 未知角色：原样透传，**不静默丢弃**（丢了会连累后面所有配对）
            items.append({"role": role, "content": content})

        merged = "\n\n".join(instructions) if instructions else None
        return merged, items

    # ----------------------------------------------------- tools 扁平化

    def _translate_tools(self, tools):
        """chat 的**嵌套**工具定义 → Responses 的**扁平**工具定义（P3 实测通过）。

            {"type":"function","function":{"name","description","parameters"}}
              ↓
            {"type":"function","name","description","parameters"}

        ★ 已经是扁平格式的原样放行 —— 这样将来 agent 侧若改用新格式也不会坏。
        """
        out = []
        for item in (tools or []):
            fn = item.get("function")
            if not fn:
                out.append(item)                       # 已是扁平 / 其它类型，原样
                continue
            flat = {"type": "function", "name": fn.get("name") or ""}
            if fn.get("description"):
                flat["description"] = fn["description"]
            # parameters 缺失时给个合法空壳：上游对它是否必填比较敏感
            flat["parameters"] = fn.get("parameters") or {"type": "object", "properties": {}}
            out.append(flat)
        return out

    # --------------------------------------------------------- 请求体

    def _build_payload(self, messages, tools, temperature, max_tokens):
        instructions, items = self._translate_input(messages)

        payload = {"model": self.config.model, "input": items}
        if instructions:
            payload["instructions"] = instructions

        limit = max_tokens if max_tokens is not None else self.config.max_tokens
        if limit:
            # ★ 名字和 chat 不一样：这里是 max_output_tokens
            payload["max_output_tokens"] = int(limit)

        temp = self.config.temperature if temperature is None else temperature
        if temp is not None:
            payload["temperature"] = temp        # P2 实测被接受

        if tools:
            payload["tools"] = self._translate_tools(tools)
            payload["tool_choice"] = "auto"

        # 不发 `thinking` / `reasoning` —— 实测该网关不需要（reasoning_tokens=0），
        # 多发反而可能被拒。DeepSeek 专有的 `thinking` 参数是 chat 协议那边的事。
        return payload

    # --------------------------------------------------------- 响应解析

    def _parse_response(self, data, latency):
        """`output[]` → `ChatResult`。"""
        content_parts = []
        calls = []

        for item in (data.get("output") or []):
            itype = item.get("type")

            if itype == "message":
                for block in (item.get("content") or []):
                    if block.get("type") == "output_text" and block.get("text"):
                        content_parts.append(block["text"])

            elif itype == "function_call":
                raw_args = item.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except ValueError:
                    # 模型偶尔给出不合法 JSON：当作空参并透传原文，交给 Agent 侧提示重试
                    args = {"_raw": raw_args}
                calls.append(ToolCall(
                    # ★ 用 call_id：回传 function_call_output 时要的就是它
                    id=item.get("call_id") or "",
                    name=item.get("name") or "",
                    arguments=args,
                ))

            # reasoning / 其它类型：忽略（实测未出现，但留着容错）

        content = "".join(content_parts)
        usage = data.get("usage") or {}
        prompt_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        completion_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or 0
        total_tokens = usage.get("total_tokens") or (prompt_tokens + completion_tokens)

        # ★ 与 chat 协议同一套判据：只有「既没正文、也没工具调用」才算异常。
        #   模型只回 function_call 而不写客套话是**正常**的，别误判。
        if not content.strip() and not calls:
            status = data.get("status") or "unknown"
            reason = ((data.get("incomplete_details") or {}).get("reason") or "")
            hint = ""
            if reason or status == "incomplete":
                hint = ("（status=%s%s）。若原因是 max_output_tokens，"
                        "请到「模型配置」把「最大输出 token」调大。"
                        % (status, ("，reason=" + reason) if reason else ""))
            raise ProviderError("模型没有返回正文也没有工具调用%s" % (hint or "。"))

        return ChatResult(
            content=content,
            tool_calls=calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency=latency,
            raw=data,
        )

    # --------------------------------------------------------- 对外接口

    def chat(self, messages, tools=None, temperature=None, max_tokens=None):
        url = self._endpoint()
        headers = self._headers()
        timeout = self._timeout()

        started = time.time()
        resp = self._post(url, headers,
                          self._build_payload(messages, tools, temperature, max_tokens),
                          timeout)
        latency = round(time.time() - started, 2)
        self._raise_for_status(resp)

        try:
            data = resp.json()
        except ValueError:
            raise ProviderError("接口返回的不是 JSON，可能 base_url 指到了错误的服务：%s"
                                % (resp.text or "")[:MAX_ERROR_BODY])

        return self._parse_response(data, latency)

    # test() 直接继承父类：它就是「发一句最小对话看有没有正常回答」，
    # 与协议无关 —— 父类会走 self.chat()，于是自动用上本类的翻译逻辑。

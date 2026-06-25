"""对象式 API 示例,演示把散落的 build_xxx(context=...) 收敛为单一请求对象。"""

import json
from time import time
from typing import Final, Literal, Self, cast
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer


DESKTOP_USER_AGENT: Final[str] = (
    "Codex Desktop/0.142.0 (Windows 10.0.19044; x86_64) "
    "unknown (Codex Desktop; 26.616.71553)"
)

type ToolChoice = Literal["auto", "none", "required"]
type ReasoningEffort = Literal["minimal", "low", "medium", "high", "xhigh"]
type TextVerbosity = Literal["low", "medium", "high"]


class GatewayTurnMetadata(BaseModel):
    """网关请求轮次元数据模型,承载请求身份、窗口和工作区语义。"""

    installation_id: str = Field(description="客户端安装标识。")
    session_id: str = Field(description="当前会话标识。")
    thread_id: str = Field(description="当前线程标识。")
    turn_id: str = Field(description="当前请求轮次标识。")
    window_id: str = Field(description="客户端窗口标识。")
    request_kind: Literal["turn"] = Field(default="turn", description="请求类型。")
    thread_source: Literal["user"] = Field(default="user", description="线程来源。")
    sandbox: Literal["none"] = Field(default="none", description="沙箱模式。")
    turn_started_at_unix_ms: int = Field(description="请求开始时间戳,单位为毫秒。")
    workspace_kind: Literal["project"] = Field(default="project", description="工作区类型。")


class GatewayHeaders(BaseModel):
    """网关请求头模型,仅在最终外部调用边界序列化为字典。"""

    user_agent: str = Field(
        default=DESKTOP_USER_AGENT,
        serialization_alias="User-Agent",
        description="请求协议要求的客户端用户代理。",
    )
    accept: Literal["text/event-stream"] = Field(
        default="text/event-stream",
        serialization_alias="Accept",
        description="Responses 流式响应格式。",
    )
    beta_features: Literal["remote_compaction_v2"] = Field(
        default="remote_compaction_v2",
        serialization_alias="x-codex-beta-features",
        description="请求网关启用的实验能力。",
    )
    window_id: str = Field(serialization_alias="x-codex-window-id", description="客户端窗口标识。")
    turn_metadata: GatewayTurnMetadata = Field(
        serialization_alias="x-codex-turn-metadata",
        description="最终外部边界需要渲染为压缩 JSON 的 turn 元数据。",
    )
    client_request_id: str = Field(serialization_alias="x-client-request-id", description="客户端请求标识。")
    session_id: str = Field(serialization_alias="session-id", description="当前会话标识。")
    thread_id: str = Field(serialization_alias="thread-id", description="当前线程标识。")
    originator: Literal["Codex Desktop"] = Field(
        default="Codex Desktop",
        serialization_alias="originator",
        description="请求来源产品名称。",
    )

    @field_serializer("turn_metadata")
    def _serialize_turn_metadata(self, turn_metadata: GatewayTurnMetadata) -> str:
        """
        在最终外部调用边界把 turn 元数据渲染为压缩 JSON 字符串。

        Args:
            turn_metadata: 语义化的请求轮次元数据模型。

        Returns:
            str: 可放入 x-codex-turn-metadata 请求头的压缩 JSON 字符串。
        """
        return json.dumps(
            turn_metadata.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            separators=(",", ":"),
        )


class GatewayClientMetadata(BaseModel):
    """网关请求体客户端元数据模型,表达 Responses 网关需要的身份字段。"""

    turn_id: str = Field(description="当前请求轮次标识。")
    window_id: str = Field(serialization_alias="x-codex-window-id", description="客户端窗口标识。")
    turn_metadata: GatewayTurnMetadata = Field(
        serialization_alias="x-codex-turn-metadata",
        description="最终外部边界需要渲染为压缩 JSON 的 turn 元数据。",
    )
    session_id: str = Field(description="当前会话标识。")
    thread_id: str = Field(description="当前线程标识。")
    installation_id: str = Field(
        serialization_alias="x-codex-installation-id",
        description="客户端安装标识。",
    )

    @field_serializer("turn_metadata")
    def _serialize_turn_metadata(self, turn_metadata: GatewayTurnMetadata) -> str:
        """
        在最终外部调用边界把 turn 元数据渲染为压缩 JSON 字符串。

        Args:
            turn_metadata: 语义化的请求轮次元数据模型。

        Returns:
            str: 可放入 x-codex-turn-metadata 请求体字段的压缩 JSON 字符串。
        """
        return json.dumps(
            turn_metadata.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            separators=(",", ":"),
        )


class GatewayExtraBody(BaseModel):
    """网关 Responses 扩展请求体模型,封装工具选择和客户端元数据。"""

    tool_choice: ToolChoice = Field(description="Responses 工具选择模式。")
    client_metadata: GatewayClientMetadata = Field(description="网关客户端元数据。")
    include: list[Literal["reasoning.encrypted_content"]] | None = Field(
        default=None,
        description="需要额外返回的 Responses 内容。",
    )


class PydanticAIModelSettings(BaseModel):
    """Pydantic AI 模型设置契约,在最终外部调用边界转为字典。"""

    openai_reasoning_effort: ReasoningEffort = Field(description="OpenAI Responses 推理强度。")
    openai_store: bool = Field(description="是否要求服务端保存响应。")
    openai_text_verbosity: TextVerbosity = Field(description="OpenAI Responses 文本详细程度。")
    openai_prompt_cache_key: str = Field(description="提示缓存键。")
    parallel_tool_calls: bool = Field(description="是否允许模型并行调用工具。")
    extra_headers: GatewayHeaders = Field(description="传给 Pydantic AI 的额外请求头。")
    extra_body: GatewayExtraBody = Field(description="传给 Pydantic AI 的额外请求体。")

    def as_external_call_dict(self) -> dict[str, object]:
        """
        将模型设置序列化为最终外部调用接收的字典。

        Args:
            无。

        Returns:
            dict[str, object]: 仅用于最终外部调用边界的模型设置字典。
        """
        return cast(
            dict[str, object],
            self.model_dump(mode="json", by_alias=True, exclude_none=True),
        )


class GatewayResponsesRequest(BaseModel):
    """网关 Responses 请求对象,封装一次请求的身份字段和派生配置。"""

    model_config = ConfigDict(frozen=True)

    installation_id: str = Field(description="客户端安装标识。")
    session_id: str = Field(description="会话和线程共享的稳定标识。")
    turn_id: str = Field(description="当前请求轮次标识。")
    started_at_unix_ms: int = Field(description="请求开始时间戳,单位为毫秒。")

    @classmethod
    def create(
        cls,
        *,
        session_id: str | None = None,
        turn_id: str | None = None,
        installation_id: str | None = None,
        started_at_unix_ms: int | None = None,
    ) -> Self:
        """
        创建网关 Responses 请求对象,自动补齐缺失的身份字段和开始时间。

        Args:
            session_id: 会话和线程标识,省略时自动生成。
            turn_id: 单次请求标识,省略时自动生成。
            installation_id: 安装标识,省略时自动生成。
            started_at_unix_ms: 请求开始时间戳,单位为毫秒,省略时使用当前时间。

        Returns:
            Self: 已补齐身份字段的请求对象。
        """
        resolved_started_at = started_at_unix_ms
        if resolved_started_at is None:
            resolved_started_at = int(time() * 1000)

        return cls(
            installation_id=installation_id or str(uuid4()),
            session_id=session_id or str(uuid4()),
            turn_id=turn_id or str(uuid4()),
            started_at_unix_ms=resolved_started_at,
        )

    @property
    def thread_id(self) -> str:
        """
        返回请求线程标识,当前实现与 session_id 保持一致。

        Args:
            无。

        Returns:
            str: 当前请求所属线程标识。
        """
        return self.session_id

    @property
    def window_id(self) -> str:
        """
        返回客户端窗口标识,用于请求头和请求体元数据。

        Args:
            无。

        Returns:
            str: 由 session_id 派生出的窗口标识。
        """
        return f"{self.session_id}:0"

    def turn_metadata(self) -> GatewayTurnMetadata:
        """
        生成网关 turn 元数据模型,供请求头和请求体复用。

        Args:
            无。

        Returns:
            GatewayTurnMetadata: 当前请求的身份和工作区元数据模型。
        """
        return GatewayTurnMetadata(
            installation_id=self.installation_id,
            session_id=self.session_id,
            thread_id=self.thread_id,
            turn_id=self.turn_id,
            window_id=self.window_id,
            turn_started_at_unix_ms=self.started_at_unix_ms,
        )

    def headers(self) -> GatewayHeaders:
        """
        生成网关风格请求头模型,供最终外部调用边界序列化。

        Args:
            无。

        Returns:
            GatewayHeaders: Pydantic AI extra_headers 的请求头模型。
        """
        return GatewayHeaders(
            window_id=self.window_id,
            turn_metadata=self.turn_metadata(),
            client_request_id=self.session_id,
            session_id=self.session_id,
            thread_id=self.thread_id,
        )

    def client_metadata(self) -> GatewayClientMetadata:
        """
        生成 Responses 请求体中的 client_metadata 模型。

        Args:
            无。

        Returns:
            GatewayClientMetadata: 网关形态请求体使用的客户端元数据模型。
        """
        return GatewayClientMetadata(
            turn_id=self.turn_id,
            window_id=self.window_id,
            turn_metadata=self.turn_metadata(),
            session_id=self.session_id,
            thread_id=self.thread_id,
            installation_id=self.installation_id,
        )

    def extra_body(
        self,
        *,
        tool_choice: ToolChoice = "auto",
        include_encrypted_reasoning: bool = True,
    ) -> GatewayExtraBody:
        """
        生成网关专用 Responses 请求体扩展模型。

        Args:
            tool_choice: 工具选择模式,传给 Responses 网关。
            include_encrypted_reasoning: 是否请求返回加密 reasoning 内容。

        Returns:
            GatewayExtraBody: Pydantic AI extra_body 的请求体扩展模型。
        """
        include = ["reasoning.encrypted_content"] if include_encrypted_reasoning else None
        return GatewayExtraBody(
            tool_choice=tool_choice,
            client_metadata=self.client_metadata(),
            include=include,
        )

    def model_settings(
        self,
        *,
        reasoning_effort: ReasoningEffort = "xhigh",
        store: bool = False,
        text_verbosity: TextVerbosity = "low",
        parallel_tool_calls: bool = True,
    ) -> PydanticAIModelSettings:
        """
        生成调用网关形态 Responses 接口所需的模型配置模型。

        Args:
            reasoning_effort: 推理强度,传给 OpenAIResponsesModel。
            store: 是否要求服务端保存响应。
            text_verbosity: 文本详细程度,传给 OpenAIResponsesModel。
            parallel_tool_calls: 是否允许模型并行调用工具。

        Returns:
            PydanticAIModelSettings: 仅在最终外部调用边界序列化的模型设置。
        """
        return PydanticAIModelSettings(
            openai_reasoning_effort=reasoning_effort,
            openai_store=store,
            openai_text_verbosity=text_verbosity,
            openai_prompt_cache_key=self.session_id,
            parallel_tool_calls=parallel_tool_calls,
            extra_headers=self.headers(),
            extra_body=self.extra_body(),
        )


# Anti-pattern reference only:
# context = create_gateway_request_context()
# headers = build_gateway_headers(context=context)
# metadata = build_gateway_client_metadata(context=context)
# extra_body = build_gateway_extra_body(context=context)
# settings = build_gateway_model_settings(context=context)
#
# Prefer:
# request = GatewayResponsesRequest.create()
# settings = request.model_settings()
# client.responses.create(**settings.as_external_call_dict())


__all__ = [
    "GatewayClientMetadata",
    "GatewayExtraBody",
    "GatewayHeaders",
    "GatewayResponsesRequest",
    "GatewayTurnMetadata",
    "PydanticAIModelSettings",
]

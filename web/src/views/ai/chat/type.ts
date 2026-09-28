/**
 * 智能问答 —— 类型定义
 *
 * 与后端 `dvadmin/aiagent/{views,agent,tools}.py` 的返回结构一一对应。
 * 字段名改动时**必须同步改这个文件**，否则页面会静默显示空（TS 是唯一防线）。
 */

// ---------------------------------------------------------------- 下拉与护栏现状
export interface ChatCredential {
	id: number;
	name: string;
	username: string;
	auth_type: string; // password | private_key
	/** 绑定的服务器 id；null = 通用凭据（可用于任何有授权的机器） */
	server: number | null;
}

export interface ChatProviderOption {
	id: number;
	name: string;
	model: string;
	is_default: boolean;
}

export interface ChatUsage {
	day: string;
	rounds: number;
	round_limit: number;
	tokens: number;
	token_limit: number;
	requests: number;
}

export interface ChatGuardState {
	readonly_mode: boolean;
	enabled_tools: boolean;
	desensitize: boolean;
	max_rounds: number;
	chat_timeout: number;
	command_timeout: number;
	max_servers: number;
	/** 白名单样例（前 15 条），给用户一个"AI 能跑什么"的直观印象 */
	allowed_sample: string[];
}

export interface ChatOptions {
	credentials: ChatCredential[];
	providers: ChatProviderOption[];
	/** number = 可操作台数；'all' = 资产运营者/超管（不限） */
	server_count: number | string;
	usage: ChatUsage;
	guard: ChatGuardState;
}

// ---------------------------------------------------------------- 会话
export interface ChatSessionBrief {
	id: number;
	title: string;
	credential_name: string | null;
	provider_name: string | null;
	rounds: number;
	tool_count: number;
	total_tokens: number;
	status: string; // active | failed
	create_datetime: string;
	update_datetime: string;
}

/**
 * 会话详情。
 *
 * ★ `messages` 是**原始 OpenAI 协议消息**（system / user / assistant / tool 四种），
 *   不是渲染好的气泡。页面负责把它压成 `ChatItem[]`（见 index.vue 的 buildItems）。
 *   之所以不在后端转好：`tool_calls` 与 `tool` 消息靠 `tool_call_id` 配对，
 *   一旦后端拍平就再也拼不回"哪条命令对应哪段输出"。
 */
export interface ChatSessionDetail {
	id: number;
	title: string;
	messages: ChatMessage[];
	readonly: boolean;
	rounds: number;
	tool_count: number;
	total_tokens: number;
	status: string;
	last_error: string;
	credential: number | null;
	provider: number | null;
	credential_name: string | null;
	provider_name: string | null;
	create_datetime: string;
	update_datetime: string;
}

export interface ChatMessageToolCall {
	id: string;
	type: string;
	function: { name: string; arguments: string };
}

export interface ChatMessage {
	role: 'system' | 'user' | 'assistant' | 'tool';
	content: string;
	tool_calls?: ChatMessageToolCall[];
	tool_call_id?: string;
	name?: string;
}

// ---------------------------------------------------------------- 工具调用
export interface ToolTarget {
	server_id: number;
	server: string;
	ip: string;
	status: string; // success | empty | failed | error | blocked
	exit_code?: number | null;
	duration?: number;
	stdout?: string;
	stderr?: string;
	error?: string;
}

/** list_servers / run_readonly_command 统一的结果体（tools.py 的 _dump 输出） */
export interface ToolResult {
	ok: boolean;
	error?: string;
	// run_readonly_command
	command?: string;
	summary?: { success: number; total: number };
	targets?: ToolTarget[];
	// list_servers
	total_matched?: number;
	returned?: number;
	servers?: Array<Record<string, any>>;
	hint?: string;
}

/** 页面渲染用的扁平消息项 */
export interface ChatItem {
	role: 'user' | 'assistant' | 'hint';
	text: string;
	calls?: ToolCallCard[];
}

export interface ToolCallCard {
	id: string;
	name: string;
	args: Record<string, any>;
	/** tool 消息还没回填时为 true */
	loading: boolean;
	result: ToolResult | null;
	/** tool 消息的 content 不是合法 JSON 时原样放这里 */
	raw?: string;
}

// ---------------------------------------------------------------- 提问
export interface SendPayload {
	message: string;
	session_id?: number | null;
	credential_id?: number | null;
	provider_id?: number | null;
}

export interface SendResult {
	session_id: number;
	answer: string;
	rounds: number;
	tools: number;
	tokens: number;
	elapsed: number;
	stop_reason: string; // answered | max_rounds | timeout
	/** 本次提问里是否触发了脱敏（用来提示用户"你输入里的敏感值已被打码"） */
	desensitized: boolean;
	tool_trace: Array<Record<string, any>>;
	usage: ChatUsage;
}

// ---------------------------------------------------------------- 台账
export interface ToolCallRecord {
	id: number;
	session: number;
	owner: number | null;
	owner_label?: string;
	round_index: number;
	tool_name: string;
	server: number | null;
	server_label: string;
	ip: string;
	command: string;
	purpose: string;
	status: string; // success | empty | failed | rejected | blocked | error
	reject_reason: string;
	exit_code: number | null;
	duration: number | null;
	stdout_excerpt: string;
	stderr_excerpt: string;
	desensitized: string;
	create_datetime: string;
}

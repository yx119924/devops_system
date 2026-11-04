/**
 * 智能问答 —— 接口封装
 *
 * ★ 前缀只在 baseURL 里出现一次：生产为 `/devops`（见 web/.env.production），
 *   这里只写业务段 `/aiagent/...`。nginx 用 `rewrite ^/devops/(.*)$ /$1 break;`
 *   剥掉外层前缀后，django 侧收到的就是 `/aiagent/...`，正好命中后端路由。
 */
import { request } from '/@/utils/service';
import type { ChatOptions, ChatSessionBrief, ChatSessionDetail, SendPayload, SendResult, ToolCallRecord } from './type';

export const chatPrefix = '/aiagent/chat/';
export const toolCallPrefix = '/aiagent/toolcall/';

/**
 * 单次提问的等待上限。
 *
 * 后端 `AiGuardConfig.chat_timeout` 默认 90s；网关（overlay/nginx/my.conf）
 * `proxy_read_timeout` 是 600s。这里取 300s —— 比后端预算宽裕、比网关窄，
 * 保证**前端先超时**能给出可读提示，而不是等 nginx 丢回来一个 504 白页。
 */
const SEND_TIMEOUT = 300000;

/** 新建会话需要的下拉 + 护栏/配额现状 */
export function GetOptions() {
	return request({ url: chatPrefix + 'options/', method: 'get' });
}

/** 我的会话列表（分页；不含 messages） */
export function GetSessions(params?: any) {
	return request({ url: chatPrefix, method: 'get', params });
}

/** 会话详情（含完整 messages，用于回放） */
export function GetSession(id: number) {
	return request({ url: chatPrefix + id + '/', method: 'get' });
}

/**
 * 提问。
 *
 * ★ 同步阻塞返回最终回答（与「命令下发」的 execute 同一惯例），不是流式、不用轮询。
 *   所以必须给足超时时间，否则长排查会被前端提前掐断。
 */
export function SendMessage(data: SendPayload) {
	return request({ url: chatPrefix + 'send/', method: 'post', data, timeout: SEND_TIMEOUT });
}

/** 删除会话（连带会话内的消息一起清掉） */
export function DelSession(id: number) {
	return request({ url: chatPrefix + id + '/', method: 'delete', data: { id } });
}

/** 某会话的工具调用台账 */
export function GetSessionToolCalls(id: number) {
	return request({ url: chatPrefix + id + '/tool_calls/', method: 'get' });
}

/** 全量台账（超管看全部、其余只看自己） */
export function GetToolCalls(params?: any) {
	return request({ url: toolCallPrefix, method: 'get', params });
}

export type { ChatOptions, ChatSessionBrief, ChatSessionDetail, SendPayload, SendResult, ToolCallRecord };

import { request } from '/@/utils/service';

/**
 * ★★ 必须显式传 timeout：`/@/utils/service.ts` 的 `createRequestFunction` 里
 *    `configDefault.timeout = 5000`，经 `Object.assign` **覆盖**了 axios 实例上的 20000
 *    ⇒ 全局 `request()` 的默认超时只有 **5s**。
 *
 *    日志检索必然 >5s：单日一个 ES 索引就有上亿条（aichem-service-log-2026.10.05
 *    = 39.3GB / 1.17 亿条），不限定时间范围时一次要扫 22 个索引。
 *    而后端 `dvadmin/log/views/source.py` 给 ES 的是 `requests.post(..., timeout=20)`。
 *
 *    ⇒ 外层 5s < 内层 20s 是**错的**：前端会先断开，把后端那句中文错误
 *      「ES 请求超时（20s）」永远埋掉，用户只看到 axios 原文
 *      `timeout of 5000ms exceeded`（本项目已踩过 3 次：Jenkins 拉取、权限面板、这里）。
 *
 *    ★ 原则：**外层超时必须 > 内层超时**。这里给 30s（> 后端 20s + nginx 600s 之下），
 *      真超时时用户看到的是后端友好的中文文案，而不是裸的 axios 报错。
 *      注意：Jenkins 那次是「把内层压到 <5s」，这里压不下去（上亿条文档），
 *      只能反向「把外层放大」——同一个 5000ms，两种相反解法。
 */
const ES_QUERY_TIMEOUT = 30000;

export function GetEsList() {
	return request({ url: '/api/log/es/all/', method: 'get' });
}

/** 索引模式列表（滚动索引已归并成通配模式） */
export function GetEsIndices(id: number, keyword?: string) {
	return request({ url: `/api/log/es/${id}/indices/`, method: 'get', params: { keyword }, timeout: ES_QUERY_TIMEOUT });
}

export function SearchLogs(id: number, params: any) {
	return request({ url: `/api/log/es/${id}/search/`, method: 'post', data: params, timeout: ES_QUERY_TIMEOUT });
}

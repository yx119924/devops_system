import { request } from '/@/utils/service';
import { PageQuery, InfoReq } from '@fast-crud/fast-crud';

/**
 * ★ 路径前缀说明同 pipeline/api.ts：这里带一层 /api，配合 nginx 的 rewrite 刚好命中
 *   django 的 `/api/release/run/`。别改成一层。
 */
export const apiPrefix = '/api/release/run/';

export function GetList(query: PageQuery) {
	return request({ url: apiPrefix, method: 'get', params: query });
}

export function GetObj(id: InfoReq) {
	return request({ url: apiPrefix + id + '/', method: 'get' });
}

/**
 * 推进一个节点。
 *
 * ★★ 必须显式传 timeout：`/@/utils/service.ts` 里 `request()` 的默认超时只有 **5000ms**，
 *    而一个节点要 SSH 到目标机执行命令（单台最长 300 秒）、或者等 Jenkins 构建完
 *    （最长 600 秒）。不传 timeout 的话，前端会在第 5 秒报"请求超时"，
 *    而后端其实还在正常执行 —— 这是本项目已经踩过的坑（Jenkins 拉取那次）。
 */
export function Advance(id: number, timeout = 900000) {
	return request({ url: apiPrefix + id + '/advance/', method: 'post', data: {}, timeout });
}

export function Abort(id: number) {
	return request({ url: apiPrefix + id + '/abort/', method: 'post', data: {} });
}

export function Retry(id: number) {
	return request({ url: apiPrefix + id + '/retry/', method: 'post', data: {} });
}

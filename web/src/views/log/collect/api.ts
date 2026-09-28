import { request } from '/@/utils/service';
import { PageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

/**
 * ★ 路径前缀说明：这里写的是 `/api/log/collect/`（**带一层 /api**）。
 * 前端 baseURL 也是 `/api`，所以实际请求是 `/api/api/log/collect/`；
 * nginx 的 `rewrite ^/api/(.*)$ /$1 break;` 会削掉一层 → django 收到
 * `/api/log/collect/`，正好命中后端路由。这是本项目既定写法，
 * 别"顺手改成一层"—— 改了会 404。
 */
export const apiPrefix = '/api/log/collect/';

export function GetList(query: PageQuery) {
	return request({ url: apiPrefix, method: 'get', params: query });
}

export function GetObj(id: InfoReq) {
	return request({ url: apiPrefix + id + '/', method: 'get' });
}

export function AddObj(obj: AddReq) {
	return request({ url: apiPrefix, method: 'post', data: obj });
}

export function UpdateObj(obj: EditReq) {
	return request({ url: apiPrefix + obj.id + '/', method: 'put', data: obj });
}

export function DelObj(id: DelReq) {
	return request({ url: apiPrefix + id + '/', method: 'delete', data: { id } });
}

/** 启用中的采集任务（下拉） */
export function GetAll() {
	return request({ url: apiPrefix + 'all/', method: 'get' });
}

/** 页面下拉：ES 数据源 / 凭据 / 级别选项 */
export function GetOptions() {
	return request({ url: apiPrefix + 'options/', method: 'get' });
}

/** CMDB 服务器下拉（复用命令下发那份，已按资产授权过滤） */
export function GetServerOptions() {
	return request({ url: '/api/cmdb/server/dispatch_options/', method: 'get' });
}

/** ES 数据源下拉 */
export function GetEsSources() {
	return request({ url: '/api/log/es/all/', method: 'get' });
}

/** 环境检测（只读）。不传 serverId 则对所有目标执行 */
export function Detect(id: number, serverId?: number) {
	return request({ url: apiPrefix + id + '/detect/', method: 'post', data: serverId ? { server_id: serverId } : {} });
}

/** 下发配置片段 */
export function ApplyCfg(id: number, serverId?: number) {
	return request({ url: apiPrefix + id + '/apply/', method: 'post', data: serverId ? { server_id: serverId } : {} });
}

/** 停止采集（删除目标机上的片段） */
export function StopCfg(id: number, serverId?: number) {
	return request({ url: apiPrefix + id + '/stop/', method: 'post', data: serverId ? { server_id: serverId } : {} });
}

/** 规则试跑（只读，抓样本跑过滤） */
export function Preview(id: number, lines = 200, serverId?: number) {
	return request({ url: apiPrefix + id + '/preview/', method: 'post', data: { lines, server_id: serverId } });
}

/** 操作台账 */
export function GetRecords(id: number, page = 1, limit = 20) {
	return request({ url: apiPrefix + id + '/records/', method: 'get', params: { page, limit } });
}

/** 目标机主配置待补内容（只读文本） */
export function GetMainPatch(id: number) {
	return request({ url: apiPrefix + id + '/main_patch/', method: 'get' });
}

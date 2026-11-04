import { request } from '/@/utils/service';
import { PageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

/**
 * ★ 路径前缀说明：外层前缀统一由 baseURL 承担（生产 `/devops`），
 * 这里只写业务段 `/release/pipeline/`，实际请求是 `/devops/release/pipeline/`；
 * nginx 的 `rewrite ^/devops/(.*)$ /$1 break;` 剥掉外层后，django 收到
 * `/release/pipeline/`，命中后端 `path("release/...")`。
 */
export const apiPrefix = '/release/pipeline/';

/** CMDB 服务器下拉（复用命令下发那份，已按资产授权过滤） */
export const serverOptionsUrl = '/cmdb/server/dispatch_options/';

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

/** 启用中的流水线（下拉） */
export function GetAll() {
	return request({ url: apiPrefix + 'all/', method: 'get' });
}

/** 页面下拉：凭据 / Jenkins 服务器 / 通知渠道 / 节点类型 / 上限 */
export function GetOptions() {
	return request({ url: apiPrefix + 'options/', method: 'get' });
}

/** CMDB 服务器下拉 */
export function GetServerOptions() {
	return request({ url: serverOptionsUrl, method: 'get' });
}

/** 读取编排 */
export function GetNodes(id: number) {
	return request({ url: apiPrefix + id + '/nodes/', method: 'get' });
}

/** 保存编排（整体替换 + 后端按数组顺序重排序号） */
export function SaveNodes(id: number, nodes: any[]) {
	return request({ url: apiPrefix + id + '/nodes/', method: 'post', data: { nodes } });
}

/** 发起一次执行 */
export function RunPipeline(id: number, params: Record<string, any>) {
	return request({ url: apiPrefix + id + '/run/', method: 'post', data: { params } });
}

/**
 * 节点预检（**不真执行**）。
 * ★ 预检只回显占位符替换结果与目标解析情况；真正执行走「发起执行」。
 */
export function PreviewNode(payload: any) {
	return request({ url: '/release/node/preview/', method: 'post', data: payload });
}

/**
 * 某个 Jenkins 服务器上的 Job 列表（构建节点的下拉）。
 *
 * ★ 复用 Jenkins 模块已有的接口，它已经按**当前用户的目录授权**过滤过了
 *   —— 分环境授权（dev/test/pre/prod）在这里同样生效，不用重写一遍。
 *   拉不到时前端退化成"直接输入 Job 路径"，不阻断编排。
 */
export function GetJobs(serverId: number) {
	return request({ url: `/jenkins/server/${serverId}/jobs/`, method: 'get' });
}

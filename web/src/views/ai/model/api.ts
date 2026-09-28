import { request } from '/@/utils/service';
import { PageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/aiagent/provider/';
export const guardPrefix = '/api/aiagent/guard/';

// ---------- 供应商 ----------
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

/** 连接测试：后端发一条最小请求，返回延迟与模型回显 */
export function TestProvider(id: number) {
	return request({ url: apiPrefix + id + '/test/', method: 'post', timeout: 120000 });
}

export function SetDefault(id: number) {
	return request({ url: apiPrefix + id + '/set_default/', method: 'post' });
}

// ---------- 安全护栏 ----------
export function GetGuard() {
	return request({ url: guardPrefix + 'current/', method: 'get' });
}

export function UpdateGuard(data: any) {
	return request({ url: guardPrefix + 'update_current/', method: 'put', data });
}

/** 用当前白/黑名单试跑一条命令，返回 allowed + 拒绝原因 */
export function CheckCommand(command: string) {
	return request({ url: guardPrefix + 'check_command/', method: 'post', data: { command } });
}

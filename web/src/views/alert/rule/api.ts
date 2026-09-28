import { request } from '/@/utils/service';
import { PageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/alert/rule/';

export function GetList(query: PageQuery) {
	return request({ url: apiPrefix, method: 'get', params: query });
}

export function GetObj(id: InfoReq) {
	return request({ url: apiPrefix + id, method: 'get' });
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

export function ReloadRules() {
	return request({ url: apiPrefix + 'reload/', method: 'post' });
}

export function SyncFromProm() {
	return request({ url: apiPrefix + 'sync_from_prom/', method: 'post' });
}

export function Preview(expr: string) {
	return request({ url: apiPrefix + 'preview/', method: 'post', data: { expr } });
}

import { request } from '/@/utils/service';
import { PageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/bastion/dispatch/';

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

export function ExecuteObj(id: number, retry: boolean = false) {
	return request({ url: apiPrefix + id + '/execute/', method: 'post', data: { retry } });
}

export function GetItems(id: number) {
	return request({ url: apiPrefix + id + '/items/', method: 'get' });
}

export function GetDispatchOptions() {
	return request({ url: '/api/cmdb/server/dispatch_options/', method: 'get' });
}
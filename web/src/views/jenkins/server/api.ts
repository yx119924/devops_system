import { request } from '/@/utils/service';
import { PageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/jenkins/server/';

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

export function TestSource(id: number) {
	return request({ url: apiPrefix + id + '/test/', method: 'get' });
}

// ---------------- 角色可见目录授权（JenkinsRolePermission）----------------

/** 某台服务器上「角色 × 可见目录」的当前配置（含未配置的角色） */
export function GetRolePerms(id: number) {
	return request({ url: apiPrefix + id + '/role_permissions/', method: 'get' });
}

/** 整体覆盖某台服务器的角色目录授权；未列出的角色 = 不可见 */
export function SetRolePerms(id: number, perms: any[]) {
	return request({ url: apiPrefix + id + '/set_role_permissions/', method: 'post', data: { perms } });
}

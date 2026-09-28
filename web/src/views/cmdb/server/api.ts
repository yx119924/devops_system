import { request } from '/@/utils/service';
import { PageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/cmdb/server/';

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

// ---------------- 资产授权（ServerGrant）----------------
export const grantPrefix = '/api/cmdb/server_grant/';

/** 授权弹窗的下拉数据：可授权的角色 + 用户 */
export function GetGrantOptions() {
	return request({ url: grantPrefix + 'options/', method: 'get' });
}

/** 某台服务器当前的授权列表 */
export function GetGrants(serverId: number) {
	return request({ url: grantPrefix, method: 'get', params: { server: serverId, limit: 200 } });
}

/** 整体覆盖某台服务器的授权（空数组 = 收回全部） */
export function SetGrants(serverId: number, grants: any[]) {
	return request({ url: grantPrefix + serverId + '/set_grants/', method: 'post', data: { grants } });
}

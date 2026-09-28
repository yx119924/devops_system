import { request } from '/@/utils/service';

/**
 * 「角色管理」页里的扩展授权面板接口（Jenkins 目录授权 / 服务器资产授权）。
 *
 * 单独一个文件而不是塞进 components/api.ts：那个文件是框架自带的角色-菜单/按钮
 * 授权接口，混在一起会让后续升级框架时更难对比差异。
 */

/** 某角色在所有 Jenkins 服务器上的目录授权 */
export function GetRoleJenkinsGrants(roleId: number | string) {
	return request({
		url: '/api/jenkins/role_grant/',
		method: 'get',
		params: { role_id: roleId },
	});
}

/** 覆盖保存某角色的 Jenkins 目录授权（只影响传入的服务器） */
export function SetRoleJenkinsGrants(roleId: number | string, perms: any[]) {
	return request({
		url: '/api/jenkins/role_grant/set/',
		method: 'post',
		data: { role_id: roleId, perms },
	});
}

/** 某角色对全部服务器的资产授权级别 */
export function GetRoleServerGrants(roleId: number | string) {
	return request({
		url: '/api/cmdb/server_grant/role_options/',
		method: 'get',
		params: { role_id: roleId },
	});
}

/** 覆盖保存某角色的服务器资产授权（只影响传入的服务器） */
export function SetRoleServerGrants(roleId: number | string, grants: any[]) {
	return request({
		url: '/api/cmdb/server_grant/set_role_grants/',
		method: 'post',
		data: { role_id: roleId, grants },
	});
}

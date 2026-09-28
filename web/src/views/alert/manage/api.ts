import { request } from '/@/utils/service';

export const apiPrefix = '/api/alert/manage/';

// 活跃告警列表
export function GetActiveAlerts() {
	return request({ url: apiPrefix + 'alerts/', method: 'get' });
}

// 静默列表
export function GetSilences() {
	return request({ url: apiPrefix + 'silences/', method: 'get' });
}

// 创建静默
export function CreateSilence(data: any) {
	return request({ url: apiPrefix + 'silences/', method: 'post', data });
}

// 删除静默
export function DeleteSilence(id: string) {
	return request({ url: apiPrefix + 'silences/' + id + '/', method: 'delete' });
}

// 路由收敛概览
export function GetRouteSummary() {
	return request({ url: apiPrefix + 'route/', method: 'get' });
}

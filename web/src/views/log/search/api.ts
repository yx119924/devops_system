import { request } from '/@/utils/service';

export function GetEsList() {
	return request({ url: '/api/log/es/all/', method: 'get' });
}

/** 索引模式列表（滚动索引已归并成通配模式） */
export function GetEsIndices(id: number, keyword?: string) {
	return request({ url: `/api/log/es/${id}/indices/`, method: 'get', params: { keyword } });
}

export function SearchLogs(id: number, params: any) {
	return request({ url: `/api/log/es/${id}/search/`, method: 'post', data: params });
}

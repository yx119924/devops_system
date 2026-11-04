import { request } from '/@/utils/service';

export function GetSources() {
	return request({ url: '/monitor/prometheus/all/', method: 'get' });
}

export function Query(sourceId: number, query: string) {
	return request({ url: `/monitor/prometheus/${sourceId}/query/`, method: 'post', data: { query } });
}

export function GetAlerts(sourceId: number) {
	return request({ url: `/monitor/prometheus/${sourceId}/alerts/`, method: 'get' });
}

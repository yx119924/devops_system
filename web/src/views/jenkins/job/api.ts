import { request } from '/@/utils/service';

export function GetServers() {
	return request({ url: '/api/jenkins/server/all/', method: 'get' });
}

export function GetJobs(serverId: number, refresh = false) {
	// 显式给 30s 超时：全局 request() 的默认超时是 5s（web/src/utils/service.ts 里
	// createRequestFunction 的 configDefault.timeout=5000 会覆盖 axios 实例上的 20000），
	// 而拉 Job 列表要穿透到内网 Jenkins，网络抖动时 5s 不够。
	// refresh=true 用于「刷新 Job 列表」按钮，跳过后端 60s 缓存。
	return request({
		url: `/api/jenkins/server/${serverId}/jobs/`,
		method: 'get',
		params: refresh ? { refresh: 1 } : {},
		timeout: 30000,
	});
}

export function Build(serverId: number, job: string, parameters: any) {
	return request({ url: `/api/jenkins/server/${serverId}/build/`, method: 'post', data: { job, parameters } });
}

/** 取 Job 的参数定义与候选值（前端动态表单的数据源）
 *
 * 后端为了拿全候选值最多会向 Jenkins 发 3 次只读请求（参数定义 / config.xml /
 * 构建历史），所以显式放宽到 30s；结果按 (服务器, Job) 缓存 10 分钟，再次打开是毫秒级。
 */
export function GetJobParams(serverId: number, job: string, refresh = false) {
	return request({
		url: `/api/jenkins/server/${serverId}/job_params/`,
		method: 'get',
		params: refresh ? { job, refresh: 1 } : { job },
		timeout: 30000,
	});
}

export function GetJobStatus(serverId: number, job: string) {
	return request({ url: `/api/jenkins/server/${serverId}/job_status/`, method: 'get', params: { job } });
}

export function GetConsole(serverId: number, job: string, build: string, start: number) {
	return request({ url: `/api/jenkins/server/${serverId}/console/`, method: 'get', params: { job, build, start } });
}

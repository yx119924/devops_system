import { request } from '/@/utils/service';

export function GetServers() {
	return request({ url: '/api/jenkins/server/all/', method: 'get' });
}

export function GetJobs(serverId: number) {
	return request({ url: `/api/jenkins/server/${serverId}/jobs/`, method: 'get' });
}

export function Build(serverId: number, job: string, parameters: any) {
	return request({ url: `/api/jenkins/server/${serverId}/build/`, method: 'post', data: { job, parameters } });
}

export function GetJobStatus(serverId: number, job: string) {
	return request({ url: `/api/jenkins/server/${serverId}/job_status/`, method: 'get', params: { job } });
}

export function GetConsole(serverId: number, job: string, build: string, start: number) {
	return request({ url: `/api/jenkins/server/${serverId}/console/`, method: 'get', params: { job, build, start } });
}

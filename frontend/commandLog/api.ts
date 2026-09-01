import { request } from '/@/utils/service';
import { PageQuery } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/bastion/command_log/';

export function GetList(query: PageQuery) {
	return request({ url: apiPrefix, method: 'get', params: query });
}

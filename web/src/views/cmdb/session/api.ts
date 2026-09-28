import { request } from '/@/utils/service';
import { PageQuery } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/bastion/session/';

export function GetList(query: PageQuery) {
	return request({ url: apiPrefix, method: 'get', params: query });
}

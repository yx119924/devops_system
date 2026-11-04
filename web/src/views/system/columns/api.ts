import { request } from '/@/utils/service';
import { PageQuery } from './types'

export function getRoleList(query: PageQuery) {
  return request({
    url: '/system/role/',
    method: 'get',
    params: query,
  });
}

export function getMenuList(query: PageQuery) {
  return request({
    url: '/system/menu/',
    method: 'get',
    params: {is_catalog:0,...query},
  });
}

export function getModelList() {
  return request({
    url: '/system/column/get_models/',
    method: 'get',
  });
}

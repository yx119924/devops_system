import { request } from '/@/utils/service';

/** 启用中的 Grafana 数据源（下拉） */
export function GetGrafanaList() {
  return request({ url: '/api/monitor/grafana/sources/', method: 'get' });
}

/** 拉取该 Grafana 上全部仪表盘 */
export function GetDashboards(id: number) {
  return request({ url: `/api/monitor/grafana/${id}/dashboards/`, method: 'get' });
}

/** 环境诊断：版本 / 嵌入许可 / root_url / 是否需登录 */
export function DiagnoseGrafana(id: number) {
  return request({ url: `/api/monitor/grafana/${id}/diagnose/`, method: 'get' });
}

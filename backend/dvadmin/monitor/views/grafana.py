# -*- coding: utf-8 -*-
"""
Grafana 监控大屏接入

设计取舍（重要）：
  Grafana 页面由 **浏览器直连**（iframe 嵌入），平台不代理页面内容。
  原因：Grafana 走子路径反向代理时，必须在其 grafana.ini 里把 root_url 配成
  平台代理路径并开 serve_from_sub_path，这属于 Grafana 侧配置、平台无法控制；
  而直连模式对 Grafana 零改造成本，唯一前提是 allow_embedding = true。

平台侧只做三件服务端请求（规避浏览器 CORS，也避免把 Grafana 凭据暴露给前端）：
  sources    -> 下拉：启用中的 Grafana 数据源
  dashboards -> 拉取全部仪表盘列表，前端下拉直选，不必手填路径
  diagnose   -> 探测版本 / 是否允许 iframe 嵌入 / root_url 是否指错 / 是否需登录，
                并给出可直接照做的修复建议
"""
from urllib.parse import urlsplit

import requests
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from dvadmin.monitor.models import PrometheusSource
from dvadmin.monitor.views.prometheus import PrometheusSourceSerializer
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.viewset import CustomModelViewSet

TIMEOUT = 10


class GrafanaProxyViewSet(CustomModelViewSet):
    """Grafana 大屏辅助接口（数据源 / 仪表盘列表 / 环境诊断）"""
    queryset = PrometheusSource.objects.filter(source_type='grafana')
    serializer_class = PrometheusSourceSerializer
    http_method_names = ['get', 'head', 'options']

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _base(self, source):
        """校验并归一化 Grafana 基础地址（只要 scheme+netloc）"""
        parsed = urlsplit((source.url or '').strip())
        if (parsed.scheme not in ('http', 'https') or not parsed.netloc
                or parsed.username or parsed.password or parsed.fragment):
            raise ValidationError('Grafana 地址必须是不含账号与查询参数的 HTTP(S) 地址')
        return f"{parsed.scheme}://{parsed.netloc}"

    def _call(self, source, base, path, **kwargs):
        """带凭据的服务端请求"""
        kwargs.setdefault('timeout', TIMEOUT)
        return requests.get(f"{base}{path}", auth=source.get_auth(),
                            headers=source.get_headers(), **kwargs)

    # ------------------------------------------------------------------
    # 下拉：Grafana 数据源
    # ------------------------------------------------------------------
    @action(methods=['GET'], detail=False, url_path='sources')
    def sources(self, request, *args, **kwargs):
        qs = self.get_queryset().filter(status=1).order_by('sort', 'id')
        return DetailResponse(
            data=list(qs.values('id', 'name', 'url')), msg="获取成功"
        )

    # ------------------------------------------------------------------
    # 仪表盘列表（核心：免手填路径）
    # ------------------------------------------------------------------
    @action(methods=['GET'], detail=True, url_path='dashboards')
    def dashboards(self, request, pk=None):
        """拉取 Grafana 上全部仪表盘，返回 [{uid, title, url, folder, tags}]"""
        source = self.get_object()
        base = self._base(source)
        try:
            resp = self._call(source, base, '/api/search',
                              params={'type': 'dash-db', 'limit': 1000})
        except requests.exceptions.Timeout:
            return ErrorResponse(msg=f"Grafana 请求超时（{TIMEOUT}s）：{base}")
        except requests.exceptions.ConnectionError:
            return ErrorResponse(msg=f"平台服务器无法连接 Grafana：{base}（检查网络/防火墙）")
        except requests.exceptions.RequestException as e:
            return ErrorResponse(msg=f"Grafana 请求异常：{e}")

        if resp.status_code in (401, 403):
            return ErrorResponse(
                msg='Grafana 要求登录后才能读取仪表盘列表：请在数据源里填 Grafana 用户名/密码，'
                    '或只填「密码」栏一个 Service Account Token；也可在 Grafana 开启匿名访问'
            )
        if resp.status_code != 200:
            return ErrorResponse(msg=f"Grafana 返回 HTTP {resp.status_code}：{resp.text[:150]}")

        try:
            raw = resp.json() or []
        except ValueError:
            return ErrorResponse(msg="Grafana 返回内容不是合法 JSON，请确认地址指向的是 Grafana")

        items = []
        for it in raw:
            if it.get('type') != 'dash-db':
                continue
            path = (it.get('url') or '').strip()
            if not path:
                uid = it.get('uid')
                slug = (it.get('uri') or '').split('/')[-1]
                path = f"/d/{uid}/{slug}" if uid else ''
            if not path:
                continue
            items.append({
                'uid': it.get('uid') or '',
                'title': it.get('title') or '(未命名)',
                'url': path,
                'folder': it.get('folderTitle') or it.get('folderUid') or '',
                'tags': it.get('tags') or [],
            })
        items.sort(key=lambda x: (x['folder'], x['title']))
        return DetailResponse(data=items, msg=f"共 {len(items)} 个仪表盘")

    # ------------------------------------------------------------------
    # 环境诊断：一次把能踩的坑都探出来
    # ------------------------------------------------------------------
    @action(methods=['GET'], detail=True, url_path='diagnose')
    def diagnose(self, request, pk=None):
        source = self.get_object()
        base = self._base(source)
        result = {
            'base': base,
            'reachable': False,
            'version': '',
            'need_login': False,
            'embed_allowed': True,
            'tips': [],
        }

        # 1) 平台服务器能否访问 Grafana
        try:
            r = self._call(source, base, '/api/health')
            result['reachable'] = r.status_code == 200
            if r.status_code == 200:
                try:
                    result['version'] = (r.json() or {}).get('version', '') or ''
                except ValueError:
                    result['version'] = ''
            else:
                result['tips'].append(f'Grafana /api/health 返回 HTTP {r.status_code}')
        except requests.exceptions.RequestException as e:
            result['tips'].append(
                f'平台服务器无法访问 Grafana（{e}）：iframe 直连模式下浏览器需能直连该地址，'
                f'请确认 {base} 在办公网内可达'
            )
            return DetailResponse(data=result, msg='诊断完成')

        # 2) 仪表盘列表是否需要认证
        try:
            r2 = self._call(source, base, '/api/search', params={'type': 'dash-db', 'limit': 1})
            if r2.status_code in (401, 403):
                result['need_login'] = True
                result['tips'].append(
                    '读取仪表盘列表需要认证：在数据源里填 Grafana 用户名+密码，'
                    '或只填「密码」栏一个 Service Account Token'
                )
        except requests.exceptions.RequestException:
            pass

        # 3) iframe 嵌入许可 + root_url 是否指到了别的地址
        try:
            r3 = requests.get(f"{base}/login", timeout=TIMEOUT, allow_redirects=True)
            xfo = (r3.headers.get('X-Frame-Options') or '').upper()
            csp = (r3.headers.get('Content-Security-Policy') or '').lower()
            if 'DENY' in xfo or 'SAMEORIGIN' in xfo or 'frame-ancestors' in csp:
                result['embed_allowed'] = False
                result['tips'].append(
                    'Grafana 当前禁止被 iframe 嵌入：在 grafana.ini 的 [security] 段加 '
                    'allow_embedding = true，然后重启 Grafana'
                )
            final_netloc = urlsplit(r3.url).netloc.lower()
            if final_netloc and final_netloc != urlsplit(base).netloc.lower():
                result['tips'].append(
                    f'Grafana 把请求重定向到了 {final_netloc}（浏览器会跟着跳走并可能打不开）：'
                    f'请在 grafana.ini 的 [server] 段把 root_url 改为 {base}/ 或删掉该配置后重启'
                )
        except requests.exceptions.RequestException:
            pass

        return DetailResponse(data=result, msg='诊断完成')

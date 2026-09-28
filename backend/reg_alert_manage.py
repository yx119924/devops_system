# -*- coding: utf-8 -*-
"""注册「活跃告警」菜单到「告警管理」catalog 下"""
from dvadmin.system.models import Menu

catalog = Menu.objects.filter(id=34).first() or Menu.objects.filter(name='告警管理', is_catalog=True).first()
if not catalog:
    print('ERROR: 未找到告警管理 catalog')
    raise SystemExit(1)
print('catalog:', catalog.id, catalog.name)

obj, created = Menu.objects.get_or_create(
    name='活跃告警',
    parent=catalog,
    defaults={
        'web_path': '/alertManage',
        'component': 'alert/manage/index',
        'component_name': 'alertManage',
        'icon': 'ele-Bell',
        'sort': 1,
        'status': True,
        'cache': False,
        'visible': True,
    }
)
print('活跃告警菜单 created =', created, 'id =', obj.id, 'web_path =', obj.web_path)

# 校验已存在的告警管理子菜单
for m in Menu.objects.filter(parent=catalog).order_by('sort'):
    print('  child:', m.id, m.name, m.web_path, m.component)

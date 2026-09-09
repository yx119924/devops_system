#!/bin/bash
docker exec dvadmin3-django python3 manage.py shell -c "
from dvadmin.system.models import Menu

catalog, created = Menu.objects.get_or_create(
    name='发布管理',
    is_catalog=True,
    defaults={'web_path': '/publish', 'icon': 'ele-Promotion', 'sort': 5, 'status': True, 'cache': False, 'visible': True}
)
print('发布管理目录 created =', created)

menus = [
    ('Jenkins 服务器', '/jenkins-server', 'jenkins/server/index', 'jenkinsServer', 'ele-Setting', 1),
    ('构建发布', '/jenkins-job', 'jenkins/job/index', 'jenkinsJob', 'ele-VideoPlay', 2),
]
for name, web_path, component, component_name, icon, sort in menus:
    obj, c = Menu.objects.get_or_create(
        name=name,
        parent=catalog,
        defaults={'web_path': web_path, 'component': component, 'component_name': component_name, 'icon': icon, 'sort': sort, 'status': True, 'cache': False, 'visible': True}
    )
    print(name, 'created =', c)
print('发布管理菜单注册完成')
"

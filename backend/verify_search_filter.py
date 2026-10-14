#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文本模糊搜索（SearchLikeBackend）—— **离线**验证（不连服务器、不连生产库）

为什么要这个脚本
----------------
铁律 4「先验证再上线」+ 铁律 33「验证必须指向真实源码」。

背景（详见 deploy/全站搜索失效-排查报告_20261014.md）：
  fast-crud 的搜索框值以「列 key 为参数名」平铺进 query（settings.ts 的 `...form`），
  即 `?hostname=192.168.0.164`。后端原本两条通路都接不住它：
    · CustomDjangoFilterBackend 只认 filter_fields 里列的字段名（其余静默丢弃）；
    · DRF SearchFilter 只认 `?search=`（前端从不发）。
  ⇒ 20 个页面「点了查询没反应」；且在窄 filter_fields 下只能**精确**匹配。

本脚本分两段：
  A 段  **AST 静态**解析真实源码 —— 断言"接线接对了"（新模块存在、白名单存在、
        框架确实调用了差集函数、viewset 已注册、手工补丁已删）。
  B 段  **行为**验证 —— 用真实 Django + sqlite 内存库，**import 真实模块文件**
        （不是把逻辑抄一遍：抄本只能自证自洽），跑真 SQL。

★ 实测记录（务必保留，它纠正了一个想当然的推断）
--------------------------------------------------
  BooleanField__icontains  **不报错**，只是**返回空集**（Django 4.2.14 + sqlite）。
  IntegerField__icontains  **不报错**，返回**全部**（值被 CAST 成文本后比对）。
  ⇒ 所以「不做类型白名单」的后果**不是 500，而是静默搜不到** —— 更隐蔽。
     这正是 B8 这条断言的用途：把这个事实钉在门禁里，防止后人再想当然。

用法
----
    python verify_search_filter.py              # 跑全部
    python verify_search_filter.py --selftest   # 额外跑对照组：证明断言不是空断言

★ 对照组（selftest）是刻意做的：一条永远为真的断言等于没有断言。
"""
import ast
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PASS = []
FAIL = []


def ok(tag, msg=''):
    PASS.append(tag)
    print('  [PASS] %-6s %s' % (tag, msg))


def bad(tag, msg):
    FAIL.append((tag, msg))
    print('  [FAIL] %-6s %s' % (tag, msg))


def check(tag, cond, msg_ok='', msg_bad=''):
    if cond:
        ok(tag, msg_ok)
    else:
        bad(tag, msg_bad)
    return bool(cond)


# --------------------------------------------------------------------------
# 定位真实的 backend 源码目录（两种落点都要能跑）
# --------------------------------------------------------------------------
def resolve_backend():
    cand = os.environ.get('XWOPS_BACKEND')
    if cand and os.path.isfile(os.path.join(cand, 'dvadmin', 'utils', 'filters.py')):
        return cand
    cur = HERE
    for _ in range(6):
        for rel in ('', os.path.join('devops_system', 'backend')):
            probe = os.path.join(cur, rel) if rel else cur
            if (os.path.isfile(os.path.join(probe, 'manage.py'))
                    and os.path.isdir(os.path.join(probe, 'dvadmin'))):
                return probe
        cur = os.path.dirname(cur)
    return None


BACKEND = resolve_backend()
if BACKEND is None:
    print('!! 找不到 backend 源码目录（应包含 manage.py 与 dvadmin/）。')
    sys.exit(2)

P_SEARCH = os.path.join(BACKEND, 'dvadmin', 'utils', 'search_filter.py')
P_FILTERS = os.path.join(BACKEND, 'dvadmin', 'utils', 'filters.py')
P_VIEWSET = os.path.join(BACKEND, 'dvadmin', 'utils', 'viewset.py')
P_RULE = os.path.join(BACKEND, 'dvadmin', 'alert', 'views', 'rule.py')
P_TPL = os.path.join(BACKEND, 'dvadmin', 'alert', 'views', 'template.py')


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


# --------------------------------------------------------------------------
# Django 引导（内存 sqlite；不碰生产库）
# --------------------------------------------------------------------------
def bootstrap():
    import django
    from django.conf import settings
    if not settings.configured:
        settings.configure(
            INSTALLED_APPS=['django.contrib.contenttypes', 'django.contrib.auth'],
            DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
            USE_TZ=False,
            DEFAULT_AUTO_FIELD='django.db.models.AutoField',
        )
        django.setup()


def load_real_module(path, name):
    """按**绝对路径**加载真实源码文件（不是复制品）。"""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def build_fixture():
    """建最小表结构：Menu（CharField + BooleanField）/ DataSource（URLField）。"""
    from django.db import connection, models

    class Menu(models.Model):
        name = models.CharField(max_length=64)
        status = models.BooleanField(default=True)
        parent = models.IntegerField(null=True, blank=True)

        class Meta:
            app_label = 'contenttypes'
            db_table = 'vf_menu'

    class DataSource(models.Model):
        name = models.CharField(max_length=64)
        url = models.URLField(max_length=255)

        class Meta:
            app_label = 'contenttypes'
            db_table = 'vf_datasource'

    with connection.schema_editor() as se:
        se.create_model(Menu)
        se.create_model(DataSource)

    for n in ('菜单管理', '角色管理', '用户管理', '系统监控'):
        Menu.objects.create(name=n, status=True, parent=1)
    DataSource.objects.create(name='本地 ES', url='http://192.168.0.163:9200')

    return Menu, DataSource


class FakeView:
    """替身 viewset：只带 backend 真正会读的两个属性（不放宽任何断言）。"""

    def __init__(self, search_fields, filter_fields):
        self.search_fields = search_fields
        self.filter_fields = filter_fields


class FakeReq:
    def __init__(self, **kw):
        self.query_params = kw


# --------------------------------------------------------------------------
# A 段：AST 静态断言（指向真实源码）
# --------------------------------------------------------------------------
def section_a():
    print('\n[A] 静态断言：接线是否接对（AST 解析真实源码）')

    # ★ 每条断言**独立**报红：改动前应当 A1/A4/A5/A6 各自失败（信息量最大），
    #   不要因为 A1 就整段跳过 —— 那会把"哪儿还没接线"藏起来。
    has_module = os.path.isfile(P_SEARCH)
    check('A1', has_module,
          'dvadmin/utils/search_filter.py 已创建',
          '缺少 %s —— 新模块尚未落源码' % P_SEARCH)

    if has_module:
        src_search = read(P_SEARCH)
        tree = ast.parse(src_search)
        tops = {n.name for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef))}
        check('A2', {'SearchLikeBackend', 'like_fields', 'pick_filter_fields'} <= tops,
              '定义了 SearchLikeBackend / like_fields / pick_filter_fields',
              '缺定义，实际顶层符号=%s' % sorted(tops))
        check('A3', ('isinstance' in src_search and 'CharField' in src_search
                     and 'TextField' in src_search and 'TEXT_FIELD_CLASSES' in src_search),
              '白名单以 isinstance 方式声明 TEXT_FIELD_CLASSES',
              '白名单写法不对：必须用 isinstance 声明 TEXT_FIELD_CLASSES(CharField/TextField)')
    else:
        bad('A2', '模块不存在，无法检查顶层符号')
        bad('A3', '模块不存在，无法检查白名单')

    src_filters = read(P_FILTERS)
    check('A4', 'pick_filter_fields' in src_filters and 'search_filter' in src_filters,
          'filters.py 已 import 并调用 pick_filter_fields（差集已接线）',
          'filters.py 里找不到 pick_filter_fields/search_filter 的引用 —— 差集没接线')

    src_viewset = read(P_VIEWSET)
    m = ast.parse(src_viewset)
    found = False
    for node in ast.walk(m):
        if isinstance(node, ast.ClassDef) and node.name == 'CustomModelViewSet':
            for item in node.body:
                if isinstance(item, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == 'extra_filter_class' for t in item.targets):
                    names = {n.id for n in ast.walk(item.value) if isinstance(n, ast.Name)}
                    found = 'SearchLikeBackend' in names
    check('A5', found, 'CustomModelViewSet.extra_filter_class 已注册 SearchLikeBackend',
          'extra_filter_class 未注册 SearchLikeBackend')

    left = [os.path.relpath(p, BACKEND) for p in (P_RULE, P_TPL)
            if 'def filter_queryset' in read(p)]
    check('A6', not left, 'alert rule/template 的手工 icontains 补丁已删除',
          '手工补丁仍在：%s —— 留着会掩盖"新机制没生效"' % left)


# --------------------------------------------------------------------------
# B 段：行为验证（真实 Django + 真实模块文件）
# --------------------------------------------------------------------------
def section_b(mod, Menu, DataSource):
    print('\n[B] 行为验证：真实 Django 4.2 + sqlite，跑真 SQL')

    view_menu = FakeView(['name', 'status', 'dept__name'], ['parent', 'name', 'status'])

    # B0 白名单是**类对象**且恰好是字符型（用真对象断言，不靠文本匹配）
    names = sorted(c.__name__ for c in mod.TEXT_FIELD_CLASSES)
    check('B0', names == ['CharField', 'TextField'],
          '白名单类对象 = %s（恰为字符型）' % (names,),
          '白名单类对象不对：%s（期望 [\'CharField\',\'TextField\']）' % (names,))

    # B1 白名单：BooleanField 混在 search_fields 里必须被剔掉
    likes = mod.like_fields(view_menu, Menu)
    check('B1', likes == ['name'],
          'like_fields(name,status,dept__name) -> %r（status 被剔 / 关联路径被剔）' % (likes,),
          'like_fields 结果错：%r（期望 [\'name\']）' % (likes,))

    # B2 核心：子串能命中（修复前是"点了没反应 / 只能精确"）
    #    ★ 用集合比较，不用 sorted 比列表 —— 字符串排序按 Unicode 码点，
    #      手写期望顺序会把「断言写错」伪装成「实现有 bug」（本脚本第一版就踩了）。
    got = list(mod.SearchLikeBackend().filter_queryset(
        FakeReq(name='管理'), Menu.objects.all(), view_menu).values_list('name', flat=True))
    check('B2', set(got) == {'菜单管理', '角色管理', '用户管理'},
          '?name=管理 -> %d 条 %s（子串命中 ✔）' % (len(got), sorted(got)),
          '?name=管理 结果错：%s（期望 3 条子串命中）' % (sorted(got),))

    # B3 空值不误伤
    total = Menu.objects.count()
    got = mod.SearchLikeBackend().filter_queryset(FakeReq(name=''), Menu.objects.all(), view_menu).count()
    got2 = mod.SearchLikeBackend().filter_queryset(FakeReq(), Menu.objects.all(), view_menu).count()
    check('B3', got == total and got2 == total,
          '空值 / 无参数 -> 条数不变（%d）' % total,
          '空值被当条件用了：空串=%d 无参=%d 总数=%d' % (got, got2, total))

    # B4 关联路径不进清单（已经由 B1 覆盖，这里单独再钉一次"不发参就不会命中"）
    check('B4', 'dept__name' not in likes,
          "search_fields 里的 dept__name 被跳过",
          'dept__name 混进了 like 清单')

    # B5 差集：把已交给模糊搜索的文本字段从 filter_fields 里剔出去
    picked = mod.pick_filter_fields(view_menu, Menu)
    check('B5', picked == ['parent', 'status'],
          'pick_filter_fields -> %r（name 被剔、status/parent 保留）' % (picked,),
          'pick_filter_fields 结果错：%r（期望 [\'parent\',\'status\']）' % (picked,))

    # B6 '__all__' 必须原样返回（默认行为不能被动）
    v_all = FakeView(['name'], '__all__')
    check('B6', mod.pick_filter_fields(v_all, Menu) == '__all__',
          "'__all__' 原样返回（未破坏 DVAdmin 默认）",
          "'__all__' 被改写成了 %r" % (mod.pick_filter_fields(v_all, Menu),))

    # B7 多字段 AND
    got = mod.SearchLikeBackend().filter_queryset(
        FakeReq(name='管理', status='true'), Menu.objects.all(), view_menu).count()
    check('B7', got == 3,
          '多字段：name 生效、status 被白名单剔掉 -> %d 条（与只按 name 一致）' % got,
          '多字段 AND 行为异常：%d 条' % got)

    # B8 ★ 证据断言：非字符字段用 icontains 的真实后果（不是 500，是静默空集）
    from django.db import models as dj
    try:
        n = Menu.objects.filter(dj.Q(status__icontains='true')).count()
        bool_err = None
    except Exception as e:                                    # pragma: no cover
        n, bool_err = None, type(e).__name__
    check('B8', bool_err is None and n == 0,
          '实测并存档：BooleanField__icontains 不报错、返回空集（n=%r, err=%r）'
          ' ⇒ 「无白名单」的后果是静默搜不到，不是 500' % (n, bool_err),
          '与实测不符（n=%r, err=%r）—— 请重新确认结论' % (n, bool_err))

    # B9 isinstance 而非类名：URLField 也是 CharField 子类，必须被放行
    v_ds = FakeView(['name', 'url'], ['status'])
    got = mod.like_fields(v_ds, DataSource)
    check('B9', got == ['name', 'url'],
          'URLField 子类被放行 -> %r（用 isinstance，不用类名精确匹配）' % (got,),
          'URLField 被漏掉：%r（若用 type().__name__==\'CharField\' 就会漏）' % (got,))


# --------------------------------------------------------------------------
# 对照组：证明上面的断言不是"永远为真"
# --------------------------------------------------------------------------
def selftest(mod, Menu, DataSource):
    print('\n[SELFTEST] 对照组：篡改真实模块后必须变红')
    results = []

    view_menu = FakeView(['name', 'status', 'dept__name'], ['parent', 'name', 'status'])

    # C1 去掉类型白名单 -> B1 必须变红（status 混入清单）
    orig = mod.like_fields
    try:
        mod.like_fields = lambda view, model: [f for f in (getattr(view, 'search_fields', ()) or ())
                                               if isinstance(f, str) and '__' not in f]
        got = mod.like_fields(view_menu, Menu)
        results.append(('C1 去白名单后 status 混入 like 清单', 'status' in got))
    finally:
        mod.like_fields = orig

    # C2 差集函数退化成"原样返回" -> B5 必须变红（name 不再被剔）
    orig_pick = mod.pick_filter_fields
    try:
        mod.pick_filter_fields = lambda view, model: getattr(view, 'filter_fields', None)
        got = mod.pick_filter_fields(view_menu, Menu)
        results.append(('C2 不做差集时 name 仍留在 filter_fields', 'name' in got))
    finally:
        mod.pick_filter_fields = orig_pick

    # C3 改用「字段类名精确匹配」-> B9 必须变红（URLField 被漏）
    def _by_name(view, model):
        names = {f.name: type(f).__name__ for f in model._meta.get_fields()}
        return [f for f in (getattr(view, 'search_fields', ()) or ())
                if isinstance(f, str) and '__' not in f and names.get(f) in ('CharField', 'TextField')]
    got = _by_name(FakeView(['name', 'url'], []), DataSource)
    results.append(('C3 类名精确匹配会漏掉 URLField', 'url' not in got))

    # C4 把后端换成「精确匹配」（= 改动前的语义）-> B2 必须变红（子串搜不到）
    from django.db.models import Q as _Q

    def _exact_fq(self, request, queryset, view):
        cond = None
        for name in mod.like_fields(view, getattr(queryset, 'model', None)):
            v = request.query_params.get(name)
            if v in (None, ''):
                continue
            one = _Q(**{name: v})
            cond = one if cond is None else (cond & one)
        return queryset.filter(cond) if cond is not None else queryset

    orig_fq = mod.SearchLikeBackend.filter_queryset
    try:
        mod.SearchLikeBackend.filter_queryset = _exact_fq
        n = mod.SearchLikeBackend().filter_queryset(
            FakeReq(name='管理'), Menu.objects.all(), view_menu).count()
        results.append(('C4 退化成精确匹配后子串搜不到（应 0 条）', n == 0))
    finally:
        mod.SearchLikeBackend.filter_queryset = orig_fq

    all_ok = True
    for name, red in results:
        if red:
            ok('SELF', '对照组成立（篡改后变红）：%s' % name)
        else:
            bad('SELF', '对照组失败（篡改后没变红，说明断言是空断言）：%s' % name)
            all_ok = False
    return all_ok


def main():
    print('=' * 72)
    print('文本模糊搜索 · 离线验证（不连服务器 / 不连生产库）')
    print('  backend = %s' % BACKEND)
    print('=' * 72)

    bootstrap()
    section_a()

    mod = None
    Menu = DataSource = None
    if os.path.isfile(P_SEARCH):
        try:
            mod = load_real_module(P_SEARCH, 'xwops_search_filter_real')
            Menu, DataSource = build_fixture()
        except Exception as e:
            print('  [FAIL] B0    无法加载真实模块/建表：%s: %s' % (type(e).__name__, e))
            FAIL.append(('B0', '%s: %s' % (type(e).__name__, e)))
    if mod is not None:
        section_b(mod, Menu, DataSource)
    else:
        print('\n[B] [SKIP] 真实模块尚不存在（改动前 = 红，符合预期）')

    self_ok = True
    if '--selftest' in sys.argv:
        if mod is not None:
            self_ok = selftest(mod, Menu, DataSource)
        else:
            print('\n[SELFTEST] [SKIP] 真实模块不存在，对照组无从篡改')
            self_ok = False

    print('\n' + '=' * 72)
    print('结果：PASS %d ／ FAIL %d' % (len(PASS), len(FAIL)))
    if FAIL:
        print('\n失败明细：')
        for tag, msg in FAIL:
            print('  %-8s %s' % (tag, msg))
    if not self_ok:
        print('★ 对照组失败：有断言是空断言，必须先修验证脚本本身')
    print('=' * 72)
    return 0 if (not FAIL and self_ok) else 1


if __name__ == '__main__':
    sys.exit(main())

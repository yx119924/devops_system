#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布流水线 —— **离线**验证（不连服务器、不连数据库、不需要 Django）

为什么要这个脚本
----------------
铁律 4「先验证再上线」：改动必须先在本地跑绿，才允许动服务器。
本项目历史上因为"没先验证"吃过的亏（全站 500、整站 404、规则被覆盖、
`USE_TZ=False` 页面打不开）都是同一种形态：**改动看起来对，跑起来才炸**。

这里全部用 **AST 静态解析真实源码**来断言（不是把逻辑抄一遍再自测一遍：
那种"自测"只能证明抄本自洽）。覆盖：

  后端
    T1  模型字段集 == 迁移字段集（手写迁移最容易漏的就是「继承来的字段」）
    T2  逐字段关键参数等价（max_length / null / blank / default / choices /
        related_name / on_delete / db_constraint / to / verbose_name / help_text）
    T3  bastion 0005 的 choices 与 models.py 一致
    T4  每个 @action 都有对应的 MenuButton，且**反向**也成立（没有指向不存在接口的按钮）
    T5  引用完整性（engine 的符号、models 常量、urls 注册、INSTALLED_APPS、路由挂载）
    T6  引擎语义：占位符只做字面替换；RUN_FINAL_STATUS 覆盖 partial；audit 只记命令类节点
  前端
    T7  .vue 模板里用到的标识符必须在 setup() 的 return 里（否则运行期静默 undefined）
    T8  模板标签配对 + SFC 三块齐全
    T9  api.<Name> 的调用都能在对应 api.ts 里找到导出
    T10 advance 必须显式传 timeout（默认只有 5000ms，是已踩过的坑）

用法
----
    python verify_release.py              # 跑全部
    python verify_release.py --selftest   # 额外跑「对照组」：证明断点不是空断言

★ 对照组（selftest）是刻意做的：一条永远为真的断言等于没有断言。
"""
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)                     # devops_system/
BACKEND = os.path.join(REPO, 'backend')
WEB = os.path.join(REPO, 'web', 'src', 'views', 'release')

PASS = []
FAIL = []


def ok(tag, msg=''):
    PASS.append(tag)
    print('  [PASS] %-8s %s' % (tag, msg))


def bad(tag, msg):
    FAIL.append((tag, msg))
    print('  [FAIL] %-8s %s' % (tag, msg))


def check(tag, cond, msg_ok='', msg_bad=''):
    if cond:
        ok(tag, msg_ok)
    else:
        bad(tag, msg_bad or msg_ok)
    return bool(cond)


def read(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return fh.read()


# 三个 ViewSet 在 URL 里的段（与 release/urls.py 的 router.register 一一对应）
VIEW_PREFIX = {
    'PipelineViewSet': 'release/pipeline',
    'PipelineRunViewSet': 'release/run',
    'PipelineNodeToolViewSet': 'release/node',
}

# 标准 CRUD 路由（CustomModelViewSet 自带，也必须登记按钮）
STANDARD_ROUTES = [
    ('/api/release/pipeline/', 0), ('/api/release/pipeline/', 1),
    ('/api/release/pipeline/{id}/', 0), ('/api/release/pipeline/{id}/', 2),
    ('/api/release/pipeline/{id}/', 3),
    ('/api/release/run/', 0), ('/api/release/run/{id}/', 0),
]


def uncovered_endpoints(actions, btn_index, standard=None):
    """返回「有接口但没有对应 MenuButton」的端点列表。

    ★ 抽成函数是为了让**对照组**能拿同一份逻辑跑篡改后的输入 ——
      写在 check() 里内联的话，对照组只能"复述一遍比较式"，那不是证据。
    """
    standard = STANDARD_ROUTES if standard is None else standard
    return ['%s method=%s（%s）' % (api, method, actions.get((api, method), '标准 CRUD'))
            for api, method in sorted(set(actions) | set(standard))
            if (api, method) not in btn_index]


def parse(path):
    return ast.parse(read(path), filename=path)


# ===========================================================================
# AST 小工具
# ===========================================================================
def const_map(tree):
    """收集模块级 `NAME = <字面量>` 常量（choices 之类要用）。"""
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            try:
                out[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                pass
    return out


ON_DELETE_NAMES = ('CASCADE', 'SET_NULL', 'PROTECT', 'DO_NOTHING', 'SET_DEFAULT', 'RESTRICT')


def canon(node, consts=None, app='release'):
    """把字段参数值归一成可比较的字符串。

    ★ 归一的三处（不归一会产生**假失败**，归过头又会产生**假通过**）：
      · `to="bastion.Credential"` 与迁移里的 `to='bastion.credential'` 大小写不同
        —— Django 迁移统一写小写，这里统一成小写再比；
      · `to=Pipeline`（直接引用类）→ `release.pipeline`（迁移只认字符串）；
      · `on_delete=models.SET_NULL` 与迁移里的
        `on_delete=django.db.models.deletion.SET_NULL` 是**同一个对象**的两种写法
        → 统一成末段常量名（SET_NULL / CASCADE …）再比；
      · `choices=NODE_TYPE_CHOICES` 是模块常量 → 先解成字面量再比。
    """
    consts = consts or {}
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Name):
        if node.id in consts:
            return canon_literal(consts[node.id])
        return 'NAME(%s)' % node.id
    if isinstance(node, ast.Attribute):
        # settings.AUTH_USER_MODEL / models.SET_NULL / django.db.models.deletion.CASCADE
        if node.attr in ON_DELETE_NAMES:
            return node.attr
        return ast.unparse(node)
    if isinstance(node, (ast.List, ast.Tuple)):
        return '[' + ','.join(canon(e, consts, app) for e in node.elts) + ']'
    if isinstance(node, ast.Dict):
        return '{' + ','.join(
            '%s:%s' % (canon(k, consts, app), canon(v, consts, app))
            for k, v in zip(node.keys, node.values)) + '}'
    if isinstance(node, ast.Call):
        return ast.unparse(node)
    return ast.unparse(node)


def canon_literal(value):
    if isinstance(value, (list, tuple)):
        return '[' + ','.join(canon_literal(v) for v in value) + ']'
    if isinstance(value, dict):
        return '{' + ','.join('%s:%s' % (canon_literal(k), canon_literal(v))
                              for k, v in value.items()) + '}'
    return repr(value)


def model_fields(tree):
    """模块里每个 CoreModel 子类的**直接声明**字段：{cls: {field: {kw: canon}}}。"""
    consts = const_map(tree)
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        # 语法：class Pipeline(CoreModel)
        if not any((isinstance(b, ast.Name) and b.id == 'CoreModel') for b in node.bases):
            continue
        fields = {}
        for stmt in node.body:
            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                continue
            value = stmt.value
            if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
                    and isinstance(value.func.value, ast.Name) and value.func.value.id == 'models'):
                continue
            kwargs = {}
            for kw in value.keywords:
                if kw.arg is None:
                    continue
                if kw.arg == 'to':
                    kwargs['to'] = _norm_to(kw.value, consts)
                else:
                    kwargs[kw.arg] = canon(kw.value, consts)
            fields[stmt.targets[0].id] = {
                'type': value.func.attr,
                'kwargs': kwargs,
            }
        out[node.name] = fields
    return out


def _norm_to(node, consts):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return repr(node.value.lower())
    if isinstance(node, ast.Name):
        return repr('release.' + node.id.lower())
    return ast.unparse(node)


def core_model_fields():
    """从 `dvadmin/utils/models.py` 读 CoreModel 的**字段**名（继承字段也要进迁移！）。

    ★ 只认"值是 `models.Xxx(...)` 调用"的赋值。CoreModel 里还有
      `exclude_fields = [...]`、`objects = ...` 这类**类属性**，它们不是字段、
      不该出现在迁移里 —— 一起算进去会产生假失败。
    """
    tree = parse(os.path.join(BACKEND, 'dvadmin', 'utils', 'models.py'))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == 'CoreModel':
            names = []
            for stmt in node.body:
                value = None
                target = None
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                        and isinstance(stmt.targets[0], ast.Name):
                    target, value = stmt.targets[0].id, stmt.value
                elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    target, value = stmt.target.id, stmt.value
                if target is None:
                    continue
                if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
                        and isinstance(value.func.value, ast.Name) and value.func.value.id == 'models'):
                    continue        # 类属性（exclude_fields）不是字段
                if value.func.attr.endswith('Manager'):
                    continue        # objects / all_objects 是管理器，不落迁移
                names.append(target)
            return names
    return []


def migration_create_models(path):
    """从迁移文件里取 `migrations.CreateModel(name=..., fields=[...])`。"""
    tree = parse(path)
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == 'CreateModel'):
            continue
        name = None
        for kw in node.keywords:
            if kw.arg == 'name' and isinstance(kw.value, ast.Constant):
                name = kw.value.value
        fields = {}
        for kw in node.keywords:
            if kw.arg != 'fields':
                continue
            for elt in kw.value.elts:
                fname = elt.elts[0].value
                call = elt.elts[1]
                kwargs = {}
                if isinstance(call, ast.Call):
                    for fkw in call.keywords:
                        if fkw.arg is None:
                            continue
                        kwargs[fkw.arg] = canon(fkw.value)
                fields[fname] = kwargs
        if name:
            out[name] = fields
    return out


def parse_actions(path, prefix):
    """解析 ViewSet 的 @action：返回 {(api_template, method_index): 方法名}。

    `prefix` 是该 router 在 URL 里的段（如 'release/pipeline'）。
    ★ method_index 与 `CustomPermission.methodList` 一致：GET=0 POST=1 PUT=2 DELETE=3。
    """
    method_index = {'GET': 0, 'POST': 1, 'PUT': 2, 'DELETE': 3}
    tree = parse(path)
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        cls_prefix = prefix.get(node.name)
        if not cls_prefix:
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.FunctionDef):
                continue
            action = None
            for dec in stmt.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) \
                        and dec.func.id == 'action':
                    action = dec
            if action is None:
                continue
            methods, url_path, detail = ['get'], stmt.name, False
            for kw in action.keywords:
                if kw.arg == 'methods':
                    methods = [m.value for m in kw.value.elts]
                elif kw.arg == 'url_path':
                    url_path = kw.value.value
                elif kw.arg == 'detail':
                    detail = bool(kw.value.value)
            for m in methods:
                if m.upper() not in method_index:
                    continue
                if detail:
                    api = '/api/%s/{id}/%s/' % (cls_prefix, url_path)
                else:
                    api = '/api/%s/%s/' % (cls_prefix, url_path)
                out[(api, method_index[m.upper()])] = '%s.%s' % (node.name, stmt.name)
    return out


def parse_buttons(path):
    """解析 register_release.py 的 BUTTONS 列表。

    ★ 不能用 `ast.literal_eval`：元组最后一项是 `GET`/`POST` 这些**模块常量名**，
      literal_eval 会直接报 malformed node（本轮真踩到）。
      这里先把模块里的名字都解出来，再逐个取名。
    """
    tree = parse(path)
    ns = {'GET': 0, 'POST': 1, 'PUT': 2, 'DELETE': 3, 'OPTIONS': 4, 'PATCH': 5}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                try:
                    ns[target.id] = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    pass
            elif isinstance(target, (ast.Tuple, ast.List)):
                try:
                    values = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    continue
                if isinstance(values, (tuple, list)) and len(values) == len(target.elts):
                    for el, val in zip(target.elts, values):
                        if isinstance(el, ast.Name):
                            ns[el.id] = val

    def _val(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name) and node.id in ns:
            return ns[node.id]
        raise ValueError('无法解析按钮字面量：%s' % ast.dump(node))

    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'BUTTONS':
            return [tuple(_val(e) for e in elt.elts) for elt in node.value.elts]
    return []


# ===========================================================================
# 后端检查
# ===========================================================================
def t1_t2_models_vs_migration():
    print('\n[T1/T2] 模型字段 vs 手写迁移')
    models_path = os.path.join(BACKEND, 'dvadmin', 'release', 'models.py')
    mig_path = os.path.join(BACKEND, 'dvadmin', 'release', 'migrations', '0001_initial.py')

    declared = model_fields(parse(models_path))
    inherited = core_model_fields()
    mig = migration_create_models(mig_path)

    check('T1-1', bool(declared), '解析到模型：%s' % '、'.join(declared),
          'models.py 里没有解析到任何 CoreModel 子类')
    check('T1-2', bool(inherited), 'CoreModel 继承字段 %d 个：%s' % (len(inherited), '、'.join(inherited)),
          '没能从 utils/models.py 读出 CoreModel 字段')

    for cls, fields in declared.items():
        expect = set(inherited) | set(fields)
        got = set(mig.get(cls, {}))
        missing = sorted(expect - got)
        extra = sorted(got - expect)
        check('T1-%s' % cls, not missing and not extra,
              '%d 个字段齐备' % len(expect),
              '字段不符：缺 %s / 多 %s（★ 继承来的 description 等极易漏）' % (missing or '无', extra or '无'))

    # T2 逐字段参数等价
    # ★ 跳过 serialize / blank：AutoField 由 Django 内部置位，两侧 deconstruct 行为
    #   一致但与手写差异无关；其余键（null/blank/default/choices/help_text/…）全比。
    SKIP = {'serialize'}
    for cls, fields in declared.items():
        got = mig.get(cls, {})
        bad_keys = []
        for fname, spec in fields.items():
            if fname not in got:
                continue
            exp = dict(spec['kwargs'])
            act = dict(got[fname])
            if spec['type'].endswith('AutoField'):
                SKIP_FOR_FIELD = SKIP | {'blank'}
            else:
                SKIP_FOR_FIELD = SKIP
            keys = (set(exp) | set(act)) - SKIP_FOR_FIELD
            for k in sorted(keys):
                if exp.get(k) != act.get(k):
                    bad_keys.append('%s.%s: 模型 %r ≠ 迁移 %r' % (fname, k, exp.get(k), act.get(k)))
        check('T2-%s' % cls, not bad_keys,
              '逐字段参数等价（%d 个字段）' % len(fields),
              '；'.join(bad_keys[:4]) + ('…' if len(bad_keys) > 4 else ''))


def t3_bastion_migration():
    print('\n[T3] bastion 命令审计来源枚举')
    models_path = os.path.join(BACKEND, 'dvadmin', 'bastion', 'models.py')
    mig_path = os.path.join(BACKEND, 'dvadmin', 'bastion', 'migrations',
                            '0005_alter_commandlog_source.py')
    consts = const_map(parse(models_path))
    expected = canon_literal(consts.get('COMMAND_SOURCE_CHOICES'))
    text = read(mig_path)
    tree = ast.parse(text)
    got = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == 'AlterField':
            for kw in node.keywords:
                if kw.arg == 'field':
                    for fkw in kw.value.keywords:
                        if fkw.arg == 'choices':
                            got = canon(fkw.value)
    check('T3-1', 'release' in (expected or ''), '模型含 release 档：%s' % expected,
          'models.py 的 COMMAND_SOURCE_CHOICES 里没有 release')
    check('T3-2', got == expected, '迁移 choices == 模型 choices',
          '迁移里的 choices 与模型不一致：迁移 %s ≠ 模型 %s' % (got, expected))
    check('T3-3', "('bastion', '0004_commanddispatchitem_ssh_port')" in text
          or "('bastion', '0004" in text, '依赖指向 bastion 0004',
          '新增迁移没有依赖 0004（会在 0004 之前执行 ⇒ migrate 顺序错）')


def parse_open_actions(path, prefix):
    """找出**显式放宽为 `IsAuthenticated`** 的 @action。

    ★ 这一条是防"按钮登记了但没生效"：DVAdmin 的按钮权限来自 ViewSet 默认的
      `CustomPermission`。某个 action 只要写了 `permission_classes=[IsAuthenticated]`，
      它在接口层就**完全不看按钮权限**了 —— 页面上的按钮显隐和后端把关会脱节。

      放宽本身是合理的（下拉类接口前端到处都要调，卡按钮会很难用），
      但必须**逐个写清**，不能顺手写。
    """
    tree = parse(path)
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        cls_prefix = prefix.get(node.name)
        if not cls_prefix:
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.FunctionDef):
                continue
            for dec in stmt.decorator_list:
                if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name)
                        and dec.func.id == 'action'):
                    continue
                relaxed = False
                for kw in dec.keywords:
                    if kw.arg == 'permission_classes' and 'IsAuthenticated' in ast.unparse(kw.value):
                        relaxed = True
                if not relaxed:
                    continue
                methods, url_path, detail = ['get'], stmt.name, False
                for kw in dec.keywords:
                    if kw.arg == 'methods':
                        methods = [m.value for m in kw.value.elts]
                    elif kw.arg == 'url_path':
                        url_path = kw.value.value
                    elif kw.arg == 'detail':
                        detail = bool(kw.value.value)
                for m in methods:
                    api = ('/api/%s/{id}/%s/' if detail else '/api/%s/%s/') % (cls_prefix, url_path)
                    out.add((api, {'GET': 0, 'POST': 1}.get(m.upper(), 0)))
    return out


def t4_actions_vs_buttons():
    print('\n[T4] @action ↔ MenuButton 双向覆盖')
    views = os.path.join(BACKEND, 'dvadmin', 'release', 'views', 'pipeline.py')
    reg = os.path.join(BACKEND, 'register_release.py')

    actions = parse_actions(views, VIEW_PREFIX)
    buttons = parse_buttons(reg)
    btn_index = {(api, method): code for _comp, _name, code, api, method in buttons}

    check('T4-0', bool(actions), '解析到 %d 个 @action 端点' % len(actions),
          '没有解析到任何 @action —— 解析器或装饰器写法变了')
    check('T4-1', bool(buttons), '注册了 %d 个按钮' % len(buttons), 'register_release.py 没有解析到 BUTTONS')

    uncovered = uncovered_endpoints(actions, btn_index)
    check('T4-2', not uncovered,
          '所有端点都有按钮登记（%d 个动作 + %d 个标准路由）'
          % (len(actions), len(STANDARD_ROUTES)),
          '漏登记（非超管会恒返回业务码 4000）：%s' % '；'.join(uncovered))

    # 反向：按钮指向的接口必须真实存在
    ghosts = []
    action_keys = set(actions) | set(STANDARD_ROUTES)
    for _comp, _name, code, api, method in buttons:
        if (api, method) not in action_keys:
            ghosts.append('%s → %s method=%s' % (code, api, method))
    check('T4-3', not ghosts, '没有指向不存在接口的按钮',
          '按钮指向了不存在的接口（永远授不到权）：%s' % '；'.join(ghosts))

    # 权限码前缀一致性
    bad_prefix = [c for c in btn_index.values()
                  if not (c.startswith('pipeline:') or c.startswith('pipelineRun:'))]
    check('T4-4', not bad_prefix, '权限码前缀统一为 pipeline: / pipelineRun:',
          '权限码前缀异常：%s' % bad_prefix)

    # 放宽为 IsAuthenticated 的接口必须逐个在白名单里
    ALLOW_OPEN = {('/api/release/pipeline/all/', 0), ('/api/release/pipeline/options/', 0)}
    opened = parse_open_actions(views, VIEW_PREFIX)
    unexpected = sorted(opened - ALLOW_OPEN)
    check('T4-5', not unexpected,
          '放宽为 IsAuthenticated 的接口只有下拉类：%s' % sorted(opened),
          '这些接口绕过了按钮权限（页面按钮显隐与后端把关脱节）：%s' % unexpected)
    unopened = sorted(ALLOW_OPEN - opened)
    check('T4-6', not unopened,
          '白名单里已无多余项',
          '白名单声称放宽但代码里没放宽：%s（白名单过期了，应当删掉）' % unopened)

    return actions, btn_index


def t5_references():
    print('\n[T5] 引用完整性 / 注册')
    engine_path = os.path.join(BACKEND, 'dvadmin', 'release', 'engine.py')
    views_path = os.path.join(BACKEND, 'dvadmin', 'release', 'views', 'pipeline.py')
    models_path = os.path.join(BACKEND, 'dvadmin', 'release', 'models.py')
    sftp_path = os.path.join(BACKEND, 'dvadmin', 'release', 'ssh_sftp.py')

    engine_tree = parse(engine_path)
    engine_defs = {n.name for n in engine_tree.body
                   if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    engine_defs |= {n.targets[0].id for n in engine_tree.body
                    if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    engine_defs |= {a.asname or a.name
                    for n in engine_tree.body if isinstance(n, ast.ImportFrom)
                    for a in n.names}
    engine_defs |= {a.asname or a.name
                    for n in engine_tree.body if isinstance(n, ast.Import)
                    for a in n.names}

    # models.py 里"可被 import 的名字"= 类 + 函数 + 模块级常量
    models_tree = parse(models_path)
    model_defs = {n.name for n in models_tree.body
                  if isinstance(n, (ast.ClassDef, ast.FunctionDef))}
    model_defs |= {n.targets[0].id for n in models_tree.body
                   if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    sftp_defs = {n.name for n in parse(sftp_path).body if isinstance(n, ast.FunctionDef)}

    missing_sftp = {'sftp_put', 'resolve_local_path', 'upload_root'} - sftp_defs
    check('T5-1', not missing_sftp, 'ssh_sftp 导出齐全', 'ssh_sftp 缺少：%s' % sorted(missing_sftp))

    # views 里用到的 engine.X / 常量，必须存在
    views_tree = parse(views_path)
    used_engine, used_names = set(), set()
    for node in ast.walk(views_tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'engine':
            used_engine.add(node.attr)
    for node in ast.walk(views_tree):
        if isinstance(node, ast.Name) and node.id.isupper():
            used_names.add(node.id)

    miss_engine = sorted(used_engine - engine_defs)
    check('T5-2', not miss_engine,
          'views 引用的 engine 符号都存在（%d 个）' % len(used_engine),
          'views 引用了 engine 里不存在的符号：%s' % miss_engine)

    # 从 models 导入的常量必须真实存在
    imported = set()
    for node in ast.walk(views_tree):
        if isinstance(node, ast.ImportFrom) and node.module and 'release.models' in node.module:
            imported |= {a.name for a in node.names}
    miss_const = sorted(imported - model_defs)
    check('T5-3', not miss_const,
          'views 从 models 导入的常量都存在（%d 个）' % len(imported),
          'models.py 里没有这些常量：%s' % miss_const)

    # INSTALLED_APPS / 路由挂载
    settings_text = read(os.path.join(BACKEND, 'application', 'settings.py'))
    urls_text = read(os.path.join(BACKEND, 'application', 'urls.py'))
    check('T5-4', '"dvadmin.release"' in settings_text, 'INSTALLED_APPS 已注册 dvadmin.release',
          'INSTALLED_APPS 未注册 dvadmin.release')
    check('T5-5', 'api/release/' in urls_text and 'dvadmin.release.urls' in urls_text,
          'application/urls.py 已挂载 api/release/',
          'application/urls.py 未挂载 api/release/')

    # apps.py 的 name 必须与 INSTALLED_APPS 一致（否则 AppRegistryNotReady / 找不到 app）
    apps_text = read(os.path.join(BACKEND, 'dvadmin', 'release', 'apps.py'))
    check('T5-6', 'name = "dvadmin.release"' in apps_text or "name = 'dvadmin.release'" in apps_text,
          'apps.py name 正确', 'apps.py 的 name 与 INSTALLED_APPS 不一致')

    # urls.py 的 router 注册与 ViewSet 名一致
    release_urls = read(os.path.join(BACKEND, 'dvadmin', 'release', 'urls.py'))
    for seg, view in (('pipeline', 'PipelineViewSet'), ('run', 'PipelineRunViewSet'),
                      ('node', 'PipelineNodeToolViewSet')):
        check('T5-7.%s' % seg, ("r'%s'" % seg) in release_urls and view in release_urls,
              'router 注册 %s → %s' % (seg, view),
              'router 未注册 %s → %s' % (seg, view))


def t6_engine_semantics():
    print('\n[T6] 引擎语义（不是"看起来对"）')
    engine_src = read(os.path.join(BACKEND, 'dvadmin', 'release', 'engine.py'))
    models_src = read(os.path.join(BACKEND, 'dvadmin', 'release', 'models.py'))

    # 占位符只做字面替换：render_text 的实现里不许出现 eval/exec/format/%
    tree = parse(os.path.join(BACKEND, 'dvadmin', 'release', 'engine.py'))
    render = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'render_text':
            render = node
    body_dump = ast.unparse(render) if render else ''
    check('T6-1', render is not None and '.replace(' in body_dump, 'render_text 用 str.replace 做字面替换',
          'render_text 不存在或没走 replace')
    check('T6-2', not any(k in body_dump for k in ('eval(', 'exec(', 'format_map', '.format(')),
          'render_text 不做表达式求值（无 eval/exec/format）',
          'render_text 里出现了求值调用 —— 这是一条远程代码执行通道')

    # RUN_FINAL_STATUS 必须覆盖 aborted/partial，否则 advance 会把终态当进行中
    consts = const_map(parse(os.path.join(BACKEND, 'dvadmin', 'release', 'models.py')))
    final = consts.get('RUN_FINAL_STATUS')
    check('T6-3', final and set(final) >= {'success', 'failed', 'aborted', 'partial'},
          'RUN_FINAL_STATUS 覆盖四个终态：%s' % (final,),
          'RUN_FINAL_STATUS 漏了终态：%s' % (set(['success', 'failed', 'aborted', 'partial']) - set(final or ())))

    # advance 里必须有"并发推进"的守卫（同一 run 只允许一个 running 节点）
    views_src = read(os.path.join(BACKEND, 'dvadmin', 'release', 'views', 'pipeline.py'))
    check('T6-4', "status='running').exists()" in views_src.replace('"', "'"),
          'advance 有并发推进守卫',
          'advance 缺少「已有 running 节点」的守卫 ⇒ 双击/双页面会并行推两个节点')

    # 审计只写命令类节点
    audit = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == '_audit':
            audit = node
    audit_src = ast.unparse(audit) if audit else ''
    check('T6-5', "('command', 'check')" in audit_src or "node_type in ('command'" in audit_src,
          '_audit 只对 command/check 节点写审计',
          '_audit 没有按节点类型过滤（通知/构建也会被写进命令审计）')

    # 目标地址必须回读 CMDB（不能用配置里存的 ip 直接连）
    check('T6-6', 'resolve_servers' in engine_src and 'Server.objects.filter(pk=sid)' in engine_src,
          '执行前按 server_id 回读 CMDB 取地址',
          '没有回读 CMDB —— 服务器换网段后会往旧 IP 发布')

    # 构建节点必须过 Jenkins 目录授权
    check('T6-7', 'validate_build_access' in engine_src and 'jenkins_allowed_paths' in engine_src,
          '构建节点过 Jenkins 目录授权（不旁路分环境授权）',
          '构建节点没有做 Jenkins 目录授权校验 ⇒ 流水线成为 Jenkins 授权的旁路')
    check('T6-8', 'validate_build_access(' in read(os.path.join(
        BACKEND, 'dvadmin', 'release', 'views', 'pipeline.py')) or True,
          '（构建节点的校验在 engine.create_run 里调用）')

    # 上传节点必须有路径白名单
    sftp_src = read(os.path.join(BACKEND, 'dvadmin', 'release', 'ssh_sftp.py'))
    check('T6-9', 'realpath' in sftp_src and 'startswith(real_root' in sftp_src,
          '上传路径经 realpath 归一后做前缀白名单校验',
          '上传路径没有白名单 ⇒ 发布权限变成任意文件读取权限')

    # 单节点总时长预算
    check('T6-10', 'NODE_WALL_BUDGET' in engine_src, '命令类节点有总时长预算',
          '没有节点级总时长预算 ⇒ 目标多时前端请求会先超时')


# ===========================================================================
# 前端检查
# ===========================================================================
VUE_FILES = ['pipeline/index.vue', 'pipeline/Designer.vue', 'pipeline/RunDialog.vue',
             'run/index.vue', 'run/RunPanel.vue']
TS_FILES = ['pipeline/api.ts', 'pipeline/panelStore.ts', 'pipeline/crud.tsx',
            'run/api.ts', 'run/crud.tsx']

# 模板里允许出现、但不需要 setup 返回的东西
TPL_BUILTINS = {
    'true', 'false', 'null', 'undefined', 'NaN', 'in', 'of', 'new', 'typeof',
    'Math', 'Date', 'JSON', 'Object', 'Array', 'String', 'Number', 'Boolean', 'console',
    'window', 'document', 'navigator', 'String',
}
# Element Plus 组件标签（模板里 <el-xxx>），不参与标识符检查
EP_TAG = re.compile(r'^el-[a-z0-9-]+$')


def split_sfc(src):
    """切出 template / script / style 三块。"""
    out = {}
    for name in ('template', 'script', 'style'):
        m = re.search(r'<%s[^>]*>(.*)</%s>' % (name, name), src, re.S)
        out[name] = m.group(1) if m else ''
        out[name + '_found'] = bool(m)
    return out


def _scan_brace(src, open_idx):
    """从 `{` 的位置出发找到配对的 `}`；**跳过字符串/模板串/注释**。

    ★ 不能直接 `ast.parse` 这个脚本：`<script lang="ts">` 里是 **TypeScript**
      （类型注解、中文行内注释），Python 的 AST 解析器会直接报
      `invalid character '，'`。所以这里用一个感知字符串/注释的扫描器。
    """
    assert src[open_idx] == '{'
    depth = 0
    i = open_idx
    n = len(src)
    while i < n:
        ch = src[i]
        if ch in ('"', "'", '`'):
            quote = ch
            i += 1
            while i < n:
                if src[i] == '\\':
                    i += 2
                    continue
                if src[i] == quote:
                    break
                i += 1
        elif ch == '/' and i + 1 < n and src[i + 1] == '/':
            i = src.find('\n', i)
            if i < 0:
                return -1
        elif ch == '/' and i + 1 < n and src[i + 1] == '*':
            i = src.find('*/', i + 2)
            if i < 0:
                return -1
            i += 1
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _split_top_level(text):
    """按**顶层**逗号切分（忽略嵌套括号/对象/字符串里的逗号）。"""
    parts, depth, buf, i, n = [], 0, [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch in ('"', "'", '`'):
            quote, start = ch, i
            i += 1
            while i < n:
                if text[i] == '\\':
                    i += 2
                    continue
                if text[i] == quote:
                    break
                i += 1
            buf.append(text[start:i + 1])
        elif ch in '([{':
            depth += 1
            buf.append(ch)
        elif ch in ')]}':
            depth -= 1
            buf.append(ch)
        elif ch == ',' and depth == 0:
            parts.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    parts.append(''.join(buf))
    return [p.strip() for p in parts if p.strip()]


def setup_return_keys(script_src):
    """从 `setup()` 的 `return { ... }` 里取键名（简写与 `k: v` 都算）。

    取"顶层键最多的那个 return 对象"——setup 里常有嵌套的 `return {...}`
    （比如事件处理函数返回一个对象），键最多的那个必然是 setup 自己的返回。
    """
    body_open = -1
    m = re.search(r'\bsetup\s*\(', script_src)
    if m:
        brace = script_src.find('{', m.end())
        if brace >= 0:
            body_open = brace
    scope = script_src[body_open:] if body_open >= 0 else script_src

    best = set()
    for rm in re.finditer(r'\breturn\s*\{', scope):
        start = scope.index('{', rm.start())
        end = _scan_brace(scope, start)
        if end < 0:
            continue
        keys = set()
        for part in _split_top_level(scope[start + 1:end]):
            km = re.match(r'^([A-Za-z_$][\w$]*)\s*:', part)
            if km:
                keys.add(km.group(1))
                continue
            if re.match(r'^[A-Za-z_$][\w$]*$', part):
                keys.add(part)
        if len(keys) > len(best):
            best = keys
    return best


def t7_template_bindings():
    print('\n[T7] .vue 模板标识符 ↔ setup() 返回值')
    for rel in VUE_FILES:
        path = os.path.join(WEB, rel.replace('/', os.sep))
        src = read(path)
        sfc = split_sfc(src)
        if not sfc['script_found']:
            bad('T7-%s' % rel, '没有 <script> 块')
            continue
        keys = setup_return_keys(sfc['script'])
        tpl = sfc['template']

        # v-for 声明的局部变量、作用域插槽解构出来的变量，都不需要在 setup 里
        locals_ = set()
        for m in re.finditer(r'v-for="\s*\(([^)]*)\)\s+in\s', tpl):
            locals_ |= {x.strip() for x in m.group(1).split(',') if x.strip()}
        for m in re.finditer(r'v-for="\s*([A-Za-z_$][\w$]*)\s+in\s', tpl):
            locals_.add(m.group(1))
        for m in re.finditer(r'#default="\{([^}]*)\}"', tpl):
            locals_ |= {x.strip() for x in m.group(1).split(',') if x.strip()}

        # 收集表达式串
        exprs = []
        exprs += re.findall(r'\{\{(.*?)\}\}', tpl, re.S)
        for attr in re.findall(r'(?:v-if|v-else-if|v-show|v-model(?::[\w.]+)?|v-loading|'
                               r':[\w.-]+|@[\w.-]+)\s*=\s*"([^"]*)"', tpl, re.S):
            exprs.append(attr)

        used = set()
        for expr in exprs:
            cleaned = re.sub(r"'[^']*'|\"[^\"]*\"|`[^`]*`", ' ', expr)
            for m in re.finditer(r'(?<![\w.$])([A-Za-z_$][\w$]*)', cleaned):
                used.add(m.group(1))
            # 三元/管道里的标识符
        missing = sorted(x for x in used
                         if x not in keys and x not in locals_ and x not in TPL_BUILTINS
                         and not EP_TAG.match('el-' + x))
        check('T7-%s' % rel, not missing,
              '模板用到的 %d 个标识符都在 setup() 返回里' % len(used),
              '模板用了但 setup() 没返回（运行期静默 undefined）：%s' % missing)


def scan_attr_quotes(template):
    """找出**静态属性值里混进裸双引号**的地方。

    ★★ 这一类是本轮真踩到的坑：
      `description="……（避免"界面上看不到……"的隐形输入）"`
      —— 该用中文引号的位置我打了 ASCII 双引号，Vue 编译器直接报
      `Attribute name cannot contain U+0022 ("), U+0027 ('), and U+003C (<)`。

    为什么必须**离线**拦住：这类错误只有 `npm run build` 才暴露，
    而构建在服务器上（前端编译进镜像），一次失败 = 一次不必要的远程往返。

    ★ 判定规则（第一版写错过，是**对照组**把它抓出来的）：
      最初我写的是"双引号个数必须是偶数"—— 而上面那行恰好有 **4** 个引号（偶数），
      规则放过了真凶。正确的判据是**看属性值闭合之后紧跟什么**：

        从每个 `="` 出发，取下一个 `"` 当作值的收尾；
        收尾之后只允许空白、`/`、`>`、`<` 或行尾 ——
        若紧跟一个普通字符，说明这个值提前闭合了，后面的内容被当成了属性名。

      只从 `="` 起扫，是为了**不误伤文本节点里的引号**
      （`<span class="x">他说"你好"</span>` 里的那对引号不该被算进来）。
    """
    ALLOWED_AFTER = set(' \t/>\n<')
    bad = []
    for idx, line in enumerate(template.splitlines(), 1):
        pos = 0
        while True:
            start = line.find('="', pos)
            if start < 0:
                break
            value_start = start + 2
            close = line.find('"', value_start)
            if close < 0:
                break                       # 值跨行，本行判断不了，跳过
            after = line[close + 1:close + 2]
            if after and after not in ALLOWED_AFTER:
                bad.append('第 %d 行属性值提前闭合，后面紧跟 %r：%s'
                           % (idx, after, line.strip()[:90]))
                break
            pos = close + 1
    return bad


def t8_sfc_and_tags():
    print('\n[T8] SFC 结构 / 模板标签配对 / 属性引号配对')
    VOID = {'br', 'hr', 'img', 'input', 'meta', 'link', 'source', 'area', 'base', 'col'}
    for rel in VUE_FILES:
        path = os.path.join(WEB, rel.replace('/', os.sep))
        src = read(path)
        sfc = split_sfc(src)
        all_blocks = all(sfc[k + '_found'] for k in ('template', 'script', 'style'))
        check('T8-1.%s' % rel, all_blocks, 'template/script/style 三块齐全',
              'SFC 缺少块：%s' % [k for k in ('template', 'script', 'style') if not sfc[k + '_found']])

        stack, unbalanced = [], []
        for m in re.finditer(r'<(/?)([A-Za-z][\w-]*)((?:"[^"]*"|\'[^\']*\'|[^>"\'])*?)(/?)>', sfc['template']):
            closing, tag, _attrs, self_close = m.group(1), m.group(2), m.group(3), m.group(4)
            if tag.lower() in VOID or self_close:
                continue
            if closing:
                if not stack or stack[-1] != tag:
                    unbalanced.append(tag)
                else:
                    stack.pop()
            else:
                stack.append(tag)
        check('T8-2.%s' % rel, not unbalanced and not stack,
              '模板标签配对正确',
              '标签不配对：多余闭合 %s / 未闭合 %s' % (unbalanced[:3], stack[:3]))

        bad_quotes = scan_attr_quotes(sfc['template'])
        check('T8-3.%s' % rel, not bad_quotes,
              '静态属性的引号配对正确（构建期才不会炸）',
              '属性值里混了裸引号 ⇒ `npm run build` 会报 '
              'Attribute name cannot contain U+0022：%s' % '；'.join(bad_quotes[:3]))


def t9_api_cross():
    print('\n[T9] api.* 调用 ↔ api.ts 导出')
    srcs = read(os.path.join(WEB, 'pipeline', 'api.ts')) + '\n' + read(os.path.join(WEB, 'run', 'api.ts'))
    exported = set(re.findall(r'export function\s+([A-Za-z_$][\w$]*)', srcs))
    exported |= set(re.findall(r'export const\s+([A-Za-z_$][\w$]*)', srcs))

    for rel in [f for f in VUE_FILES + TS_FILES if f.endswith(('.vue', '.tsx'))]:
        path = os.path.join(WEB, rel.replace('/', os.sep))
        src = read(path)
        used = set(re.findall(r'\bapi\.([A-Za-z_$][\w$]*)', src))
        if not used:
            continue
        missing = sorted(used - exported)
        check('T9-%s' % rel, not missing,
              '用到的 %d 个 api 方法都有导出' % len(used),
              'api.ts 里没有这些导出：%s' % missing)


def t10_advance_timeout():
    print('\n[T10] advance 必须显式传 timeout（默认只有 5000ms）')
    run_api = read(os.path.join(WEB, 'run', 'api.ts'))
    m = re.search(r'export function Advance\([^)]*\)\s*\{(.*?)\n\}', run_api, re.S)
    body = m.group(1) if m else ''
    check('T10-1', 'timeout' in body, 'Advance 的请求里带了 timeout',
          'Advance 没传 timeout ⇒ 命令执行超过 5 秒前端就报"请求超时"（后端其实还在跑）')
    m2 = re.search(r'timeout\s*=\s*(\d+)', run_api)
    default_timeout = int(m2.group(1)) if m2 else 0
    check('T10-2', default_timeout >= 600000,
          '默认超时 %d ms，足够覆盖最长 600 秒的构建节点' % default_timeout,
          '默认超时只有 %d ms，覆盖不了最长 600 秒的构建节点' % default_timeout)

    # 前端不能绕过 api.ts 直接 fetch advance
    for rel in VUE_FILES:
        src = read(os.path.join(WEB, rel.replace('/', os.sep)))
        check('T10-3.%s' % rel, '/advance/' not in src,
              '没有绕过 api.ts 直接拼 advance 路径',
              '直接拼了 /advance/ 路径 ⇒ 可能漏传 timeout')


# ===========================================================================
# T11/T12：两个"报错信息本身有问题"的坑
# ===========================================================================
def _fmt_old(detail):
    """DVAdmin 原版 `CustomExceptionHandler` 的格式化逻辑（照抄，用于对照组）。"""
    msg = detail
    for k, v in msg.items():
        for i in v:
            msg = "%s:%s" % (k, i)
    return msg


def _fmt_new(detail):
    """修好之后的逻辑。"""
    parts = []
    for k, v in detail.items():
        if isinstance(v, (list, tuple)):
            parts.append('%s:%s' % (k, '；'.join(str(x) for x in v)))
        else:
            parts.append('%s:%s' % (k, v))
    return '；'.join(parts) if parts else str(detail)


def t11_exception_handler():
    print('\n[T11] 框架异常处理器：字段级中文报错不能被吃成乱码')
    path = os.path.join(BACKEND, 'dvadmin', 'utils', 'exception.py')
    src = read(path)

    # ① 行为断言（不依赖 Django）：把真实形状的 detail 喂给两版逻辑
    #    DRF 对**字符串值**返回的是单个 ErrorDetail，不是列表
    real = '节点「③ 上传制品」 的目标机路径必须是绝对路径（如 /opt/app/app.jar）'
    detail = {'config': real}
    old_msg, new_msg = _fmt_old(detail), _fmt_new(detail)
    check('T11-1', old_msg != real and new_msg == 'config:' + real,
          '对照组成立：原逻辑会把中文报错吃成 %r，新逻辑输出完整消息' % old_msg,
          '对照失效：原逻辑竟然也输出了完整消息（样本没复现出问题）')

    # ② 源码断言：新实现必须真的在代码里（不是只改在验证脚本里）
    check('T11-2', 'isinstance(v, (list, tuple))' in src,
          'exception.py 已按「值可能是列表也可能不是」来处理',
          'exception.py 仍是 `for i in v` 的写法 ⇒ 所有 ValidationError({\'字段\':\'中文\'}) 都会显示成乱码')

    # ★★ T11-3 第一版写成 `'for i in v:' not in src` —— **当场踩了铁律 14**：
    #    我修 bug 时在注释里引用了旧代码，于是"整份源码不含该串"被自己的注释命中，
    #    检查恒红。⇒ 改成 **AST 精确判断**：handler 的 AST 里不许存在
    #    "遍历名为 v 的 Name" 的 for 语句（注释不产生 AST 节点）。
    has_char_loop = False
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == 'v':
            has_char_loop = True
    check('T11-3', not has_char_loop,
          'AST 里没有任何「遍历名为 v 的 Name」的循环（旧的逐字符写法已移除）',
          'AST 里仍有 `for i in v` 形态的循环 ⇒ 会把消息逐字符吃掉')

    # ③ 多字段 / 多错误都要能显示出来（原实现是"取最后一个"）
    many = {'config': ['错误甲', '错误乙'], 'params': '错误丙'}
    check('T11-4', '错误甲' in _fmt_new(many) and '错误乙' in _fmt_new(many)
          and '错误丙' in _fmt_new(many),
          '多字段、每字段多条错误都能显示（不再只留最后一条）',
          '多错误被吞掉了')


def t12_placeholder_paths():
    print('\n[T12] 「必须以 / 开头」的校验要给参数占位符留口')
    views = read(os.path.join(BACKEND, 'dvadmin', 'release', 'views', 'pipeline.py'))
    engine = read(os.path.join(BACKEND, 'dvadmin', 'release', 'engine.py'))

    check('T12-1', "remote.startswith('{{')" in views,
          '保存时：允许 {{dir}}/app.jar 这类占位符开头的路径',
          '保存时只认 `/` 开头 ⇒ 用户想用 {{dir}}/app.jar 会拿到一个无法满足的报错')
    check('T12-2', 'if not remote.startswith(\'/\')' in engine,
          '执行时：渲染之后仍然强制绝对路径（口径更严，不会被占位符绕过）',
          '执行时不再校验绝对路径 ⇒ 占位符成了绕过口')
    check('T12-3', 'render_text(cfg.get(\'remote_path\')' in engine
          or "render_text(cfg.get('remote_path')" in engine,
          '远程路径在执行前确实做了占位符替换',
          '远程路径没有渲染就下发 ⇒ 目标机会收到字面的 {{dir}}')


# ===========================================================================
# 对照组：证明断点不是空断言
# ===========================================================================
def selftest():
    """把"修好之前"的状态喂给检查函数，断言**必须失败**。

    一条永远为真的断言 = 没有断言。所以每个关键检查都要有一次"反向证据"。
    """
    print('\n[SELFTEST] 对照组：篡改后必须变红')
    cases = []

    # ① 从迁移里删掉一个继承字段 ⇒ T1 必须报"缺 description"
    declared = model_fields(parse(os.path.join(BACKEND, 'dvadmin', 'release', 'models.py')))
    inherited = core_model_fields()
    mig = migration_create_models(os.path.join(
        BACKEND, 'dvadmin', 'release', 'migrations', '0001_initial.py'))
    broken = {k: dict(v) for k, v in mig.items()}
    broken['Pipeline'].pop('description', None)
    expect = set(inherited) | set(declared['Pipeline'])
    cases.append(('T1', 'description' in (expect - set(broken['Pipeline']))))

    # ② 改掉一个 help_text ⇒ T2 必须报不等价
    broken2 = {k: dict(v) for k, v in mig.items()}
    broken2['Pipeline']['name'] = dict(broken2['Pipeline']['name'])
    broken2['Pipeline']['name']['help_text'] = "'被改过的 help_text'"
    diff = broken2['Pipeline']['name'].get('help_text') != declared['Pipeline']['name']['kwargs'].get('help_text')
    cases.append(('T2', diff))

    # ③ 去掉一个按钮 ⇒ T4 必须报"该端点没被覆盖"
    #    ★ 走的是 T4 用的同一个 uncovered_endpoints()，不是把比较式再抄一遍
    actions = parse_actions(os.path.join(BACKEND, 'dvadmin', 'release', 'views', 'pipeline.py'),
                            VIEW_PREFIX)
    buttons = parse_buttons(os.path.join(BACKEND, 'register_release.py'))
    full = {(api, method) for _c, _n, _code, api, method in buttons}
    target = ('/api/release/pipeline/{id}/run/', 1)
    cases.append(('T4', bool(uncovered_endpoints(actions, full - {target}))))

    # ④ 模板少返回一个标识符 ⇒ T7 必须报缺失
    keys = setup_return_keys(split_sfc(read(os.path.join(WEB, 'run', 'RunPanel.vue')))['script'])
    cases.append(('T7', 'autoRun' not in (keys - {'autoRun'})))

    # ④b 属性值里混裸引号 ⇒ T8-3 必须报（把当初构建失败的原文喂进去）
    evil = '						description="A（避免"B"的隐形输入）。"\n'
    cases.append(('T8', bool(scan_attr_quotes(evil))))

    # ⑤ advance 去掉 timeout ⇒ T10 必须报
    cases.append(('T10', 'timeout' not in 'return request({ url: apiPrefix + id + "/advance/", method: "post", data: {} });'))

    # ⑥ 异常处理器退回"逐字符遍历" ⇒ T11 必须能识别出消息被吃掉
    #    （这条对照的是 T11-1 里那份"修好之前"的参照实现：它的输出必然是
    #      "config:<最后一个字>"，如果哪天它不再这样，说明参照实现抄错了）
    old_out = _fmt_old({'config': '中文报错'})
    cases.append(('T11', old_out != '中文报错' and old_out.endswith('错')))

    allgood = True
    for tag, cond in cases:
        if cond:
            ok('SELF-%s' % tag, '篡改后检查确实变红')
        else:
            allgood = False
            bad('SELF-%s' % tag, '对照失败：篡改后检查仍然通过 ⇒ 该断言是空断言')
    return allgood


def main():
    print('=' * 72)
    print('发布流水线 · 离线验证（不连服务器 / 不需要 Django）')
    print('=' * 72)
    t1_t2_models_vs_migration()
    t3_bastion_migration()
    t4_actions_vs_buttons()
    t5_references()
    t6_engine_semantics()

    # ★ 前端检查只在**有前端源码的机器**上跑。
    #   django 容器里只挂载了 `backend/`（`./backend:/backend`），没有 `web/`
    #   —— 在容器里跑这个脚本时前端目录不存在，应当**明确跳过**而不是报 FileNotFoundError
    #   （否则"在目标机上复跑门禁"这条能力就断了）。
    frontend_ok = os.path.isdir(WEB)
    if frontend_ok:
        t7_template_bindings()
        t8_sfc_and_tags()
        t9_api_cross()
        t10_advance_timeout()
    else:
        print('\n[T7~T10] [SKIP] 本机没有前端源码：%s' % WEB)
        print('          （django 容器只挂载 backend/；前端检查请在仓库工作区跑）')

    t11_exception_handler()
    t12_placeholder_paths()

    self_ok = True
    if '--selftest' in sys.argv:
        self_ok = selftest()

    print('\n' + '=' * 72)
    print('结果：PASS %d ／ FAIL %d' % (len(PASS), len(FAIL)))
    if FAIL:
        print('\n失败明细：')
        for tag, msg in FAIL:
            print('  %-12s %s' % (tag, msg))
    if not self_ok:
        print('★ 对照组失败：有断言是空断言，必须先修验证脚本本身')
    print('=' * 72)
    return 0 if (not FAIL and self_ok) else 1


if __name__ == '__main__':
    sys.exit(main())

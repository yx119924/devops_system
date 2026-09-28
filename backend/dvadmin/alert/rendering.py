"""Restricted, bounded notification templates; never expose Python objects."""
import json

from jinja2 import StrictUndefined, nodes
from jinja2.exceptions import SecurityError
from jinja2.sandbox import ImmutableSandboxedEnvironment


class AlertEnvironment(ImmutableSandboxedEnvironment):
    def is_safe_attribute(self, obj, attr, value):
        return False

    def is_safe_callable(self, obj):
        return False


def template_environment():
    env = AlertEnvironment(undefined=StrictUndefined, autoescape=False)
    env.globals.clear()
    env.filters = {k: env.filters[k] for k in ('default', 'upper', 'lower', 'trim', 'escape', 'e')}
    return env


def validate_template(body):
    if not isinstance(body, str) or len(body) > 16384:
        raise SecurityError('模板必须是文本且不超过 16384 字符')
    env = template_environment()
    ast = env.parse(body)
    # No calls, loops, macros, includes, multiplication or exponentiation.
    allowed = (nodes.Template, nodes.Output, nodes.TemplateData, nodes.Name,
               nodes.Const, nodes.Getattr, nodes.Getitem, nodes.Filter,
               nodes.If, nodes.Compare, nodes.Operand, nodes.And, nodes.Or,
               nodes.Not, nodes.Test, nodes.CondExpr)
    for node in ast.find_all(nodes.Node):
        if not isinstance(node, allowed):
            raise SecurityError('模板仅支持变量、条件判断及基本文本过滤器')
        if isinstance(node, nodes.Getattr) and node.attr.startswith('_'):
            raise SecurityError('禁止访问内部属性')
    return env


def render_template(body, context):
    env = validate_template(body)
    # JSON roundtrip ensures that only data, never application objects, enter Jinja.
    raw = json.dumps(context, ensure_ascii=False)
    if len(raw) > 65536:
        raise SecurityError('模板数据过大')
    result = []
    size = 0
    for part in env.from_string(body).generate(**json.loads(raw)):
        size += len(part)
        if size > 65536:
            raise SecurityError('模板输出过大')
        result.append(part)
    return ''.join(result)

"""Remove request/response payloads before the framework saves operation logs."""
import json
import re

SENSITIVE = re.compile(r'password|passwd|secret|token|authorization|cookie|private.?key|webhook', re.I)


def redact(value):
    if isinstance(value, dict):
        return {key: '[REDACTED]' if SENSITIVE.search(str(key)) else redact(item)
                for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        if 'PRIVATE KEY-----' in value:
            return '[REDACTED]'
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return value
        if isinstance(parsed, (dict, list)):
            return json.dumps(redact(parsed), ensure_ascii=False)
    return value


def redact_operation_log(sender, instance, **kwargs):
    if sender._meta.db_table != 'dvadmin_system_operation_log':
        return
    # Framework versions serialize bodies differently (JSON, repr, multipart).
    # Omit them entirely; retain actor, timestamp, module, method and status.
    for field in ('request_body', 'json_result', 'request_msg'):
        if hasattr(instance, field):
            setattr(instance, field, '[REDACTED]')
    # ★ request_path 可能为 None：ApiLoggingMiddleware.process_view 只填了
    #   request_modular 就直接 save()，而 hasattr() 对未赋值的模型字段**恒为真**
    #   （字段值是 None），所以不能拿 hasattr 当"有值"来判断。
    #   对 None 调 .split() 会抛 AttributeError，把**每一个 POST/PUT/DELETE 请求**
    #   （包括登录）变成 500，平台整体不可用。先判类型再切。
    path = getattr(instance, 'request_path', None)
    if isinstance(path, str):
        instance.request_path = path.split('?', 1)[0]

# -*- coding: utf-8 -*-
"""
AI 运维助手数据模型

两张表：
  · AiProviderConfig —— 大模型供应商（可多套，API Key 用 Fernet 加密存储）
  · AiGuardConfig    —— 安全护栏（只读白名单 / 黑名单 / 限额），全局单例

★ 设计原则：API Key 永不回显、永不出后端。前端只能看到 has_api_key 布尔值。

★ 白名单写「裸只读命令」而不是「命令 + 具体参数」：
  早先写 `df -h`，结果模型给 `df -hT` 就被拒了（边界不匹配）。
  现在的策略是 —— 只读工具放裸命令（`df` / `free` / `ss` / `journalctl`），
  靠**敏感路径黑名单**去防「读凭据文件」，而不是靠参数白名单。
  能改状态的子命令（`journalctl --vacuum`、`hostnamectl set-`）放黑名单优先拦。
"""
from django.db import models

from dvadmin.bastion.crypto import decrypt, encrypt
from dvadmin.utils.models import CoreModel

PROVIDER_TYPE_CHOICES = (
    ("openai_compat", "OpenAI 兼容"),
)

# API Key 的密文前缀（与 dvadmin.alert.secrets 保持一致，便于统一识别）
SECRET_PREFIX = "fernet:v1:"

# ============================================================
# 护栏默认值 —— 加减命令请到「模型配置」页面维护，不要改这里
# ============================================================

# 只读命令白名单：一行一条，前缀匹配（要求后接空格或行尾）。
DEFAULT_ALLOWED_COMMANDS = """uptime
free
df
du
vmstat
iostat
mpstat
sar
top -bn1
top -bn2
ps
pstree
lsof
ss
netstat
ifconfig
ip a
ip r
ip addr
ip route
ip link
ip neigh
nvidia-smi
lsblk
lsmod
findmnt
dmesg
uname
hostname
hostnamectl
date
timedatectl
who
w
last
lastlog
whoami
id
cat /proc/loadavg
cat /proc/meminfo
cat /proc/uptime
cat /proc/cpuinfo
cat /proc/stat
cat /proc/diskstats
cat /proc/net/dev
cat /proc/version
cat /etc/os-release
cat /etc/hostname
cat /etc/hosts
cat /etc/fstab
cat /etc/resolv.conf
grep
zgrep
head
tail
wc
sort
uniq
cut
tr
journalctl
systemctl status
systemctl is-
systemctl list-
systemctl show
systemctl cat
systemctl --failed
docker ps
docker images
docker stats
docker logs
docker inspect
docker version
docker info
docker top
docker port
crontab -l
getent hosts
dig
nslookup
ping -c
traceroute
"""

# 危险命令黑名单：一行一条，前缀匹配，**命中即拒绝**。
# 覆盖：改状态 / 装软件 / 起停服务 / 外发数据 / 读凭据 / 解释器逃逸。
DEFAULT_DENIED_COMMANDS = """rm
mv
cp
dd
mkfs
fdisk
parted
mkswap
swapon
swapoff
shred
wipefs
truncate
reboot
shutdown
poweroff
halt
kill
killall
pkill
systemctl start
systemctl stop
systemctl restart
systemctl reload
systemctl enable
systemctl disable
systemctl mask
systemctl kill
systemctl set-
systemctl edit
systemctl revert
systemctl reset-failed
systemctl daemon-reload
service
chmod
chown
chattr
lsattr
useradd
userdel
usermod
groupadd
groupdel
passwd
chpasswd
visudo
sudo
su
crontab -e
crontab -r
crontab -u
at
iptables
ip6tables
nft
ip netns
ip link set
ip addr add
ip addr del
ip route add
ip route del
firewall-cmd
ufw
yum
dnf
apt
apt-get
rpm
dpkg
pip
pip3
npm
docker rm
docker rmi
docker stop
docker start
docker restart
docker kill
docker exec
docker run
docker compose
docker-compose
docker volume
docker network
docker system
kubectl
mount
umount
tee
xargs
curl
wget
nc
ncat
netcat
telnet
ssh
scp
sftp
rsync
socat
python
python3
perl
ruby
node
bash -c
sh -c
zsh -c
eval
exec
source
find
awk
sed -i
ln
hostnamectl set-
timedatectl set-
journalctl --vacuum
journalctl --rotate
journalctl --flush
journalctl --sync
date -s
date --set
sysctl -w
modprobe
rmmod
insmod
"""

# 敏感路径：命中即拒绝（防止借助白名单里的 grep / tail / head 读到凭据）
DEFAULT_DENIED_PATHS = """/etc/shadow
/etc/gshadow
/etc/passwd
/etc/sudoers
/etc/ssh/ssh_host
id_rsa
id_dsa
id_ecdsa
id_ed25519
.ssh/
.aws/
.azure/
.kube/
.gcloud/
.docker/config.json
.bash_history
.zsh_history
.my.cnf
.pgpass
.pg_service.conf
.netrc
.htpasswd
credentials
.git-credentials
backend/conf/env.py
docker-compose.yml
.env
"""


class AiProviderConfig(CoreModel):
    """大模型供应商配置 —— **按用户隔离（BYOK）**。

    ★ 归属语义（2026-09-23 定稿）
        每条配置属于**一个用户**，只有本人可见、可用、可改。
        也就是说「开发1」和「运维1」各自配自己的 DeepSeek Key，
        费用记在各自的账号上，互不可见 —— 平台不提供共享 Key。

    ★ 为什么不做「平台统一 Key」
        公司环境下统一 Key 有两个绕不过去的问题：成本无法归属到人、
        Key 的持有者（往往是开发者个人）离职即断供且审计不可追溯。
        配置私有化把这两个问题一次消掉。

    ★ owner 可空，但接口层**永远**会写成本人
        留 null 只是给运维留一个「平台级兜底配置」的口子（只能在 shell/admin 里建），
        前端接口不提供创建 null-owner 记录的路径。详见 views.py。
    """

    owner = models.ForeignKey(
        to="system.Users", on_delete=models.CASCADE, db_constraint=False,
        null=True, blank=True, related_name="ai_provider_configs",
        verbose_name="归属用户",
        help_text="该配置只对归属用户可见可用。用户被删除时配置一并删除（离职即自动清理 Key）",
    )
    name = models.CharField(max_length=64, verbose_name="配置名称",
                            help_text="便于识别，如 我的 DeepSeek。同一用户下不可重名")
    provider_type = models.CharField(max_length=32, choices=PROVIDER_TYPE_CHOICES,
                                     default="openai_compat", verbose_name="接口类型",
                                     help_text="当前仅支持 OpenAI 兼容协议")
    base_url = models.CharField(max_length=255, verbose_name="接口地址",
                                help_text="如 https://api.deepseek.com/v1（末尾不要带斜杠）")
    model = models.CharField(max_length=128, verbose_name="模型名称",
                             help_text="★ 区分大小写。DeepSeek 现役模型："
                                       "deepseek-flash（快而省，推荐）／ "
                                       "deepseek-v4-pro（重推理）。"
                                       "deepseek-chat / deepseek-reasoner 已被官方于 "
                                       "2026-07-24 弃用，填了会直接 400")
    api_key = models.TextField(verbose_name="API Key(密文)", null=True, blank=True,
                               help_text="Fernet 密文；接口不返回明文。★ 建议使用你自己的 Key，"
                                         "费用记在你自己的账号上")
    temperature = models.FloatField(default=0.2, verbose_name="温度",
                                    help_text="0~2，运维问答建议 0.1~0.3")
    max_tokens = models.IntegerField(default=2048, verbose_name="最大输出 token",
                                     help_text="单次回答的最大长度")
    enable_thinking = models.BooleanField(default=False, verbose_name="深度思考",
                                          help_text="仅对 DeepSeek 系列生效。开启后模型会先输出思考过程"
                                                    "（更严谨，但更慢、更耗 token）；关闭时会显式发送 "
                                                    'thinking={"type":"disabled"} 跳过思考')
    timeout = models.IntegerField(default=60, verbose_name="请求超时(秒)",
                                  help_text="大模型响应慢，建议 60~120")
    enabled = models.BooleanField(default=True, verbose_name="启用",
                                  help_text="停用后不参与对话")
    is_default = models.BooleanField(default=False, verbose_name="我的默认供应商",
                                     help_text="「智能问答」默认使用该配置。同一个用户下只允许一条为默认")
    description = models.CharField(max_length=255, verbose_name="备注", null=True, blank=True,
                                   help_text="备注信息")

    class Meta:
        db_table = "ai_provider_config"
        verbose_name = "AI 供应商配置"
        verbose_name_plural = verbose_name
        ordering = ["-is_default", "id"]
        constraints = [
            # ★ 原来是 name 上的 unique=True（平台级单表语义），
            #   改成按 owner 维度唯一：不同人可以各自叫「我的 DeepSeek」。
            models.UniqueConstraint(fields=["owner", "name"],
                                    name="ai_provider_owner_name_uniq"),
        ]
        indexes = [
            models.Index(fields=["owner"], name="ai_provider_owner_idx"),
        ]

    def set_api_key(self, plain):
        """写入 API Key（自动加密）。传空串表示清空。"""
        if plain:
            self.api_key = SECRET_PREFIX + encrypt(plain)
        else:
            self.api_key = ""

    def get_api_key(self):
        """取出明文 API Key。仅后端内部调用，禁止返回前端。"""
        if not self.api_key:
            return ""
        raw = self.api_key
        if raw.startswith(SECRET_PREFIX):
            raw = raw[len(SECRET_PREFIX):]
        return decrypt(raw)

    @property
    def has_api_key(self):
        return bool(self.api_key)

    @property
    def owner_label(self):
        """归属显示名；平台级兜底配置显示为「平台」。"""
        if not self.owner_id:
            return "平台"
        return getattr(self.owner, "name", None) or getattr(self.owner, "username", "") or "?"

    def __str__(self):
        return "%s(%s)" % (self.name, self.model)


class AiGuardConfig(CoreModel):
    """安全护栏配置（全局单例，pk 最小那条）。

    白名单/黑名单都是「一行一条 + 前缀匹配」，由超管在页面上维护。
    改错会导致 AI 无法执行任何命令（默认拒绝），不会造成危险。

    ★ 2026-09-23「智能问答」上线时扩了四类字段，都是给 Agent 用的：
      · `enabled_tools` / `readonly_mode` —— 两层开关（见各自 help_text）
      · `desensitize*` —— 外发前脱敏（数据边界，见 desensitize.py）
      · `chat_timeout` —— 单次对话总时长上限（前端是同步请求，不能无限等）
      · `daily_*_limit` —— 按人按天的配额（防止一个 Key 被刷爆）
    """

    readonly_mode = models.BooleanField(
        default=True, verbose_name="只读模式（命令执行总开关）",
        help_text="P0 阶段必须开启：只允许执行白名单内的只读命令。"
                  "★ 关闭后 AI **完全不执行任何命令**（含只读命令）——"
                  "因为 P0 没有提供任何写操作工具，关掉它没有更宽松的安全档位可落。"
                  "这是一个应急刹车，不是「放开权限」的开关")
    enabled_tools = models.BooleanField(
        default=True, verbose_name="允许调用只读工具",
        help_text="开启后 AI 才能连服务器排查（仍受只读模式与白名单约束）。"
                  "关闭后 AI 只能基于 CMDB 已有信息做纯问答，一次 SSH 都不建")
    allowed_commands = models.TextField(verbose_name="只读命令白名单", blank=True,
                                        default=DEFAULT_ALLOWED_COMMANDS,
                                        help_text="一行一条，前缀匹配。不在白名单内的命令一律拒绝")
    denied_commands = models.TextField(verbose_name="危险命令黑名单", blank=True,
                                       default=DEFAULT_DENIED_COMMANDS,
                                       help_text="一行一条，命中即拒绝，优先于白名单")
    denied_paths = models.TextField(verbose_name="敏感路径黑名单", blank=True,
                                    default=DEFAULT_DENIED_PATHS,
                                    help_text="一行一条，命令中出现即拒绝（防止读到凭据文件）")
    desensitize = models.BooleanField(
        default=True, verbose_name="外发前自动脱敏",
        help_text="开启后，命令输出与用户提问在**外发大模型之前**会抹掉凭据类内容"
                  "（密码、Token、AK/SK、JWT、私钥块、连接串里的口令）。"
                  "★ 强烈建议保持开启：docker inspect 这类命令会原样回显容器环境变量")
    desensitize_keywords = models.TextField(
        verbose_name="自定义脱敏关键词", blank=True, default="",
        help_text="一行一个，**按子串**匹配（不是正则），命中后替换为 ***。"
                  "适合加公司域名、内部账号名等。少于 3 个字符会被忽略")
    chat_timeout = models.IntegerField(
        default=90, verbose_name="单次对话时长上限(秒)",
        help_text="一次提问从开始到放弃的总时长。Agent 会在超时前收敛并给出当前结论。"
                  "网关的读超时是 600 秒，这里留足余量")
    daily_round_limit = models.IntegerField(
        default=300, verbose_name="每人每日轮次上限",
        help_text="「模型调用轮次」按人按自然日累计。超出后当天不能再提问（防止刷爆自己的 Key 额度）")
    daily_token_limit = models.IntegerField(
        default=800000, verbose_name="每人每日 token 上限",
        help_text="按人按自然日累计。一般用不到，作为兜底")
    max_rounds = models.IntegerField(default=12, verbose_name="单次对话最大轮次",
                                     help_text="Agent 最多调用多少次工具后强制收敛")
    max_servers = models.IntegerField(default=5, verbose_name="单轮最大机器数",
                                      help_text="一次工具调用最多并发操作的服务器数量")
    command_timeout = models.IntegerField(default=30, verbose_name="单命令超时(秒)",
                                          help_text="SSH 命令执行的超时时间")
    max_workers = models.IntegerField(default=4, verbose_name="并发线程数",
                                      help_text="批量执行 SSH 时的线程池大小")
    max_output_chars = models.IntegerField(default=8000, verbose_name="单次输出字符上限",
                                           help_text="工具输出回灌给大模型前的截断长度")

    class Meta:
        db_table = "ai_guard_config"
        verbose_name = "AI 护栏配置"
        verbose_name_plural = verbose_name

    @classmethod
    def load(cls):
        """取全局唯一配置，不存在则用默认值创建。"""
        obj = cls.objects.order_by("id").first()
        if obj is None:
            obj = cls.objects.create()
        return obj

    def __str__(self):
        return "AI 护栏配置"


# ============================================================
# 智能问答：会话 / 工具调用台账 / 用量
# ============================================================

CHAT_STATUS_CHOICES = (
    ("active", "进行中"),
    ("done", "已完成"),
    ("failed", "失败"),
)

TOOL_CALL_STATUS_CHOICES = (
    ("success", "成功"),
    ("empty", "成功但无输出"),
    ("failed", "执行失败"),
    ("rejected", "被护栏拒绝"),
    ("blocked", "无资产授权"),
    ("error", "参数或系统错误"),
)


class AiChatSession(CoreModel):
    """一次「智能问答」会话。

    ★ `messages` 直接存 OpenAI 格式的消息数组（含 system 与 tool 消息），
      这样"续问"不需要任何额外拼装逻辑，也让审计能完整回放模型看到了什么。
      ★ 入库前**已经脱敏**（见 desensitize.py）—— 所以这一列里不会有明文凭据。

    ★ `readonly` 恒为 True：P0 只提供只读工具。留字段是为了将来加写操作时
      能一眼看出"这条会话当时是只读的"（历史会话的语义不会被后续版本改写）。
    """

    owner = models.ForeignKey(
        to="system.Users", on_delete=models.CASCADE, db_constraint=False,
        null=True, blank=True, related_name="ai_chat_sessions",
        verbose_name="归属用户",
        help_text="会话与 Key 一样按人隔离：别人看不到你的提问与命令输出")
    title = models.CharField(max_length=128, verbose_name="标题", blank=True,
                             help_text="取第一条提问的前 40 字，便于在列表里辨认")
    credential = models.ForeignKey(
        to="bastion.Credential", on_delete=models.SET_NULL, db_constraint=False,
        null=True, blank=True, related_name="ai_chat_sessions",
        verbose_name="使用的凭据",
        help_text="本会话所有 SSH 都用这一条凭据（任务级统一凭证，与「命令下发」一致）")
    provider = models.ForeignKey(
        to="aiagent.AiProviderConfig", on_delete=models.SET_NULL, db_constraint=False,
        null=True, blank=True, related_name="ai_chat_sessions",
        verbose_name="使用的模型配置",
        help_text="会话创建时选定的模型配置；配置被删则本字段置空（问历史时提示重选）")
    messages = models.JSONField(default=list, blank=True, verbose_name="消息上下文",
                                help_text="OpenAI 格式的消息数组（已脱敏）")
    readonly = models.BooleanField(default=True, verbose_name="只读会话")
    rounds = models.IntegerField(default=0, verbose_name="累计模型轮次")
    tool_count = models.IntegerField(default=0, verbose_name="累计工具调用次数")
    total_tokens = models.IntegerField(default=0, verbose_name="累计消耗 token")
    status = models.CharField(max_length=20, choices=CHAT_STATUS_CHOICES,
                              default="active", verbose_name="状态")
    last_error = models.TextField(verbose_name="最近错误", null=True, blank=True)

    class Meta:
        db_table = "ai_chat_session"
        verbose_name = "AI 问答会话"
        verbose_name_plural = verbose_name
        ordering = ["-update_datetime"]
        indexes = [
            models.Index(fields=["owner"], name="ai_chat_owner_idx"),
        ]

    def __str__(self):
        return "%s(%s)" % (self.title or "未命名会话", self.pk)


class AiToolCall(CoreModel):
    """工具调用台账 —— 本功能的**审计主表**。

    ★ 为什么「被拒绝的尝试」也要落一行：
      安全审计关心的不是"AI 干了什么"，而是"AI 想干什么、被什么拦住了"。
      只记成功调用会看不出有人在用 AI 试探读 /etc/shadow。
      所以 `rejected`（护栏拒绝）/ `blocked`（无资产授权）同样写台账。

    ★ `stdout_excerpt` / `stderr_excerpt` 存的是**已脱敏、已截断**的片段：
      足够复盘（看到命令返回了什么），但不构成二次泄密面。
    """

    session = models.ForeignKey(
        to="aiagent.AiChatSession", on_delete=models.CASCADE, db_constraint=False,
        related_name="tool_logs", verbose_name="所属会话")
    owner = models.ForeignKey(
        to="system.Users", on_delete=models.CASCADE, db_constraint=False,
        null=True, blank=True, related_name="ai_tool_calls",
        verbose_name="归属用户",
        help_text="冗余自会话，便于「我的台账」直接按人过滤")
    round_index = models.IntegerField(default=0, verbose_name="第几轮")
    tool_name = models.CharField(max_length=64, verbose_name="工具名")
    server = models.ForeignKey(
        to="cmdb.Server", on_delete=models.SET_NULL, db_constraint=False,
        null=True, blank=True, related_name="ai_tool_calls",
        verbose_name="目标服务器")
    server_label = models.CharField(max_length=128, verbose_name="目标显示名", blank=True)
    ip = models.CharField(max_length=64, verbose_name="目标IP", blank=True)
    command = models.TextField(verbose_name="命令", blank=True)
    purpose = models.CharField(max_length=255, verbose_name="调用理由", blank=True)
    status = models.CharField(max_length=20, choices=TOOL_CALL_STATUS_CHOICES,
                              default="success", verbose_name="结果")
    reject_reason = models.CharField(max_length=512, verbose_name="拒绝原因", blank=True)
    exit_code = models.IntegerField(verbose_name="退出码", null=True, blank=True)
    duration = models.FloatField(verbose_name="耗时(秒)", null=True, blank=True)
    stdout_excerpt = models.TextField(verbose_name="标准输出(脱敏截断)", blank=True)
    stderr_excerpt = models.TextField(verbose_name="标准错误(脱敏截断)", blank=True)
    desensitized = models.CharField(max_length=255, verbose_name="脱敏命中", blank=True,
                                    help_text="命中的脱敏规则，如「键值对口令×3」")

    class Meta:
        db_table = "ai_tool_call"
        verbose_name = "AI 工具调用台账"
        verbose_name_plural = verbose_name
        ordering = ["id"]
        indexes = [
            models.Index(fields=["session"], name="ai_toolcall_session_idx"),
            models.Index(fields=["owner"], name="ai_toolcall_owner_idx"),
        ]

    def __str__(self):
        return "%s@%s(%s)" % (self.tool_name, self.server_label or self.ip, self.status)


class AiUsage(CoreModel):
    """按「用户 × 自然日」累计用量 —— 每日配额的唯一事实来源。

    ★ 为什么不从会话/台账里聚合算：
      `AiChatSession.rounds` 是会话累计值，跨天后仍是同一个数，
      按 "update_datetime 在今天" 去 Sum 会把昨天的轮次算进今天。
      单独一张 (owner, day) 唯一的小表，累加语义明确，也便于直接查"谁用得多"。
    """

    owner = models.ForeignKey(
        to="system.Users", on_delete=models.CASCADE, db_constraint=False,
        null=True, blank=True, related_name="ai_usages", verbose_name="归属用户")
    day = models.DateField(verbose_name="日期")
    rounds = models.IntegerField(default=0, verbose_name="模型调用轮次")
    tokens = models.IntegerField(default=0, verbose_name="消耗 token")
    requests = models.IntegerField(default=0, verbose_name="对话次数")

    class Meta:
        db_table = "ai_usage"
        verbose_name = "AI 每日用量"
        verbose_name_plural = verbose_name
        ordering = ["-day", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "day"], name="ai_usage_owner_day_uniq"),
        ]

    def __str__(self):
        return "%s@%s rounds=%s" % (
            getattr(self.owner, "name", None) or self.owner_id, self.day, self.rounds)

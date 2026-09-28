<template>
	<div class="ai-guard">
		<el-alert
			type="warning"
			:closable="false"
			show-icon
			class="guard-alert"
			title="安全护栏是「智能问答」执行服务器命令的唯一闸门"
			description="策略是「默认拒绝」——白名单之外的一律不让跑；黑名单优先于白名单。这里改错只会导致命令被拦下来（模型会看到拒绝原因并换一条），不会造成危险操作。"
		/>

		<!-- ===== 运行开关与限额 ===== -->
		<el-card shadow="never" class="guard-card">
			<template #header><span class="card-title">运行开关与限额</span></template>
			<el-form label-width="130px" class="guard-form">
				<el-form-item label="允许调用工具">
					<el-switch v-model="form.enabled_tools" />
					<span class="form-hint">
						关闭后 AI <b>一次 SSH 都不建</b>，只能基于 CMDB 已有信息做纯问答。
						适用于「先给同事开放问答、但暂时不让它碰服务器」的过渡期。
					</span>
				</el-form-item>
				<el-form-item label="只读模式">
					<el-switch v-model="form.readonly_mode" />
					<span class="form-hint">
						这是<b>命令执行的总开关（应急刹车）</b>：关闭后 AI 完全不执行任何命令（含只读命令），
						因为 P0 没有提供任何写操作工具，关掉它没有更宽松的档位可落。日常请保持开启。
					</span>
				</el-form-item>
				<el-row :gutter="16">
					<el-col :xs="24" :sm="12" :md="8">
						<el-form-item label="单会话最大轮次">
							<el-input-number v-model="form.max_rounds" :min="1" :max="50" controls-position="right" />
							<span class="form-hint">AI 最多调用 多少次工具 后强制收敛</span>
						</el-form-item>
					</el-col>
					<el-col :xs="24" :sm="12" :md="8">
						<el-form-item label="单次对话时长">
							<el-input-number v-model="form.chat_timeout" :min="15" :max="600" controls-position="right" />
							<span class="form-hint">秒。到时强制收敛并给出当前结论</span>
						</el-form-item>
					</el-col>
					<el-col :xs="24" :sm="12" :md="8">
						<el-form-item label="单轮最大机器数">
							<el-input-number v-model="form.max_servers" :min="1" :max="50" controls-position="right" />
							<span class="form-hint">一次工具调用最多并发几台服务器</span>
						</el-form-item>
					</el-col>
					<el-col :xs="24" :sm="12" :md="8">
						<el-form-item label="单命令超时">
							<el-input-number v-model="form.command_timeout" :min="5" :max="600" controls-position="right" />
							<span class="form-hint">秒</span>
						</el-form-item>
					</el-col>
					<el-col :xs="24" :sm="12" :md="8">
						<el-form-item label="并发线程数">
							<el-input-number v-model="form.max_workers" :min="1" :max="32" controls-position="right" />
							<span class="form-hint">SSH 线程池大小，建议 ≤ 8</span>
						</el-form-item>
					</el-col>
					<el-col :xs="24" :sm="12" :md="8">
						<el-form-item label="单次输出上限">
							<el-input-number v-model="form.max_output_chars" :min="500" :max="100000" :step="500" controls-position="right" />
							<span class="form-hint">字符，回灌给模型前的截断长度</span>
						</el-form-item>
					</el-col>
					<el-col :xs="24" :sm="12" :md="8">
						<el-form-item label="每人每日轮次">
							<el-input-number v-model="form.daily_round_limit" :min="0" :max="100000" :step="50" controls-position="right" />
							<span class="form-hint">按人按自然日累计，0 = 不限制</span>
						</el-form-item>
					</el-col>
					<el-col :xs="24" :sm="12" :md="8">
						<el-form-item label="每人每日 token">
							<el-input-number v-model="form.daily_token_limit" :min="0" :max="100000000" :step="100000" controls-position="right" />
							<span class="form-hint">兜底项，一般用不到；0 = 不限制</span>
						</el-form-item>
					</el-col>
				</el-row>
				<div class="mini-tip">
					★ 配额是「每人各自算」的：因为每个用户在「模型配置」里填的是<b>自己的 API Key</b>，
					这里的上限防的是「某个人把自己的 Key 额度刷爆」，不是平台公共额度。
				</div>
			</el-form>
		</el-card>

		<!-- ===== 数据外发脱敏 ===== -->
		<el-card shadow="never" class="guard-card">
			<template #header>
				<span class="card-title">数据外发脱敏</span>
				<span class="card-sub">命令输出在发给大模型厂商之前，先把凭据类内容抹成 ***</span>
			</template>
			<el-form label-width="130px" class="guard-form">
				<el-form-item label="自动脱敏">
					<el-switch v-model="form.desensitize" />
					<span class="form-hint">
						★ <b>强烈建议保持开启</b>。内置规则覆盖：<code>KEY=value</code> 键值对、JSON 里的
						<code>"password": "x"</code>、连接串里的口令（<code>mysql://u:p@h</code>）、
						PEM 私钥块、云厂商 AK（AKIA/LTAI…）、<code>sk-</code>、GitHub/GitLab/Slack Token、
						JWT、<code>Bearer</code>/<code>Basic</code> 认证头。
						最典型的泄漏场景就是 <code>docker inspect</code> 原样回显容器的
						<code>MYSQL_ROOT_PASSWORD</code>。
					</span>
				</el-form-item>
				<el-form-item label="自定义关键词">
					<el-input
						v-model="form.desensitize_keywords"
						type="textarea"
						:rows="5"
						spellcheck="false"
						class="mono-box"
						placeholder="一行一个，例如：&#10;corp.example.com&#10;internal-db-01&#10;zhangsan"
					/>
					<div class="form-hint block">
						当前 <b>{{ keywordCount }}</b> 个生效关键词（少于 3 个字符的会被忽略）。
						这里按<b>子串</b>替换、<b>不是正则</b> —— 写错最多是不命中，不会让功能 500。
						适合加公司域名、内部主机名、内部账号名。
					</div>
				</el-form-item>
			</el-form>
		</el-card>

		<!-- ===== 白名单 / 黑名单 ===== -->
		<el-card shadow="never" class="guard-card">
			<template #header><span class="card-title">命令白名单 / 黑名单</span></template>
			<div class="mini-tip">
				一行一条，<b>前缀匹配</b>；空行与以 <code>#</code> 开头的行会被忽略（可以写注释）。当前共
				<b>{{ allowedCount }}</b> 条白名单、<b>{{ deniedCount }}</b> 条黑名单、<b>{{ pathCount }}</b> 条敏感路径。
			</div>
			<el-row :gutter="16">
				<el-col :xs="24" :md="12">
					<div class="list-head">
						<span class="list-title allowed">只读命令白名单</span>
						<span class="list-count">{{ allowedCount }} 条</span>
					</div>
					<el-input
						v-model="form.allowed_commands"
						type="textarea"
						:rows="20"
						spellcheck="false"
						class="mono-box"
					/>
					<div class="form-hint block">不在白名单内的一律拒绝。白名单可以写「裸命令」（如 <code>df</code>），靠下面的敏感路径兜底防读凭据。</div>
				</el-col>
				<el-col :xs="24" :md="12">
					<div class="list-head">
						<span class="list-title denied">危险命令黑名单</span>
						<span class="list-count">{{ deniedCount }} 条</span>
					</div>
					<el-input
						v-model="form.denied_commands"
						type="textarea"
						:rows="20"
						spellcheck="false"
						class="mono-box"
					/>
					<div class="form-hint block">命中即拒绝，优先级高于白名单。用来拦「能改状态」的子用法，如 <code>journalctl --vacuum</code>、<code>hostnamectl set-</code>。</div>
				</el-col>
			</el-row>

			<div class="list-head mt16">
				<span class="list-title path">敏感路径黑名单</span>
				<span class="list-count">{{ pathCount }} 条</span>
			</div>
			<el-input v-model="form.denied_paths" type="textarea" :rows="8" spellcheck="false" class="mono-box" />
			<div class="form-hint block">命令文本里出现这些片段就拒绝，专门挡住「用白名单里的 grep / tail 去读凭据文件」。</div>
		</el-card>

		<!-- ===== 命令试跑 ===== -->
		<el-card shadow="never" class="guard-card">
			<template #header>
				<span class="card-title">命令试跑</span>
				<span class="card-sub">纯本地校验，不会连接任何服务器，保存前可先在这里验证策略</span>
			</template>

			<div class="try-row">
				<el-input
					v-model="tryCommand"
					class="try-input"
					placeholder="输入一条命令，例如：df -hT /var/log"
					clearable
					@keyup.enter="doCheck"
				/>
				<el-button type="primary" :loading="checking" @click="doCheck">试跑</el-button>
			</div>

			<div v-if="tryResult" class="try-result">
				<el-tag :type="tryResult.allowed ? 'success' : 'danger'" effect="dark" size="large">
					{{ tryResult.allowed ? '会被放行' : '会被拒绝' }}
				</el-tag>
				<span class="try-reason">{{ tryResult.allowed ? '该命令符合当前策略，AI 可以执行' : tryResult.reason }}</span>
				<div v-if="tryResult.segments && tryResult.segments.length" class="try-seg">
					<span class="form-hint">拆成 {{ tryResult.segments.length }} 段后逐段校验：</span>
					<el-tag v-for="(s, i) in tryResult.segments" :key="i" size="small" class="seg-tag">{{ s }}</el-tag>
				</div>
			</div>

			<div class="quick-try">
				<span class="form-hint">快捷示例：</span>
				<el-button v-for="c in samples" :key="c" link type="primary" class="sample-btn" @click="quickCheck(c)">{{ c }}</el-button>
			</div>
		</el-card>

		<!-- ===== 底部操作 ===== -->
		<div class="guard-footer">
			<el-button :icon="Refresh" :loading="loading" @click="load">重新加载</el-button>
			<el-button type="primary" :loading="saving" @click="save">保存并立即生效</el-button>
			<span v-if="dirty" class="dirty-hint">有未保存的改动</span>
		</div>
	</div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Refresh } from '@element-plus/icons-vue';
import { GetGuard, UpdateGuard, CheckCommand } from './api';

/** 与后端 guard.parse_rules 保持一致的解析：去注释行 / 去空行 / 折叠空白 / 去重 */
function parseRules(text: string): string[] {
	const rules: string[] = [];
	const seen: any = {};
	for (const raw of String(text || '').split(/\r?\n/)) {
		let line = raw.trim();
		if (!line || line.startsWith('#')) continue;
		line = line.replace(/\s+/g, ' ');
		if (!seen[line]) {
			seen[line] = true;
			rules.push(line);
		}
	}
	return rules;
}

const EMPTY_FORM = {
	// 两层开关
	enabled_tools: true,
	readonly_mode: true,
	// 白/黑名单
	allowed_commands: '',
	denied_commands: '',
	denied_paths: '',
	// 外发脱敏
	desensitize: true,
	desensitize_keywords: '',
	// 运行参数
	max_rounds: 12,
	max_servers: 5,
	command_timeout: 30,
	chat_timeout: 90,
	max_workers: 4,
	max_output_chars: 8000,
	// 每人每日配额
	daily_round_limit: 300,
	daily_token_limit: 800000,
};

/** 与后端 desensitize.parse_keywords 一致：去空行 / 去 # 注释 / 去重，并忽略 < 3 字符的词 */
function parseKeywords(text: string): string[] {
	const out: string[] = [];
	const seen: any = {};
	for (const raw of String(text || '').split(/\r?\n/)) {
		const kw = raw.trim();
		if (!kw || kw.startsWith('#')) continue;
		if (kw.length < 3) continue;
		if (!seen[kw]) {
			seen[kw] = true;
			out.push(kw);
		}
	}
	return out;
}

export default defineComponent({
	name: 'aiGuard',
	setup() {
		const loading = ref(false);
		const saving = ref(false);
		const checking = ref(false);
		const form = ref<any>({ ...EMPTY_FORM });
		const snapshot = ref<string>('');
		const tryCommand = ref('');
		const tryResult = ref<any>(null);

		const samples = [
			'df -hT',
			'free -m',
			'docker ps -a',
			'uptime; rm -rf /tmp/x',
			'cat /etc/shadow',
			'journalctl --vacuum-size=100M',
		];

		const allowedCount = computed(() => parseRules(form.value.allowed_commands).length);
		const deniedCount = computed(() => parseRules(form.value.denied_commands).length);
		const pathCount = computed(() => parseRules(form.value.denied_paths).length);
		const keywordCount = computed(() => parseKeywords(form.value.desensitize_keywords).length);
		const dirty = computed(() => JSON.stringify(form.value) !== snapshot.value);

		const load = async () => {
			loading.value = true;
			try {
				const res: any = await GetGuard();
				if (res.code === 2000) {
					const d = res.data || {};
					// 只取后端字段里我们关心的，避免把 id / counts 等回写进表单
					const next: any = { ...EMPTY_FORM };
					Object.keys(EMPTY_FORM).forEach((k) => {
						if (d[k] !== undefined && d[k] !== null) next[k] = d[k];
					});
					form.value = next;
					snapshot.value = JSON.stringify(next);
				} else {
					ElMessage.error(res.msg || '读取护栏配置失败');
				}
			} catch (e) {
				ElMessage.error('读取护栏配置失败');
			} finally {
				loading.value = false;
			}
		};

		const save = async () => {
			if (!allowedCount.value) {
				ElMessage.warning('白名单为空 = 任何命令都执行不了，请至少保留几条只读命令');
				return;
			}
			// ★ 只读模式是「命令执行总开关」，关掉等于 AI 完全不能碰服务器。
			//   这是应急刹车，必须显式确认（旧文案说"不再强制只读语义"会让人以为
			//   只是放宽了限制，与实际行为不符）。
			if (!form.value.readonly_mode) {
				try {
					await ElMessageBox.confirm(
						'关闭「只读模式」= 关闭命令执行总开关：AI 将完全不执行任何命令（包括 uptime、df 这类只读命令），' +
							'只能基于 CMDB 已有信息回答。这是应急刹车，不是「放开权限」。确定按当前开关保存吗？',
						'即将关闭命令执行',
						{ type: 'warning', confirmButtonText: '仍然保存', cancelButtonText: '去开启' }
					);
				} catch (e) {
					return;
				}
			}
			// 同理：关掉工具开关会让 AI 一次 SSH 都不建，先提醒一句
			if (!form.value.enabled_tools && form.value.readonly_mode) {
				try {
					await ElMessageBox.confirm(
						'关闭「允许调用工具」后，AI 只能做纯问答、不会再连服务器排查。确定吗？',
						'即将关闭工具调用',
						{ type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
					);
				} catch (e) {
					return;
				}
			}
			// 脱敏是数据边界，关掉意味着密码可能原文发给大模型厂商，二次确认
			if (!form.value.desensitize) {
				try {
					await ElMessageBox.confirm(
						'关闭「自动脱敏」后，命令输出会**原样**发给大模型厂商 —— ' +
							'docker inspect 之类的输出里常常带明文密码。确定要关闭吗？',
						'即将关闭脱敏',
						{ type: 'error', confirmButtonText: '仍然关闭', cancelButtonText: '保持开启' }
					);
				} catch (e) {
					return;
				}
			}
			saving.value = true;
			try {
				const res: any = await UpdateGuard({ ...form.value });
				if (res.code === 2000) {
					ElMessage.success(res.msg || '护栏配置已保存，立即生效');
					snapshot.value = JSON.stringify(form.value);
				} else {
					ElMessage.error(res.msg || '保存失败');
				}
			} catch (e) {
				ElMessage.error('保存失败');
			} finally {
				saving.value = false;
			}
		};

		const doCheck = async () => {
			const cmd = (tryCommand.value || '').trim();
			if (!cmd) {
				ElMessage.warning('请先输入一条命令');
				return;
			}
			checking.value = true;
			try {
				const res: any = await CheckCommand(cmd);
				if (res.code === 2000) {
					tryResult.value = res.data || null;
				} else {
					tryResult.value = null;
					ElMessage.error(res.msg || '试跑失败');
				}
			} catch (e) {
				tryResult.value = null;
				ElMessage.error('试跑失败');
			} finally {
				checking.value = false;
			}
		};

		const quickCheck = (cmd: string) => {
			tryCommand.value = cmd;
			doCheck();
		};

		onMounted(() => {
			load();
		});

		return {
			loading, saving, checking, form, dirty,
			tryCommand, tryResult, samples,
			allowedCount, deniedCount, pathCount, keywordCount,
			load, save, doCheck, quickCheck,
			Refresh,
		};
	},
});
</script>

<style scoped>
.ai-guard {
	padding: 4px;
}
.guard-alert {
	margin-bottom: 12px;
}
.guard-card {
	margin-bottom: 12px;
	border-radius: 10px;
}
.card-title {
	font-size: 15px;
	font-weight: 600;
	color: #303133;
	padding-left: 10px;
	border-left: 4px solid #409eff;
	line-height: 1.2;
}
.card-sub {
	margin-left: 10px;
	font-size: 12px;
	color: #909399;
}
.guard-form :deep(.el-form-item) {
	margin-bottom: 14px;
}
.form-hint {
	margin-left: 8px;
	font-size: 12px;
	color: #909399;
}
.form-hint.block {
	display: block;
	margin: 6px 0 0;
	line-height: 1.6;
}
.mini-tip {
	font-size: 12px;
	color: #606266;
	background: #f5f7fa;
	border-radius: 6px;
	padding: 8px 12px;
	margin-bottom: 12px;
	line-height: 1.7;
}
.mono-box :deep(.el-textarea__inner) {
	font-family: Consolas, Monaco, 'Courier New', monospace;
	font-size: 12.5px;
	line-height: 1.6;
}
.list-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 6px;
}
.list-head.mt16 {
	margin-top: 16px;
}
.list-title {
	font-size: 13px;
	font-weight: 600;
	color: #303133;
	padding-left: 8px;
	border-left: 3px solid #909399;
	line-height: 1.1;
}
.list-title.allowed {
	border-left-color: #67c23a;
}
.list-title.denied {
	border-left-color: #f56c6c;
}
.list-title.path {
	border-left-color: #e6a23c;
}
.list-count {
	font-size: 12px;
	color: #909399;
}
.try-row {
	display: flex;
	gap: 8px;
	align-items: center;
}
.try-input {
	flex: 1;
}
.try-result {
	margin-top: 12px;
	padding: 12px;
	background: #fafafa;
	border: 1px solid #ebeef5;
	border-radius: 8px;
}
.try-reason {
	margin-left: 10px;
	font-size: 13px;
	color: #606266;
	line-height: 1.7;
}
.try-seg {
	margin-top: 8px;
	line-height: 2;
}
.seg-tag {
	margin: 2px 4px 2px 0;
	font-family: Consolas, Monaco, 'Courier New', monospace;
}
.quick-try {
	margin-top: 12px;
	line-height: 2;
}
.sample-btn {
	margin-right: 8px;
	font-family: Consolas, Monaco, 'Courier New', monospace;
}
.guard-footer {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 4px 0 12px;
}
.dirty-hint {
	font-size: 12px;
	color: #e6a23c;
}
</style>

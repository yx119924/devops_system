<template>
	<el-drawer
		v-model="show"
		:title="`流水线编排 · ${pipeline?.name || ''}`"
		size="94%"
		:close-on-click-modal="false"
		destroy-on-close
		@open="onOpen"
	>
		<div v-loading="loading" class="designer">
			<!-- ─────────── 左：节点流 ─────────── -->
			<div class="pane-left">
				<div class="pane-head">
					<span class="pane-title">流程节点</span>
					<el-button size="small" type="primary" plain @click="addNode">+ 添加节点</el-button>
				</div>

				<div class="node-flow">
					<el-empty v-if="!nodes.length" description="还没有节点，点「添加节点」开始编排" :image-size="70" />
					<template v-for="(n, i) in nodes" :key="n._key">
						<div class="node-card" :class="{ active: i === currentIndex }" @click="currentIndex = i">
							<div class="node-seq">{{ i + 1 }}</div>
							<div class="node-body">
								<div class="node-name">{{ n.name || '未命名节点' }}</div>
								<div class="node-meta">
									<el-tag size="small" effect="plain">{{ typeLabel(n.node_type) }}</el-tag>
									<span v-if="n.on_failure === 'continue'" class="tag-warn">失败继续</span>
									<span v-if="targetCount(n)" class="tag-dim">{{ targetCount(n) }} 台目标</span>
								</div>
							</div>
							<div class="node-ops" @click.stop>
								<el-button link size="small" :disabled="i === 0" @click="move(i, -1)">上移</el-button>
								<el-button link size="small" :disabled="i === nodes.length - 1" @click="move(i, 1)">下移</el-button>
								<el-button link size="small" type="danger" @click="removeNode(i)">删除</el-button>
							</div>
						</div>
						<div v-if="i < nodes.length - 1" class="flow-arrow">↓</div>
					</template>
				</div>

				<div class="pane-tip">
					顺序执行：从上到下依次推进。失败后走哪个方向由每个节点自己的「失败处理」决定。
					★ 现在刻意**不做自由拖拽画布** —— 你要的是"点节点配语法"，不是画连线。
				</div>
			</div>

			<!-- ─────────── 右：配置 ─────────── -->
			<div class="pane-right">
				<el-tabs v-model="tab">
					<el-tab-pane label="节点配置" name="node">
						<el-empty v-if="!currentNode" description="先在左侧选中一个节点" :image-size="70" />

						<el-form v-else :model="currentNode" label-width="106px" size="default">
							<el-form-item label="节点名称">
								<el-input v-model="currentNode.name" maxlength="64" placeholder="如 上传制品 / 重启服务" />
							</el-form-item>
							<el-form-item label="节点类型">
								<el-select v-model="currentNode.node_type" style="width: 220px" @change="onTypeChange">
									<el-option v-for="t in options.node_types" :key="t.value" :label="t.label" :value="t.value" />
								</el-select>
							</el-form-item>
							<el-form-item label="失败处理">
								<el-radio-group v-model="currentNode.on_failure">
									<el-radio v-for="o in options.on_failure_options" :key="o.value" :label="o.value">{{ o.label }}</el-radio>
								</el-radio-group>
								<div class="hint">
									「失败即停止」= 后续节点不再执行；「失败继续」= 后面的节点照跑（整体会标为"部分失败"，不会假装成功）。
								</div>
							</el-form-item>

							<el-divider content-position="left">节点配置</el-divider>

							<!-- 参数化 -->
							<template v-if="currentNode.node_type === 'param'">
								<el-alert
									type="info"
									:closable="false"
									show-icon
									title="这个节点不做事，只作为流程图上的起点标记"
									description="真正的参数在右侧「运行时参数」标签页里定义；节点里用 {{参数名}} 引用它们。"
								/>
							</template>

							<!-- 命令 / 检查 -->
							<template v-else-if="isCmdType(currentNode.node_type)">
								<el-form-item label="命令">
									<el-input
										v-model="currentNode.config.command"
										type="textarea"
										:rows="6"
										placeholder="如 systemctl restart myapp&#10;支持 {{参数名}} 占位符，例如 tar -xzf {{version}}.tar.gz"
									/>
									<div class="hint">
										这里就是你要的「pipeline 语法」——命令按行原样交给目标机的 shell 执行。
										★ 只做一层字面替换，不做表达式求值。
									</div>
								</el-form-item>
								<el-form-item label="目标服务器">
									<el-select
										v-model="currentNode.config.cmdb_targets"
										multiple
										filterable
										clearable
										placeholder="从 CMDB 服务器多选"
										style="width: 100%"
									>
										<el-option
											v-for="s in servers"
											:key="s.id"
											:label="`${s.hostname} (${s.ip})`"
											:value="s.id"
										/>
									</el-select>
									<div class="hint">
										只能选到你有操作授权的服务器；连接地址执行时以 CMDB 最新 IP 为准。
									</div>
								</el-form-item>
								<el-form-item label="凭据">
									<el-select v-model="currentNode.config.credential" clearable placeholder="留空则用流水线默认凭据" style="width: 260px">
										<el-option v-for="c in options.credentials" :key="c.id" :label="c.name" :value="c.id" />
									</el-select>
								</el-form-item>
								<el-form-item label="单台超时">
									<el-input-number v-model="currentNode.config.timeout" :min="1" :max="options.limits.max_node_timeout" />
									<span class="hint-inline">
										秒（上限 {{ options.limits.max_node_timeout }}）。★ 节点还有一个总时长预算，
										目标多的时候超出的目标会被明确标失败，而不是悄悄不发。
									</span>
								</el-form-item>
							</template>

							<!-- 上传制品 -->
							<template v-else-if="currentNode.node_type === 'upload'">
								<el-form-item label="制品文件">
									<el-input v-model="currentNode.config.local_path" placeholder="如 myapp-1.2.0.tar.gz" />
									<div class="hint">
										★ 只能是**服务器上制品目录内**的文件（相对路径按该目录解析）。
										这是刻意的限制：否则「发布」权限会变成任意文件读取权限。
										上传前把包放到：<code>/backend/media/release_artifacts/</code>
									</div>
								</el-form-item>
								<el-form-item label="目标机路径">
									<el-input v-model="currentNode.config.remote_path" placeholder="如 /opt/app/myapp.tar.gz" />
									<div class="hint">必须是绝对路径；目标机目录需已存在（平台不自动建目录，避免掩盖路径写错）。</div>
								</el-form-item>
								<el-form-item label="目标服务器">
									<el-select v-model="currentNode.config.cmdb_targets" multiple filterable clearable style="width: 100%">
										<el-option v-for="s in servers" :key="s.id" :label="`${s.hostname} (${s.ip})`" :value="s.id" />
									</el-select>
								</el-form-item>
								<el-form-item label="凭据">
									<el-select v-model="currentNode.config.credential" clearable placeholder="留空则用流水线默认凭据" style="width: 260px">
										<el-option v-for="c in options.credentials" :key="c.id" :label="c.name" :value="c.id" />
									</el-select>
								</el-form-item>
							</template>

							<!-- 构建 -->
							<template v-else-if="currentNode.node_type === 'build'">
								<el-form-item label="Jenkins">
									<el-select
										v-model="currentNode.config.jenkins_server_id"
										style="width: 320px"
										@change="loadJobs"
									>
										<el-option v-for="j in options.jenkins_servers" :key="j.id" :label="`${j.name} (${j.url})`" :value="j.id" />
									</el-select>
								</el-form-item>
								<el-form-item label="Job">
									<el-select
										v-model="currentNode.config.job"
										filterable
										allow-create
										default-first-option
										placeholder="选择或直接输入 Job 路径"
										style="width: 100%"
									>
										<el-option v-for="j in jobs" :key="j.full_path" :label="j.full_path" :value="j.full_path" />
									</el-select>
									<div class="hint">
										下拉只列出你有目录授权的 Job（分环境授权照样生效）。
										拉不到也可以直接输入，如 <code>dev/中心/backend</code>。
									</div>
								</el-form-item>
								<el-form-item label="构建参数">
									<div class="kv-editor">
										<div v-for="(row, ki) in currentNode.config._params" :key="ki" class="kv-row">
											<el-input v-model="row.k" placeholder="参数名" style="width: 220px" />
											<el-input v-model="row.v" placeholder="值（支持 {{参数名}}）" style="width: 300px" />
											<el-button link type="danger" @click="currentNode.config._params.splice(ki, 1)">删除</el-button>
										</div>
										<el-button size="small" plain @click="currentNode.config._params.push({ k: '', v: '' })">
											+ 添加参数
										</el-button>
										<div class="hint">
											留空则走 <code>/build</code>；有参数走 <code>/buildWithParameters</code>（参数化 Job 走前者会 400，后端会自动降级重试）。
										</div>
									</div>
								</el-form-item>
								<el-form-item label="等待时长">
									<el-input-number v-model="currentNode.config.wait_timeout" :min="30" :max="options.limits.max_build_wait" />
									<span class="hint-inline">秒（上限 {{ options.limits.max_build_wait }}）</span>
								</el-form-item>
							</template>

							<!-- 通知 -->
							<template v-else-if="currentNode.node_type === 'notify'">
								<el-form-item label="通知渠道">
									<el-select v-model="currentNode.config.channel_id" style="width: 280px">
										<el-option v-for="c in options.channels" :key="c.id" :label="`${c.name}（${c.type}）`" :value="c.id" />
									</el-select>
								</el-form-item>
								<el-form-item label="触发条件">
									<el-select v-model="currentNode.config.on" style="width: 200px">
										<el-option v-for="o in notifyOnOptions" :key="o.value" :label="o.label" :value="o.value" />
									</el-select>
								</el-form-item>
								<el-form-item label="标题">
									<el-input v-model="currentNode.config.title" placeholder="留空则为「流水线通知」" />
								</el-form-item>
								<el-form-item label="内容">
									<el-input
										v-model="currentNode.config.content"
										type="textarea"
										:rows="4"
										placeholder="留空则自动生成（流水线名 / 参数 / 当前节点 / 结果）"
									/>
								</el-form-item>
							</template>
						</el-form>
					</el-tab-pane>

					<!-- ─────────── 运行时参数 ─────────── -->
					<el-tab-pane label="运行时参数" name="params">
						<el-alert
							type="info"
							:closable="false"
							show-icon
							title="发起执行时会让填的参数"
							description="节点配置里用 {{参数名}} 引用。参数名只允许字母、数字、下划线；未在定义里出现的值在执行时会被丢弃（避免界面上看不到、却能影响发布结果的隐形输入）。"
							class="mb12"
						/>
						<div v-for="(p, pi) in paramDefs" :key="pi" class="param-row">
							<el-input v-model="p.key" placeholder="参数名，如 version" style="width: 200px" />
							<el-input v-model="p.label" placeholder="显示名，如 版本号" style="width: 200px" />
							<el-input v-model="p.default" placeholder="默认值" style="width: 220px" />
							<el-checkbox v-model="p.required">必填</el-checkbox>
							<el-button link type="danger" @click="paramDefs.splice(pi, 1)">删除</el-button>
						</div>
						<el-button size="small" plain @click="paramDefs.push({ key: '', label: '', default: '', required: false })">
							+ 添加参数
						</el-button>
					</el-tab-pane>
				</el-tabs>
			</div>
		</div>

		<template #footer>
			<div class="footer-bar">
				<div class="footer-left">
					<el-button :disabled="!currentNode" @click="preview">预检本节点</el-button>
					<span class="hint-inline">预检不会真执行（不触发构建、不连目标机、不发通知）</span>
				</div>
				<div>
					<el-button @click="show = false">关闭</el-button>
					<el-button type="primary" :loading="saving" @click="save">保存编排</el-button>
				</div>
			</div>
		</template>

		<!-- 预检结果 -->
		<el-dialog v-model="previewVisible" title="节点预检结果" width="760px" append-to-body>
			<el-alert v-if="previewResult.ok" type="success" :closable="false" show-icon title="静态检查通过" class="mb12" />
			<el-alert v-else type="error" :closable="false" show-icon title="发现问题，保存执行前请先修正" class="mb12" />
			<el-alert v-for="(e, ei) in previewResult.errors || []" :key="`e${ei}`" type="error" :title="e" :closable="false" show-icon class="mb12" />
			<el-alert v-for="(w, wi) in previewResult.warnings || []" :key="`w${wi}`" type="warning" :title="w" :closable="false" show-icon class="mb12" />

			<h4>替换后会执行的内容</h4>
			<pre class="code-block">{{ prettyRendered }}</pre>

			<h4 v-if="(previewResult.targets || []).length">目标服务器（地址以 CMDB 现值为准）</h4>
			<el-table v-if="(previewResult.targets || []).length" :data="previewResult.targets" size="small" border>
				<el-table-column prop="label" label="主机名" />
				<el-table-column prop="ip" label="IP" width="150" />
				<el-table-column prop="ssh_port" label="端口" width="80" />
				<el-table-column prop="status" label="状态" width="100" />
			</el-table>

			<div class="hint mt8">凭据：{{ previewResult.credential || '（未指定，将使用流水线默认凭据）' }}</div>
			<div class="hint">{{ previewResult.note }}</div>
		</el-dialog>
	</el-drawer>
</template>

<script lang="ts">
import { defineComponent, ref, computed, watch } from 'vue';
import { ElMessage } from 'element-plus';
import * as api from './api';

/** 节点配置里那些"前端临时用、不该发给后端"的键 */
const LOCAL_KEYS = ['_key', '_params', 'cmdb_targets'];

let uid = 0;
const nextKey = () => `n${Date.now()}_${uid++}`;

function defaultsFor(type: string) {
	if (type === 'command' || type === 'check') {
		return { command: '', cmdb_targets: [], credential: null, timeout: 30 };
	}
	if (type === 'upload') {
		return { local_path: '', remote_path: '', cmdb_targets: [], credential: null };
	}
	if (type === 'build') {
		return { jenkins_server_id: null, job: '', _params: [], wait_timeout: 600 };
	}
	if (type === 'notify') {
		return { channel_id: null, on: 'always', title: '', content: '' };
	}
	return {};
}

export default defineComponent({
	name: 'ReleasePipelineDesigner',
	props: {
		modelValue: { type: Boolean, default: false },
		pipeline: { type: Object, default: null },
	},
	emits: ['update:modelValue', 'saved'],
	setup(props, { emit }) {
		const show = computed({
			get: () => props.modelValue,
			set: (v: boolean) => emit('update:modelValue', v),
		});

		const loading = ref(false);
		const saving = ref(false);
		const tab = ref('node');
		const nodes = ref<any[]>([]);
		const currentIndex = ref(-1);
		const servers = ref<any[]>([]);
		const jobs = ref<any[]>([]);
		const options = ref<any>({
			credentials: [], jenkins_servers: [], channels: [],
			node_types: [], on_failure_options: [], notify_on_options: [],
			limits: { max_node_timeout: 300, max_build_wait: 600, max_targets_per_node: 50 },
		});
		const paramDefs = ref<any[]>([]);

		const previewVisible = ref(false);
		const previewResult = ref<any>({});

		const currentNode = computed(() => nodes.value[currentIndex.value] || null);
		const notifyOnOptions = computed(() => [
			{ value: 'always', label: '总是通知' },
			{ value: 'success', label: '仅成功时' },
			{ value: 'failure', label: '仅失败时' },
		]);
		const prettyRendered = computed(() => JSON.stringify(previewResult.value.rendered || {}, null, 2));

		const typeLabel = (t: string) =>
			(options.value.node_types || []).find((o: any) => o.value === t)?.label || t;

		const isCmdType = (t: string) => t === 'command' || t === 'check';

		const targetCount = (n: any) =>
			(isCmdType(n.node_type) || n.node_type === 'upload') ? (n.config?.cmdb_targets || []).length : 0;

		/** 后端 config → 前端可编辑形态（把 targets 拆成 cmdb_targets、parameters 拆成 _params） */
		function toEditable(raw: any) {
			const cfg = { ...(raw.config || {}) };
			const node: any = {
				_key: nextKey(),
				id: raw.id || null,
				name: raw.name || '',
				node_type: raw.node_type || 'command',
				on_failure: raw.on_failure || 'stop',
				pos_x: raw.pos_x || 0,
				pos_y: raw.pos_y || 0,
				config: cfg,
			};
			if (isCmdType(node.node_type) || node.node_type === 'upload') {
				cfg.cmdb_targets = (cfg.targets || []).map((t: any) => t.server_id).filter(Boolean);
			}
			if (node.node_type === 'build') {
				cfg._params = Object.entries(cfg.parameters || {}).map(([k, v]) => ({ k, v }));
			}
			return node;
		}

		/** 前端形态 → 后端 payload */
		function toPayload(node: any) {
			const cfg: any = {};
			Object.entries(node.config || {}).forEach(([k, v]) => {
				if (LOCAL_KEYS.includes(k)) return;
				cfg[k] = v;
			});
			if (isCmdType(node.node_type) || node.node_type === 'upload') {
				cfg.targets = (node.config?.cmdb_targets || []).map((sid: number) => {
					const s = servers.value.find((x: any) => x.id === sid) || {};
					return { server_id: sid, label: s.hostname || '', ip: s.ip || '', ssh_port: s.ssh_port || 22 };
				});
			}
			if (node.node_type === 'build') {
				const params: Record<string, string> = {};
				(node.config?._params || []).forEach((row: any) => {
					if (row && String(row.k || '').trim()) params[String(row.k).trim()] = row.v ?? '';
				});
				cfg.parameters = params;
			}
			if (node.node_type === 'notify') {
				cfg.title = node.config?.title || '';
				cfg.content = node.config?.content || '';
			}
			if (node.node_type === 'param') return {};
			return {
				id: node.id,
				name: node.name,
				node_type: node.node_type,
				on_failure: node.on_failure,
				pos_x: node.pos_x,
				pos_y: node.pos_y,
				config: cfg,
			};
		}

		async function loadServers() {
			try {
				const resp: any = await api.GetServerOptions();
				servers.value = resp?.data?.data || resp?.data || [];
			} catch (e) {
				servers.value = [];
			}
		}

		async function loadOptions() {
			try {
				const resp: any = await api.GetOptions();
				const d = resp?.data?.data || resp?.data || {};
				options.value = { ...options.value, ...d };
				if (d.limits) options.value.limits = d.limits;
			} catch (e) { /* 接口失败时保留默认值，不阻断编排 */ }
		}

		async function loadJobs(serverId?: number) {
			jobs.value = [];
			if (!serverId) return;
			try {
				// 这个接口会按当前用户的 Jenkins 目录授权过滤；拉不到就退化成"手输路径"
				const resp: any = await api.GetJobs(serverId);
				jobs.value = resp?.data?.data?.jobs || resp?.data?.jobs || [];
			} catch (e) {
				jobs.value = [];
			}
		}

		async function onOpen() {
			loading.value = true;
			tab.value = 'node';
			nodes.value = [];
			currentIndex.value = -1;
			try {
				await Promise.all([loadOptions(), loadServers()]);
				if (props.pipeline?.id) {
					const resp: any = await api.GetNodes(props.pipeline.id);
					const list = resp?.data?.data || resp?.data || [];
					nodes.value = list.map(toEditable);
					if (nodes.value.length) currentIndex.value = 0;
					const buildNode = nodes.value.find((n: any) => n.node_type === 'build' && n.config.jenkins_server_id);
					if (buildNode) loadJobs(buildNode.config.jenkins_server_id);
				}
				paramDefs.value = (props.pipeline?.params || []).map((p: any) => ({
					key: p.key || '', label: p.label || '', default: p.default || '', required: !!p.required,
				}));
			} finally {
				loading.value = false;
			}
		}

		function addNode() {
			nodes.value.push({
				_key: nextKey(), id: null, name: '', node_type: 'command',
				on_failure: 'stop', pos_x: 0, pos_y: 0, config: defaultsFor('command'),
			});
			currentIndex.value = nodes.value.length - 1;
			tab.value = 'node';
		}

		function removeNode(i: number) {
			nodes.value.splice(i, 1);
			if (currentIndex.value >= nodes.value.length) currentIndex.value = nodes.value.length - 1;
		}

		function move(i: number, delta: number) {
			const j = i + delta;
			if (j < 0 || j >= nodes.value.length) return;
			const arr = nodes.value;
			[arr[i], arr[j]] = [arr[j], arr[i]];
			currentIndex.value = j;
		}

		function onTypeChange(type: string) {
			if (!currentNode.value) return;
			currentNode.value.config = defaultsFor(type);
		}

		/** 保存前的前端体检：把明显漏填的挡在请求之前（后端也会再校验一遍） */
		function collectFrontendErrors(): string[] {
			const errs: string[] = [];
			if (!nodes.value.length) errs.push('至少要有一个节点');
			nodes.value.forEach((n: any, i: number) => {
				const label = `第 ${i + 1} 个节点「${n.name || '未命名'}」`;
				if (!String(n.name || '').trim()) errs.push(`${label}：没有填名称`);
				if (isCmdType(n.node_type) && !String(n.config?.command || '').trim()) {
					errs.push(`${label}：没有填写命令`);
				}
				if ((isCmdType(n.node_type) || n.node_type === 'upload') && !(n.config?.cmdb_targets || []).length) {
					errs.push(`${label}：没有选择目标服务器`);
				}
				if (n.node_type === 'upload') {
					if (!String(n.config?.local_path || '').trim()) errs.push(`${label}：没有填制品文件`);
					if (!String(n.config?.remote_path || '').trim()) errs.push(`${label}：没有填目标机路径`);
				}
				if (n.node_type === 'build') {
					if (!n.config?.jenkins_server_id) errs.push(`${label}：没有选 Jenkins 服务器`);
					if (!String(n.config?.job || '').trim()) errs.push(`${label}：没有选 Job`);
				}
				if (n.node_type === 'notify' && !n.config?.channel_id) errs.push(`${label}：没有选通知渠道`);
			});
			const keys: string[] = [];
			paramDefs.value.forEach((p: any) => {
				const k = String(p.key || '').trim();
				if (!k) return;
				if (!/^[A-Za-z0-9_]+$/.test(k)) errs.push(`参数名「${k}」只能含字母、数字、下划线`);
				if (keys.includes(k)) errs.push(`参数名「${k}」重复`);
				keys.push(k);
			});
			return errs;
		}

		async function save() {
			const errs = collectFrontendErrors();
			if (errs.length) {
				ElMessage.error(errs[0] + (errs.length > 1 ? `（共 ${errs.length} 处）` : ''));
				return;
			}
			saving.value = true;
			try {
				await api.UpdateObj({
					id: props.pipeline.id,
					name: props.pipeline.name,
					status: props.pipeline.status === 0 ? 0 : 1,
					credential: props.pipeline.credential || null,
					params: paramDefs.value
						.filter((p: any) => String(p.key || '').trim())
						.map((p: any) => ({
							key: String(p.key).trim(), label: p.label || '',
							default: p.default || '', required: !!p.required,
						})),
				});
				await api.SaveNodes(props.pipeline.id, nodes.value.map(toPayload));
				ElMessage.success('编排已保存');
				emit('saved');
			} finally {
				saving.value = false;
			}
		}

		async function preview() {
			if (!currentNode.value) return;
			try {
				const resp: any = await api.PreviewNode({
					pipeline: props.pipeline.id,
					node_type: currentNode.value.node_type,
					config: toPayload(currentNode.value).config,
					params: {},
				});
				previewResult.value = resp?.data?.data || resp?.data || {};
				previewVisible.value = true;
			} catch (e) { /* 拦截器已经提示过了 */ }
		}

		watch(() => props.pipeline, () => {
			if (props.modelValue) onOpen();
		});

		return {
			show, loading, saving, tab, nodes, currentIndex, currentNode, options, servers, jobs,
			paramDefs, previewVisible, previewResult, prettyRendered, notifyOnOptions,
			typeLabel, isCmdType, targetCount,
			onOpen, addNode, removeNode, move, onTypeChange, save, preview, loadJobs,
		};
	},
});
</script>

<style scoped>
.designer {
	display: flex;
	gap: 16px;
	height: 100%;
	min-height: 420px;
}
.pane-left {
	width: 380px;
	flex: none;
	border-right: 1px solid #ebeef5;
	padding-right: 14px;
	overflow: auto;
}
.pane-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 10px;
}
.pane-title {
	font-weight: 600;
	color: #303133;
}
.node-flow {
	min-height: 120px;
}
.node-card {
	display: flex;
	align-items: center;
	gap: 10px;
	border: 1px solid #dcdfe6;
	border-radius: 6px;
	padding: 8px 10px;
	background: #fff;
	cursor: pointer;
	transition: all 0.15s;
}
.node-card:hover {
	border-color: #a0cfff;
}
.node-card.active {
	border-color: #409eff;
	background: #ecf5ff;
	box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.12);
}
.node-seq {
	width: 22px;
	height: 22px;
	flex: none;
	border-radius: 50%;
	background: #409eff;
	color: #fff;
	font-size: 12px;
	line-height: 22px;
	text-align: center;
}
.node-body {
	flex: 1;
	min-width: 0;
}
.node-name {
	font-size: 13.5px;
	color: #303133;
	font-weight: 500;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.node-meta {
	display: flex;
	gap: 6px;
	align-items: center;
	margin-top: 4px;
	flex-wrap: wrap;
}
.tag-warn {
	color: #e6a23c;
	font-size: 12px;
}
.tag-dim {
	color: #909399;
	font-size: 12px;
}
.node-ops {
	flex: none;
}
.flow-arrow {
	text-align: center;
	color: #c0c4cc;
	font-size: 16px;
	line-height: 1.4;
}
.pane-tip {
	margin-top: 14px;
	color: #909399;
	font-size: 12px;
	line-height: 1.75;
}
.pane-right {
	flex: 1;
	overflow: auto;
	padding-right: 4px;
}
.hint {
	color: #909399;
	font-size: 12px;
	line-height: 1.7;
	margin-top: 4px;
}
.hint-inline {
	color: #909399;
	font-size: 12px;
	margin-left: 8px;
}
.mb12 {
	margin-bottom: 12px;
}
.mt8 {
	margin-top: 8px;
}
.kv-editor {
	width: 100%;
}
.kv-row {
	display: flex;
	gap: 8px;
	align-items: center;
	margin-bottom: 6px;
}
.param-row {
	display: flex;
	gap: 8px;
	align-items: center;
	margin-bottom: 8px;
}
.code-block {
	background: #1e1e1e;
	color: #d4d4d4;
	padding: 12px;
	border-radius: 4px;
	max-height: 320px;
	overflow: auto;
	font-size: 12.5px;
	line-height: 1.6;
	white-space: pre-wrap;
	word-break: break-all;
}
.footer-bar {
	display: flex;
	align-items: center;
	justify-content: space-between;
}
.footer-left {
	display: flex;
	align-items: center;
}
:deep(.el-drawer__body) {
	overflow: hidden;
}
:deep(.el-form-item) {
	margin-bottom: 14px;
}
</style>

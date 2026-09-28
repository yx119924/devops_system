<template>
	<fs-page>
		<div class="ai-chat">
			<!-- ==================== 左：我的会话 ==================== -->
			<aside class="chat-side">
				<div class="side-head">
					<span class="side-title">我的排查会话</span>
					<el-button type="primary" size="small" @click="newSession">新建</el-button>
				</div>
				<div class="side-tip">会话只对你自己可见；每条命令都用会话选定的凭据执行。</div>
				<el-scrollbar class="side-list" v-loading="sessionsLoading">
					<div
						v-for="s in sessions"
						:key="s.id"
						class="sess"
						:class="{ active: s.id === currentId }"
						@click="openSession(s.id)"
					>
						<div class="sess-title" :title="s.title">{{ s.title || '未命名会话' }}</div>
						<div class="sess-meta">
							<span>{{ s.rounds }} 轮 · {{ s.tool_count }} 次命令</span>
							<span class="sess-tokens">{{ s.total_tokens }} tok</span>
						</div>
						<div class="sess-foot">
							<span class="sess-time">{{ shortTime(s.update_datetime) }}</span>
							<el-button
								link
								type="danger"
								size="small"
								class="sess-del"
								@click.stop="removeSession(s)"
								>删除</el-button
							>
						</div>
					</div>
					<el-empty v-if="!sessionsLoading && !sessions.length" description="还没有会话" :image-size="56" />
				</el-scrollbar>
			</aside>

			<!-- ==================== 右：对话 ==================== -->
			<section class="chat-main">
				<!-- 顶部状态条 -->
				<header class="main-head">
					<div class="head-left">
						<span class="head-title">智能问答</span>
						<el-tag v-if="guard.readonly_mode && guard.enabled_tools" type="success" size="small" effect="plain">
							只读排查
						</el-tag>
						<el-tag v-else type="danger" size="small" effect="plain">命令执行已关闭</el-tag>
						<el-tooltip
							:content="`AI 可操作的服务器：${serverText}；单次最多 ${guard.max_servers} 台；单条命令超时 ${guard.command_timeout}s`"
							placement="bottom"
						>
							<span class="head-meta">可操作 {{ serverText }}</span>
						</el-tooltip>
						<el-tooltip
							:content="`脱敏${guard.desensitize ? '已开启' : '已关闭'}；单次对话最多 ${guard.max_rounds} 轮工具调用、${guard.chat_timeout} 秒`"
							placement="bottom"
						>
							<span class="head-meta">
								今日 {{ usage.rounds }}/{{ usage.round_limit }} 轮 · {{ usage.tokens }}/{{ usage.token_limit }} tok
							</span>
						</el-tooltip>
					</div>
					<div class="head-right">
						<template v-if="!currentId">
							<span class="head-new">新会话需要先选：</span>
							<el-select
								v-model="form.credentialId"
								placeholder="SSH 凭据（必选）"
								size="small"
								filterable
								style="width: 210px"
							>
								<el-option
									v-for="c in credentials"
									:key="c.id"
									:label="credOptionLabel(c)"
									:value="c.id"
								/>
							</el-select>
							<el-select
								v-model="form.providerId"
								placeholder="模型配置（默认）"
								size="small"
								clearable
								style="width: 190px"
							>
								<el-option v-for="p in providers" :key="p.id" :label="providerOptionLabel(p)" :value="p.id" />
							</el-select>
						</template>
						<template v-else>
							<el-tag size="small" effect="plain">凭据：{{ detail.credential_name || '-' }}</el-tag>
							<el-tag size="small" effect="plain">模型：{{ detail.provider_name || '-' }}</el-tag>
							<el-button link type="primary" size="small" @click="openLedger">命令台账</el-button>
						</template>
					</div>
				</header>

				<!-- 消息区 -->
				<el-scrollbar ref="scrollRef" class="msg-area">
					<div class="msg-inner">
						<div v-if="!items.length" class="msg-empty">
							<div class="me-title">问点什么，我来只读排查</div>
							<div class="me-tip">
								例如：「web-01 现在负载高吗，帮我看下哪几个进程占 CPU」<br />
								AI 会先查 CMDB 找到机器，再跑白名单内的只读命令（uptime / df / free / ss / ps / docker ps …），
								最后给出「现象 / 判断 / 建议」。<br />
								<span class="me-warn">
									它没有任何写权限：改配置、重启服务、删文件都必须由你人工执行。
								</span>
							</div>
							<div class="me-quick">
								<el-button
									v-for="q in quickQuestions"
									:key="q"
									size="small"
									plain
									@click="question = q"
									>{{ q }}</el-button
								>
							</div>
						</div>

						<div v-for="(m, i) in items" :key="i" class="msg" :class="'is-' + m.role">
							<!-- 用户 -->
							<template v-if="m.role === 'user'">
								<div class="avatar me">我</div>
								<div class="bubble user">
									<div class="bubble-text" v-text="m.text"></div>
								</div>
							</template>

							<!-- 系统收尾提示（后端在轮次用尽时追加的，不当成用户提问） -->
							<template v-else-if="m.role === 'hint'">
								<div class="avatar sys">系</div>
								<div class="bubble hint" v-text="m.text"></div>
							</template>

							<!-- AI -->
							<template v-else>
								<div class="avatar ai">AI</div>
								<div class="bubble ai">
									<!-- 工具调用卡片 -->
									<div v-for="c in m.calls || []" :key="c.key" class="tool-card" :class="'st-' + callStatus(c).type">
										<div class="tc-head" @click="toggleCall(c.key)">
											<span class="tc-caret">{{ expanded[c.key] ? '▾' : '▸' }}</span>
											<span class="tc-name">{{ c.name }}</span>
											<el-tag :type="callStatus(c).type" size="small" effect="plain">{{ callStatus(c).text }}</el-tag>
											<span class="tc-brief" v-text="callBrief(c)"></span>
											<span class="tc-round" v-if="c.args && c.args.purpose">目的：{{ c.args.purpose }}</span>
										</div>
										<div v-show="expanded[c.key]" class="tc-body">
											<div class="tc-line">
												<span class="tc-label">参数</span>
												<code class="tc-code" v-text="prettyArgs(c)"></code>
											</div>
											<template v-if="c.loading">
												<div class="tc-line muted">正在执行…</div>
											</template>
											<template v-else-if="c.result && c.result.error">
												<div class="tc-line err">被拒绝 / 失败：{{ c.result.error }}</div>
											</template>
											<template v-else-if="c.result">
												<!-- run_readonly_command -->
												<template v-if="c.result.targets && c.result.targets.length">
													<div
														v-for="t in c.result.targets"
														:key="t.server_id + '-' + t.ip"
														class="tc-target"
													>
														<div class="tt-head">
															<span class="tt-host">{{ t.server || ('server_id=' + t.server_id) }}</span>
															<span class="tt-ip">{{ t.ip }}</span>
															<el-tag :type="targetTagType(t.status)" size="small" effect="plain">{{ t.status }}</el-tag>
															<span v-if="t.exit_code !== null && t.exit_code !== undefined" class="tt-meta">
																exit={{ t.exit_code }}
															</span>
															<span v-if="t.duration" class="tt-meta">{{ t.duration }}s</span>
														</div>
														<div v-if="t.error" class="tt-err">{{ t.error }}</div>
														<pre v-if="t.stdout" class="tt-out" v-text="t.stdout"></pre>
														<pre v-if="t.stderr" class="tt-out stderr" v-text="t.stderr"></pre>
													</div>
												</template>
												<!-- list_servers -->
												<template v-else-if="c.result.servers">
													<div class="tc-line muted">
														匹配 {{ c.result.total_matched }} 台，返回 {{ c.result.returned }} 台
													</div>
													<div v-if="c.result.hint" class="tc-line warn" v-text="c.result.hint"></div>
													<div v-for="s in c.result.servers" :key="s.server_id" class="tc-srv">
														<span class="srv-id">#{{ s.server_id }}</span>
														<span class="srv-host">{{ s.hostname }}</span>
														<span class="srv-ip">{{ s.ip }}</span>
														<span class="srv-env">{{ s.environment }} / {{ s.idc }}</span>
														<span class="srv-st">{{ s.status }}</span>
													</div>
												</template>
												<div v-else-if="c.raw" class="tc-line muted">{{ c.raw }}</div>
											</template>
										</div>
									</div>

									<!-- 正文 -->
									<div v-if="m.text" class="bubble-text ai-text" v-text="m.text"></div>
									<div v-else-if="(m.calls || []).length" class="tc-pending">正在排查…</div>
								</div>
							</template>
						</div>

						<!-- 等待回复 -->
						<div v-if="sending" class="msg is-assistant">
							<div class="avatar ai">AI</div>
							<div class="bubble ai">
								<div class="typing">
									正在排查（最多 {{ guard.max_rounds }} 轮工具调用 / {{ guard.chat_timeout }} 秒，请稍等）
								</div>
							</div>
						</div>
					</div>
				</el-scrollbar>

				<!-- 输入区 -->
				<footer class="input-area">
					<el-input
						v-model="question"
						type="textarea"
						:rows="3"
						resize="none"
						maxlength="4000"
						show-word-limit
						placeholder="描述现象，例如：web-01 的 / 分区快满了，帮我看下哪个目录占空间（Enter 发送，Shift+Enter 换行）"
						@keydown="onKeydown"
					/>
					<div class="input-foot">
						<span class="input-hint">
							只读命令；输出外发前会脱敏；本次对话的命令都会进审计台账。
						</span>
						<div class="input-btns">
							<el-button :disabled="sending" @click="question = ''">清空</el-button>
							<el-button type="primary" :loading="sending" :disabled="!canSend" @click="send">
								{{ sending ? '排查中…' : '发送' }}
							</el-button>
						</div>
					</div>
				</footer>
			</section>
		</div>

		<!-- ==================== 命令台账抽屉 ==================== -->
		<el-drawer v-model="ledgerVisible" title="本次会话的命令台账" size="60%" @open="loadLedger">
			<div class="ledger-tip">
				包含**被护栏拒绝、无授权**的尝试 —— 审计关心的是「AI 想干什么、被什么拦住」。
			</div>
			<el-table :data="ledger" size="small" v-loading="ledgerLoading" height="72vh">
				<el-table-column prop="round_index" label="轮" width="50" />
				<el-table-column prop="tool_name" label="工具" width="150" show-overflow-tooltip />
				<el-table-column label="目标" width="170">
					<template #default="{ row }">
						<div>{{ row.server_label || '-' }}</div>
						<div class="ledger-sub">{{ row.ip }}</div>
					</template>
				</el-table-column>
				<el-table-column label="命令 / 参数" min-width="220">
					<template #default="{ row }">
						<div class="ledger-cmd">{{ row.command || '-' }}</div>
						<div class="ledger-sub">{{ row.purpose }}</div>
					</template>
				</el-table-column>
				<el-table-column label="结果" width="110">
					<template #default="{ row }">
						<el-tag :type="recordTagType(row.status)" size="small" effect="plain">{{ row.status }}</el-tag>
					</template>
				</el-table-column>
				<el-table-column label="说明 / 输出" min-width="240">
					<template #default="{ row }">
						<div v-if="row.reject_reason" class="ledger-err">{{ row.reject_reason }}</div>
						<div v-if="row.desensitized" class="ledger-sub">脱敏：{{ row.desensitized }}</div>
						<pre v-if="row.stdout_excerpt" class="ledger-out" v-text="row.stdout_excerpt"></pre>
					</template>
				</el-table-column>
				<el-table-column prop="create_datetime" label="时间" width="160" />
			</el-table>
		</el-drawer>
	</fs-page>
</template>

<script lang="ts">
import { computed, defineComponent, nextTick, onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
	GetOptions,
	GetSession,
	GetSessions,
	GetSessionToolCalls,
	SendMessage,
	DelSession,
} from './api';
import type {
	ChatCredential,
	ChatGuardState,
	ChatItem,
	ChatProviderOption,
	ChatSessionBrief,
	ChatSessionDetail,
	ChatMessage,
	ChatUsage,
	ToolCallCard,
	ToolCallRecord,
	ToolResult,
} from './type';

/** 后端在轮次/时长用尽时追加的收尾提示的前缀（agent.CONVERGE_HINT） */
const HINT_PREFIX = '（系统提示：';

/** 空态里的示例问题 —— 都是只读能查出来的，别给用户"改配置"这类做不到的暗示 */
const QUICK_QUESTIONS = [
	'服务器现在负载高吗，哪几个进程占 CPU',
	'根分区还剩多少空间，哪个目录占用最大',
	'内存和 swap 使用情况怎么样，有没有被 OOM',
	'docker 容器有没有异常退出的',
];

export default defineComponent({
	name: 'aiChat',
	setup() {
		// ---------------------------------------------------------- 基础状态
		const sessions = ref<ChatSessionBrief[]>([]);
		const sessionsLoading = ref(false);
		const currentId = ref<number | null>(null);
		const detail = ref<Partial<ChatSessionDetail>>({});
		const items = ref<ChatItem[]>([]);
		const question = ref('');
		const sending = ref(false);
		const scrollRef = ref();

		const credentials = ref<ChatCredential[]>([]);
		const providers = ref<ChatProviderOption[]>([]);
		const serverCount = ref<number | string>(0);
		const usage = ref<ChatUsage>({
			day: '',
			rounds: 0,
			round_limit: 0,
			tokens: 0,
			token_limit: 0,
			requests: 0,
		});
		const guard = ref<ChatGuardState>({
			readonly_mode: true,
			enabled_tools: true,
			desensitize: true,
			max_rounds: 12,
			chat_timeout: 90,
			command_timeout: 30,
			max_servers: 5,
			allowed_sample: [],
		});

		// 新建会话时的选择（续问时沿用会话里已绑定的，不再让改）
		const form = reactive<{ credentialId: number | null; providerId: number | null }>({
			credentialId: null,
			providerId: null,
		});

		// 工具卡片的展开态（key → 是否展开）
		const expanded = reactive<Record<string, boolean>>({});

		const ledgerVisible = ref(false);
		const ledgerLoading = ref(false);
		const ledger = ref<ToolCallRecord[]>([]);

		// ---------------------------------------------------------- 计算属性
		const serverText = computed(() =>
			serverCount.value === 'all' ? '不限（管理员）' : `${serverCount.value} 台`
		);

		const canSend = computed(() => {
			if (sending.value || !question.value.trim()) return false;
			// 新会话必须先选凭据，否则后端必然报错 —— 提前拦住，少一次无效请求
			if (!currentId.value && !form.credentialId) return false;
			return true;
		});

		// ---------------------------------------------------------- 展示辅助
		const shortTime = (v: string) => {
			if (!v) return '';
			return String(v).replace('T', ' ').slice(5, 16);
		};

		const credOptionLabel = (c: ChatCredential) =>
			`${c.name}（${c.username || 'root'}）${c.server ? '' : ' · 通用'}`;

		const providerOptionLabel = (p: ChatProviderOption) =>
			`${p.name}｜${p.model}${p.is_default ? ' · 默认' : ''}`;

		const targetTagType = (st: string) => {
			if (st === 'success') return 'success';
			if (st === 'empty') return 'info';
			if (st === 'blocked' || st === 'rejected') return 'warning';
			return 'danger';
		};

		const recordTagType = (st: string) => {
			if (st === 'success') return 'success';
			if (st === 'empty') return 'info';
			if (st === 'blocked' || st === 'rejected') return 'warning';
			return 'danger';
		};

		/** 工具卡片的整体状态：执行中 / 失败 / 被拦 / 完成 */
		const callStatus = (c: ToolCallCard) => {
			if (c.loading) return { type: 'info', text: '执行中' };
			const r = c.result;
			if (r && r.error) {
				const blocked = /拒绝|无权限|授权|已关闭|白名单|黑名单|敏感路径/.test(r.error);
				return { type: blocked ? 'warning' : 'danger', text: blocked ? '已拦截' : '失败' };
			}
			if (!r) return { type: 'info', text: '无输出' };
			const s = r.summary;
			if (s && s.total && s.success !== s.total) {
				return { type: 'warning', text: `部分失败 ${s.success}/${s.total}` };
			}
			if (r.servers) return { type: 'success', text: `返回 ${r.returned} 台` };
			return { type: 'success', text: '完成' };
		};

		/** 卡片摘要：一行话说明这条命令干了什么 */
		const callBrief = (c: ToolCallCard) => {
			if (c.name === 'list_servers') {
				const kw = c.args && c.args.keyword;
				return kw ? `查资产：${kw}` : '查资产清单';
			}
			const cmd = c.args && c.args.command;
			const ids = c.args && c.args.server_ids;
			const n = Array.isArray(ids) ? ids.length : 0;
			return cmd ? `${cmd}${n ? `　→ ${n} 台` : ''}` : '';
		};

		const prettyArgs = (c: ToolCallCard) => {
			try {
				return JSON.stringify(c.args || {}, null, 0);
			} catch (e) {
				return String(c.args);
			}
		};

		const toggleCall = (key: string) => {
			expanded[key] = !expanded[key];
		};

		const safeParse = (txt: any) => {
			if (!txt) return null;
			if (typeof txt === 'object') return txt;
			try {
				return JSON.parse(txt);
			} catch (e) {
				return null;
			}
		};

		/**
		 * 把 OpenAI 协议的原始消息压成页面能渲染的项。
		 *
		 * ★ 关键：`tool` 消息靠 `tool_call_id` 回填到对应卡片的 `result`，
		 *   所以 assistant 的 tool_calls 必须先落地成卡片。
		 *   只解析 `JSON.parse` 失败就原样放进 `raw` —— 绝不丢内容，
		 *   否则模型看到的东西和用户看到的对不上，排查会跑偏。
		 */
		const buildItems = (messages: ChatMessage[]): ChatItem[] => {
			const out: ChatItem[] = [];
			const pending: Record<string, ToolCallCard> = {};
			(messages || []).forEach((m, mi) => {
				const role = m && m.role;
				if (role === 'system') return;
				if (role === 'user') {
					const text = m.content || '';
					out.push({
						role: text.startsWith(HINT_PREFIX) ? 'hint' : 'user',
						text,
					});
					return;
				}
				if (role === 'assistant') {
					const calls: ToolCallCard[] = (m.tool_calls || []).map((c, ci) => {
						const card: ToolCallCard = {
							key: `r${mi}c${ci}`,
							id: c.id || '',
							name: (c.function && c.function.name) || '',
							args: safeParse(c.function && c.function.arguments) || {},
							loading: true,
							result: null,
						};
						if (card.id) pending[card.id] = card;
						return card;
					});
					out.push({ role: 'assistant', text: m.content || '', calls });
					return;
				}
				if (role === 'tool') {
					const card = pending[m.tool_call_id || ''];
					if (!card) return;
					card.loading = false;
					const parsed = safeParse(m.content);
					if (parsed) card.result = parsed as ToolResult;
					else card.raw = m.content || '';
				}
			});
			return out;
		};

		const scrollToBottom = () => {
			nextTick(() => {
				try {
					scrollRef.value?.setScrollTop(1e7);
				} catch (e) {
					/* 滚动失败不影响功能 */
				}
			});
		};

		// ---------------------------------------------------------- 数据加载
		const loadOptions = async () => {
			try {
				const res: any = await GetOptions();
				if (res.code !== 2000) {
					ElMessage.error(res.msg || '获取配置失败');
					return;
				}
				const d = res.data || {};
				credentials.value = d.credentials || [];
				providers.value = d.providers || [];
				serverCount.value = d.server_count === undefined ? 0 : d.server_count;
				usage.value = d.usage || usage.value;
				guard.value = Object.assign({}, guard.value, d.guard || {});
				// 只剩一条凭据时直接选中，省掉一次无意义的选择
				if (!form.credentialId && credentials.value.length === 1) {
					form.credentialId = credentials.value[0].id;
				}
				// 默认模型配置优先选中
				if (!form.providerId && providers.value.length) {
					const def = providers.value.find((p) => p.is_default) || providers.value[0];
					form.providerId = def.id;
				}
			} catch (e: any) {
				ElMessage.error(e?.message || '获取配置失败');
			}
		};

		const loadSessions = async () => {
			sessionsLoading.value = true;
			try {
				const res: any = await GetSessions({ page: 1, limit: 100 });
				if (res.code !== 2000) {
					ElMessage.error(res.msg || '获取会话列表失败');
					return;
				}
				sessions.value = Array.isArray(res.data) ? res.data : [];
			} catch (e: any) {
				ElMessage.error(e?.message || '获取会话列表失败');
			} finally {
				sessionsLoading.value = false;
			}
		};

		const refreshUsage = async () => {
			try {
				const res: any = await GetOptions();
				if (res.code === 2000 && res.data) {
					usage.value = res.data.usage || usage.value;
				}
			} catch (e) {
				/* 配额显示刷新失败不打扰用户 */
			}
		};

		/**
		 * 拉取会话详情并重建消息列表。
		 *
		 * ★ 刻意**不带任何守卫**（既不判 sending、也不判"是不是同一个 id"）：
		 *   发送完成后必须无条件重建一次，否则页面上只剩乐观回显的那条提问，
		 *   AI 的回答不会出现。用户点击左侧列表才需要守卫 → 见 openSession。
		 */
		const loadSessionDetail = async (id: number) => {
			const res: any = await GetSession(id);
			if (res.code !== 2000) {
				ElMessage.error(res.msg || '打开会话失败');
				return false;
			}
			currentId.value = id;
			detail.value = res.data || {};
			const built = buildItems((res.data && res.data.messages) || []);
			items.value = built;
			// 历史里已经出结果的卡片默认折叠，把屏幕留给正文
			built.forEach((it) => {
				(it.calls || []).forEach((c) => {
					if (expanded[c.key] === undefined) expanded[c.key] = false;
				});
			});
			scrollToBottom();
			return true;
		};

		/** 用户点击左侧列表切换会话（切换期间不允许并发发送） */
		const openSession = async (id: number) => {
			if (sending.value) {
				ElMessage.warning('正在排查中，等这一次结束再切换会话');
				return;
			}
			if (currentId.value === id) return;
			try {
				await loadSessionDetail(id);
			} catch (e: any) {
				ElMessage.error(e?.message || '打开会话失败');
			}
		};

		const newSession = () => {
			if (sending.value) {
				ElMessage.warning('正在排查中，等这一次结束再新建');
				return;
			}
			currentId.value = null;
			detail.value = {};
			items.value = [];
			question.value = '';
		};

		const removeSession = (s: ChatSessionBrief) => {
			ElMessageBox.confirm(
				`确定删除会话「${s.title || '未命名会话'}」？会话里的提问与命令输出会一起清掉。`,
				'删除会话',
				{ type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
			)
				.then(async () => {
					const res: any = await DelSession(s.id);
					if (res.code !== 2000) {
						ElMessage.error(res.msg || '删除失败');
						return;
					}
					ElMessage.success('已删除');
					if (currentId.value === s.id) newSession();
					loadSessions();
				})
				.catch(() => {
					/* 取消 */
				});
		};

		// ---------------------------------------------------------- 提问
		const send = async () => {
			const text = question.value.trim();
			if (!text) {
				ElMessage.warning('先说一下要排查什么');
				return;
			}
			if (!currentId.value && !form.credentialId) {
				ElMessage.warning('新会话要先选一条 SSH 凭据');
				return;
			}
			if (!providers.value.length) {
				ElMessage.warning('你还没有可用的模型配置，请先到「AI 运维助手 → 模型配置」新建一条');
				return;
			}

			// 乐观回显：先把提问画上去，用户不至于对着空屏等
			items.value.push({ role: 'user', text });
			question.value = '';
			sending.value = true;
			scrollToBottom();

			try {
				const res: any = await SendMessage({
					message: text,
					session_id: currentId.value,
					credential_id: form.credentialId,
					provider_id: form.providerId,
				});
				if (res.code !== 2000) {
					ElMessage.error(res.msg || '排查失败');
					return;
				}
				const data = res.data || {};
				if (data.desensitized) {
					ElMessage.info('你输入里的敏感值已被自动打码后再外发');
				}
				if (data.stop_reason === 'max_rounds' || data.stop_reason === 'timeout') {
					ElMessage.warning('已达单次排查上限，上面是基于已有输出的当前结论；可以把问题拆小再问一次');
				} else {
					ElMessage.success(res.msg || '已完成排查');
				}
				// ★ 统一从后端重取会话详情重建展示：
				//   避免"本地拼出来的消息"与"库里存的消息"两套口径逐渐跑偏。
				//   ★ 必须走 loadSessionDetail 而不是 openSession —— 此刻
				//     sending 仍为 true，openSession 的两道守卫会把刷新整个吞掉。
				if (data.session_id) {
					const isFirst = !currentId.value;
					await loadSessionDetail(data.session_id);
					if (isFirst) loadSessions();
				}
				if (data.usage) usage.value = data.usage;
			} catch (e: any) {
				// 业务错误已被 service.ts 拦截器转成 { code, msg }
				ElMessage.error(e?.msg || e?.message || '排查失败，请稍后重试');
			} finally {
				sending.value = false;
				refreshUsage();
			}
		};

		/**
		 * Enter 发送 / Shift+Enter 换行。
		 * ★ 必须判 `isComposing`：中文输入法选字时按 Enter 会带着 229 的 keyCode，
		 *   不判的话「打一半字就被发出去」是必然事件。
		 */
		const onKeydown = (e: KeyboardEvent) => {
			if (e.key !== 'Enter' || e.shiftKey) return;
			if (e.isComposing || (e as any).keyCode === 229) return;
			e.preventDefault();
			if (canSend.value) send();
		};

		// ---------------------------------------------------------- 台账
		const openLedger = () => {
			ledgerVisible.value = true;
		};

		const loadLedger = async () => {
			if (!currentId.value) return;
			ledgerLoading.value = true;
			try {
				const res: any = await GetSessionToolCalls(currentId.value);
				if (res.code !== 2000) {
					ElMessage.error(res.msg || '获取台账失败');
					return;
				}
				ledger.value = Array.isArray(res.data) ? res.data : [];
			} catch (e: any) {
				ElMessage.error(e?.message || '获取台账失败');
			} finally {
				ledgerLoading.value = false;
			}
		};

		onMounted(async () => {
			await loadOptions();
			await loadSessions();
		});

		return {
			// 状态
			sessions,
			sessionsLoading,
			currentId,
			detail,
			items,
			question,
			sending,
			scrollRef,
			credentials,
			providers,
			serverCount,
			usage,
			guard,
			form,
			expanded,
			ledgerVisible,
			ledgerLoading,
			ledger,
			// 计算
			serverText,
			canSend,
			quickQuestions: QUICK_QUESTIONS,
			// 方法
			shortTime,
			credOptionLabel,
			providerOptionLabel,
			targetTagType,
			recordTagType,
			callStatus,
			callBrief,
			prettyArgs,
			toggleCall,
			newSession,
			openSession,
			removeSession,
			send,
			onKeydown,
			openLedger,
			loadLedger,
		};
	},
});
</script>

<style scoped>
.ai-chat {
	display: flex;
	gap: 12px;
	height: calc(100vh - 150px);
	min-height: 520px;
}

/* ---------------- 左侧会话列表 ---------------- */
.chat-side {
	width: 246px;
	flex: none;
	display: flex;
	flex-direction: column;
	background: #fff;
	border: 1px solid #ebeef5;
	border-radius: 10px;
	padding: 10px;
	box-sizing: border-box;
}
.side-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
}
.side-title {
	font-size: 14px;
	font-weight: 600;
	color: #303133;
}
.side-tip {
	margin: 8px 0 6px;
	font-size: 12px;
	color: #909399;
	line-height: 1.6;
}
.side-list {
	flex: 1;
	overflow: hidden;
}
.sess {
	padding: 8px 10px;
	border-radius: 8px;
	cursor: pointer;
	border: 1px solid transparent;
	margin-bottom: 6px;
	transition: background 0.15s;
}
.sess:hover {
	background: #f5f7fa;
}
.sess.active {
	background: #ecf5ff;
	border-color: #b3d8ff;
}
.sess-title {
	font-size: 13px;
	color: #303133;
	font-weight: 500;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.sess-meta {
	margin-top: 3px;
	font-size: 12px;
	color: #909399;
	display: flex;
	justify-content: space-between;
}
.sess-foot {
	margin-top: 2px;
	display: flex;
	align-items: center;
	justify-content: space-between;
}
.sess-time {
	font-size: 12px;
	color: #c0c4cc;
}
.sess-del {
	padding: 0;
	height: auto;
	opacity: 0;
	transition: opacity 0.15s;
}
.sess:hover .sess-del {
	opacity: 1;
}

/* ---------------- 右侧对话区 ---------------- */
.chat-main {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
	background: #fff;
	border: 1px solid #ebeef5;
	border-radius: 10px;
	box-sizing: border-box;
	overflow: hidden;
}
.main-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 10px;
	flex-wrap: wrap;
	padding: 10px 14px;
	border-bottom: 1px solid #f0f2f5;
	background: #fcfcfd;
}
.head-left,
.head-right {
	display: flex;
	align-items: center;
	gap: 8px;
}
.head-title {
	font-size: 15px;
	font-weight: 600;
	color: #303133;
}
.head-meta {
	font-size: 12px;
	color: #909399;
	cursor: default;
}
.head-new {
	font-size: 12px;
	color: #e6a23c;
}

/* 消息区 */
.msg-area {
	flex: 1;
	overflow: hidden;
	background: #f7f8fa;
}
.msg-inner {
	padding: 14px 16px 6px;
}
.msg-empty {
	padding: 26px 8px;
	text-align: center;
}
.me-title {
	font-size: 15px;
	font-weight: 600;
	color: #303133;
}
.me-tip {
	margin: 10px auto 14px;
	max-width: 640px;
	font-size: 13px;
	color: #606266;
	line-height: 1.9;
	text-align: left;
	background: #fff;
	border: 1px solid #ebeef5;
	border-radius: 8px;
	padding: 12px 16px;
}
.me-warn {
	color: #e6a23c;
}
.me-quick {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	justify-content: center;
}

.msg {
	display: flex;
	gap: 10px;
	margin-bottom: 14px;
}
.msg.is-user {
	flex-direction: row-reverse;
}
.avatar {
	width: 30px;
	height: 30px;
	flex: none;
	border-radius: 6px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 12px;
	color: #fff;
}
.avatar.me {
	background: #409eff;
}
.avatar.ai {
	background: #67c23a;
}
.avatar.sys {
	background: #c0c4cc;
}
.bubble {
	max-width: 82%;
	min-width: 0;
}
.bubble.user {
	background: #409eff;
	color: #fff;
	border-radius: 8px 2px 8px 8px;
	padding: 8px 12px;
}
.bubble.ai {
	background: #fff;
	border: 1px solid #ebeef5;
	border-radius: 2px 8px 8px 8px;
	padding: 10px 12px;
	flex: 1;
}
.bubble.hint {
	background: #fdf6ec;
	border: 1px solid #f5dab1;
	color: #b88230;
	border-radius: 6px;
	padding: 6px 10px;
	font-size: 12px;
	line-height: 1.7;
}
.bubble-text {
	font-size: 13.5px;
	line-height: 1.85;
	white-space: pre-wrap;
	word-break: break-word;
}
.ai-text {
	color: #303133;
}
.tc-pending,
.typing {
	font-size: 13px;
	color: #909399;
}
.typing::after {
	content: '...';
	animation: blink 1.2s steps(4, end) infinite;
}
@keyframes blink {
	0% {
		opacity: 0.3;
	}
	50% {
		opacity: 1;
	}
	100% {
		opacity: 0.3;
	}
}

/* 工具卡片 */
.tool-card {
	border: 1px solid #e4e7ed;
	border-radius: 8px;
	margin-bottom: 10px;
	overflow: hidden;
	background: #fafcff;
}
.tool-card.st-warning {
	border-color: #f5dab1;
	background: #fdf9f3;
}
.tool-card.st-danger {
	border-color: #fbc4c4;
	background: #fef7f7;
}
.tc-head {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 6px 10px;
	cursor: pointer;
	flex-wrap: wrap;
	font-size: 12.5px;
}
.tc-head:hover {
	background: rgba(64, 158, 255, 0.06);
}
.tc-caret {
	color: #909399;
	width: 10px;
}
.tc-name {
	font-family: Consolas, Monaco, 'Courier New', monospace;
	font-weight: 600;
	color: #303133;
}
.tc-brief {
	font-family: Consolas, Monaco, 'Courier New', monospace;
	color: #606266;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	max-width: 340px;
}
.tc-round {
	color: #909399;
	font-size: 12px;
}
.tc-body {
	padding: 8px 10px 10px;
	border-top: 1px dashed #e4e7ed;
	background: #fff;
}
.tc-line {
	font-size: 12.5px;
	line-height: 1.8;
	color: #606266;
	word-break: break-all;
}
.tc-line.muted {
	color: #909399;
}
.tc-line.err {
	color: #f56c6c;
}
.tc-line.warn {
	color: #e6a23c;
}
.tc-label {
	display: inline-block;
	min-width: 32px;
	color: #909399;
	margin-right: 6px;
}
.tc-code {
	font-family: Consolas, Monaco, 'Courier New', monospace;
	font-size: 12px;
	color: #303133;
	background: #f5f7fa;
	border-radius: 4px;
	padding: 1px 5px;
}
.tc-target {
	margin-top: 8px;
	border-left: 3px solid #dcdfe6;
	padding-left: 8px;
}
.tt-head {
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: wrap;
	font-size: 12.5px;
}
.tt-host {
	font-weight: 600;
	color: #303133;
}
.tt-ip {
	font-family: Consolas, Monaco, 'Courier New', monospace;
	color: #606266;
}
.tt-meta {
	color: #909399;
	font-size: 12px;
}
.tt-err {
	margin-top: 4px;
	font-size: 12.5px;
	color: #f56c6c;
}
.tt-out {
	margin: 6px 0 0;
	padding: 8px;
	max-height: 260px;
	overflow: auto;
	background: #f5f7fa;
	border-radius: 6px;
	font-family: Consolas, Monaco, 'Courier New', monospace;
	font-size: 12px;
	line-height: 1.6;
	color: #303133;
	white-space: pre-wrap;
	word-break: break-all;
}
.tt-out.stderr {
	background: #fef0f0;
	color: #c45656;
}
.tc-srv {
	display: flex;
	align-items: center;
	gap: 8px;
	font-size: 12.5px;
	padding: 3px 0;
	border-bottom: 1px dashed #f0f2f5;
	flex-wrap: wrap;
}
.srv-id {
	color: #c0c4cc;
	font-family: Consolas, Monaco, 'Courier New', monospace;
}
.srv-host {
	font-weight: 600;
	color: #303133;
}
.srv-ip,
.srv-env,
.srv-st {
	color: #606266;
	font-family: Consolas, Monaco, 'Courier New', monospace;
}
.srv-env,
.srv-st {
	color: #909399;
}

/* 输入区 */
.input-area {
	border-top: 1px solid #f0f2f5;
	padding: 10px 14px 12px;
	background: #fff;
}
.input-foot {
	margin-top: 8px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 10px;
	flex-wrap: wrap;
}
.input-hint {
	font-size: 12px;
	color: #909399;
}
.input-btns {
	display: flex;
	gap: 8px;
}

/* 台账抽屉 */
.ledger-tip {
	font-size: 12px;
	color: #606266;
	background: #f5f7fa;
	border-radius: 6px;
	padding: 8px 12px;
	margin-bottom: 10px;
	line-height: 1.7;
}
.ledger-sub {
	font-size: 12px;
	color: #909399;
}
.ledger-cmd {
	font-family: Consolas, Monaco, 'Courier New', monospace;
	font-size: 12.5px;
	color: #303133;
	word-break: break-all;
}
.ledger-err {
	font-size: 12px;
	color: #f56c6c;
	line-height: 1.6;
}
.ledger-out {
	margin: 4px 0 0;
	max-height: 120px;
	overflow: auto;
	font-family: Consolas, Monaco, 'Courier New', monospace;
	font-size: 11.5px;
	color: #606266;
	white-space: pre-wrap;
	word-break: break-all;
}
</style>

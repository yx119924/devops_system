<template>
	<div class="alert-manage">
		<el-tabs v-model="activeTab" class="manage-tabs">
			<!-- ===== Tab 1: 活跃告警 ===== -->
			<el-tab-pane name="alerts">
				<template #label>
					<span class="tab-label">
						活跃告警
						<el-badge v-if="alerts.length" :value="alerts.length" class="tab-badge" />
					</span>
				</template>
				<div class="tab-toolbar">
					<div class="toolbar-left">
						<el-radio-group v-model="stateFilter" size="small" @change="loadAlerts">
							<el-radio-button label="">全部</el-radio-button>
							<el-radio-button label="active">告警中</el-radio-button>
							<el-radio-button label="suppressed">已静默</el-radio-button>
						</el-radio-group>
					</div>
					<div class="toolbar-right">
						<el-button :icon="Refresh" :loading="alertsLoading" @click="loadAlerts">刷新</el-button>
					</div>
				</div>
				<el-table :data="filteredAlerts" v-loading="alertsLoading" border stripe empty-text="暂无活跃告警" class="manage-table">
					<el-table-column type="index" label="#" width="55" align="center" />
					<el-table-column label="级别" width="90" align="center">
						<template #default="{ row }">
							<el-tag :type="severityType(row.severity)" size="small" effect="dark">{{ severityText(row.severity) }}</el-tag>
						</template>
					</el-table-column>
					<el-table-column prop="alertname" label="告警名称" min-width="160" show-overflow-tooltip />
					<el-table-column label="状态" width="100" align="center">
						<template #default="{ row }">
							<el-tag v-if="row.silenced" type="info" size="small">已静默</el-tag>
							<el-tag v-else-if="row.inhibited" type="warning" size="small">已抑制</el-tag>
							<el-tag v-else type="danger" size="small">告警中</el-tag>
						</template>
					</el-table-column>
					<el-table-column prop="instance" label="实例" min-width="140" show-overflow-tooltip />
					<el-table-column prop="summary" label="摘要" min-width="180" show-overflow-tooltip />
					<el-table-column label="开始时间" width="170">
						<template #default="{ row }">{{ fmtTime(row.startsAt) }}</template>
					</el-table-column>
					<el-table-column label="操作" width="140" align="center" fixed="right">
						<template #default="{ row }">
							<el-button link type="primary" :icon="Bell" @click="openSilence(row)">静默</el-button>
							<el-button link type="info" @click="showDetail(row)">详情</el-button>
						</template>
					</el-table-column>
				</el-table>
			</el-tab-pane>

			<!-- ===== Tab 2: 静默管理 ===== -->
			<el-tab-pane name="silences">
				<template #label>
					<span class="tab-label">
						静默管理
						<el-badge v-if="activeSilenceCount" :value="activeSilenceCount" class="tab-badge" />
					</span>
				</template>
				<div class="tab-toolbar">
					<div class="toolbar-left">
						<span class="toolbar-tip">静默用于临时屏蔽告警通知，到期自动恢复</span>
						<el-checkbox v-model="hideExpired" class="toolbar-check">隐藏已过期</el-checkbox>
						<span v-if="hideExpired && expiredCount" class="toolbar-hint">
							已隐藏 {{ expiredCount }} 条已过期记录（Alertmanager 会保留失效静默，其保留期结束后自动清理）
						</span>
					</div>
					<div class="toolbar-right">
						<el-button type="primary" :icon="Plus" @click="openSilence(null)">新建静默</el-button>
						<el-button :icon="Refresh" :loading="silencesLoading" @click="loadSilences">刷新</el-button>
					</div>
				</div>
				<el-table :data="visibleSilences" v-loading="silencesLoading" border stripe empty-text="暂无静默规则" class="manage-table">
					<el-table-column type="index" label="#" width="55" align="center" />
					<el-table-column label="匹配标签" min-width="220">
						<template #default="{ row }">
							<el-tag v-for="m in row.matchers" :key="m.name + m.value" size="small" class="matcher-tag">
								{{ m.name }}{{ m.isRegex ? '=~' : '=' }}{{ m.value }}
							</el-tag>
						</template>
					</el-table-column>
					<el-table-column label="状态" width="90" align="center">
						<template #default="{ row }">
							<el-tag :type="silenceStateType(row)" size="small">{{ silenceStateText(row) }}</el-tag>
						</template>
					</el-table-column>
					<el-table-column prop="comment" label="备注" min-width="160" show-overflow-tooltip />
					<el-table-column prop="createdBy" label="创建人" width="100" align="center" />
					<el-table-column label="到期时间" width="170">
						<template #default="{ row }">{{ fmtTime(row.endsAt) }}</template>
					</el-table-column>
					<el-table-column label="操作" width="110" align="center" fixed="right">
						<template #default="{ row }">
							<!-- 已失效的记录 Alertmanager 只能靠自身回收，接口 DELETE 是幂等空操作 → 不提供按钮，避免「点了没反应」 -->
							<el-button v-if="silenceActive(row)" link type="danger" @click="doDeleteSilence(row)">删除</el-button>
							<el-tooltip v-else content="已失效的静默不再拦截告警；Alertmanager 会在保留期结束后自行清理，无法手动删除" placement="left">
								<span class="op-muted">已失效</span>
							</el-tooltip>
						</template>
					</el-table-column>
				</el-table>
			</el-tab-pane>

			<!-- ===== Tab 3: 路由收敛 ===== -->
			<el-tab-pane name="route">
				<template #label><span class="tab-label">路由收敛</span></template>
				<div class="tab-toolbar">
					<div class="toolbar-left">
						<span class="toolbar-tip">告警经 Alertmanager 按标签分组收敛后，再分发到接收器</span>
					</div>
					<div class="toolbar-right">
						<el-button :icon="Refresh" :loading="routeLoading" @click="loadRoute">刷新</el-button>
					</div>
				</div>
				<el-row :gutter="16" v-loading="routeLoading">
					<el-col :xs="24" :sm="12">
						<div class="route-card">
							<div class="route-card-title">默认路由（route）</div>
							<el-descriptions :column="1" border size="small">
								<el-descriptions-item label="接收器 receiver">{{ route.receiver || '-' }}</el-descriptions-item>
								<el-descriptions-item label="分组标签 group_by">
									<el-tag v-for="g in route.group_by" :key="g" size="small" class="matcher-tag">{{ g }}</el-tag>
									<span v-if="!route.group_by?.length">-</span>
								</el-descriptions-item>
								<el-descriptions-item label="首次等待 group_wait">{{ route.group_wait || '-' }}</el-descriptions-item>
								<el-descriptions-item label="分组间隔 group_interval">{{ route.group_interval || '-' }}</el-descriptions-item>
								<el-descriptions-item label="重复间隔 repeat_interval">{{ route.repeat_interval || '-' }}</el-descriptions-item>
							</el-descriptions>
						</div>
					</el-col>
					<el-col :xs="24" :sm="12">
						<div class="route-card">
							<div class="route-card-title">接收器（receivers）</div>
							<el-table :data="receivers" border stripe empty-text="无接收器" size="small">
								<el-table-column prop="name" label="名称" min-width="120" />
								<el-table-column label="集成类型" min-width="160">
									<template #default="{ row }">
										<el-tag v-for="t in row.integrations" :key="t" size="small" type="info" class="matcher-tag">{{ t }}</el-tag>
									</template>
								</el-table-column>
							</el-table>
						</div>
					</el-col>
				</el-row>
			</el-tab-pane>
		</el-tabs>

		<!-- ===== 新建静默对话框 ===== -->
		<el-dialog v-model="silenceDialog" title="新建静默" width="620px" :close-on-click-modal="false">
			<el-form :model="silenceForm" label-width="100px">
				<el-form-item label="匹配方式">
					<el-radio-group v-model="silenceForm.matchType">
						<el-radio-button label="alertname">按告警名称</el-radio-button>
						<el-radio-button label="instance">按实例</el-radio-button>
						<el-radio-button label="custom">自定义标签</el-radio-button>
					</el-radio-group>
				</el-form-item>

				<template v-if="silenceForm.matchType !== 'custom'">
					<el-form-item label="匹配值">
						<el-input v-model="silenceForm.matchValue" placeholder="输入要静默的值" clearable />
					</el-form-item>
					<el-form-item label="匹配规则">
						<el-switch v-model="silenceForm.matchRegex" />
						<span class="form-hint">
							{{ silenceForm.matchRegex ? '正则匹配（=~），如 交叉楼.* 可一次覆盖一组' : '精确匹配（=），值必须与标签值完全一致' }}
						</span>
					</el-form-item>
				</template>

				<template v-else>
					<el-form-item v-for="(m, i) in silenceForm.customMatchers" :key="i" :label="i === 0 ? '匹配条件' : ''">
						<div class="matcher-row">
							<el-input v-model="m.name" placeholder="标签名" class="mr-name" />
							<el-select v-model="m.isRegex" class="mr-regex">
								<el-option label="=（精确）" :value="false" />
								<el-option label="=~（正则）" :value="true" />
							</el-select>
							<el-input v-model="m.value" placeholder="标签值" class="mr-value" />
							<el-button
								v-if="silenceForm.customMatchers.length > 1"
								link
								type="danger"
								:icon="Delete"
								@click="removeCustomMatcher(i)"
							/>
						</div>
					</el-form-item>
					<el-form-item>
						<el-button link type="primary" :icon="Plus" @click="addCustomMatcher">添加条件</el-button>
						<span class="form-hint">多个条件之间是「同时满足」（AND）</span>
					</el-form-item>
				</template>

				<el-form-item label="将提交">
					<div class="matcher-preview">
						<el-tag
							v-for="(m, i) in previewMatchers"
							:key="i"
							size="small"
							:type="m.isRegex ? 'warning' : 'info'"
							class="matcher-tag"
						>
							{{ m.name }}{{ m.isRegex ? '=~' : '=' }}{{ m.value }}
						</el-tag>
						<span v-if="!previewMatchers.length" class="form-hint">请先填写匹配条件</span>
						<div v-if="regexError" class="form-warn">{{ regexError }}</div>
						<div v-else-if="regexHint" class="form-warn">{{ regexHint }}</div>
					</div>
				</el-form-item>

				<el-form-item label="静默时长">
					<el-select v-model="silenceForm.duration" style="width: 100%">
						<el-option label="30 分钟" :value="30" />
						<el-option label="1 小时" :value="60" />
						<el-option label="2 小时" :value="120" />
						<el-option label="4 小时" :value="240" />
						<el-option label="8 小时" :value="480" />
						<el-option label="24 小时" :value="1440" />
					</el-select>
				</el-form-item>
				<el-form-item label="备注">
					<el-input v-model="silenceForm.comment" type="textarea" :rows="2" placeholder="静默原因（建议写清：谁 + 为什么）" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="silenceDialog = false">取消</el-button>
				<el-button type="primary" :loading="silenceSubmitting" @click="submitSilence">确定</el-button>
			</template>
		</el-dialog>

		<!-- ===== 告警详情对话框 ===== -->
		<el-dialog v-model="detailDialog" title="告警详情" width="640px">
			<el-descriptions :column="2" border size="small">
				<el-descriptions-item label="告警名称" :span="2">{{ detail.alertname || '-' }}</el-descriptions-item>
				<el-descriptions-item label="级别">
					<el-tag :type="severityType(detail.severity)" size="small" effect="dark">{{ severityText(detail.severity) }}</el-tag>
				</el-descriptions-item>
				<el-descriptions-item label="状态">{{ detail.silenced ? '已静默' : detail.inhibited ? '已抑制' : '告警中' }}</el-descriptions-item>
				<el-descriptions-item label="实例" :span="2">{{ detail.instance || '-' }}</el-descriptions-item>
				<el-descriptions-item label="指纹" :span="2">
					<span style="font-family: monospace">{{ detail.fingerprint || '-' }}</span>
					<span class="form-hint">Alertmanager 按「全部标签」的哈希生成指纹：指纹相同才是同一条告警，不同就是两条独立告警</span>
				</el-descriptions-item>
				<el-descriptions-item label="开始时间">{{ fmtTime(detail.startsAt) }}</el-descriptions-item>
				<el-descriptions-item label="恢复时间">{{ fmtTime(detail.endsAt) }}</el-descriptions-item>
				<el-descriptions-item label="摘要" :span="2">{{ detail.summary || '-' }}</el-descriptions-item>
				<el-descriptions-item label="描述" :span="2">{{ detail.description || '-' }}</el-descriptions-item>
				<el-descriptions-item label="接收器" :span="2">
					<el-tag v-for="r in detail.receivers" :key="r" size="small" class="matcher-tag">{{ r }}</el-tag>
					<span v-if="!detail.receivers?.length">-</span>
				</el-descriptions-item>
				<el-descriptions-item label="全部标签" :span="2">
					<el-tag v-for="(v, k) in detail.labels" :key="k" size="small" type="info" class="matcher-tag">{{ k }}={{ v }}</el-tag>
					<span v-if="!detail.labels">-</span>
				</el-descriptions-item>
			</el-descriptions>
		</el-dialog>
	</div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Refresh, Plus, Bell, Delete } from '@element-plus/icons-vue';
import {
	GetActiveAlerts, GetSilences, CreateSilence, DeleteSilence, GetRouteSummary,
} from './api';

const SEVERITY_MAP: Record<string, { text: string; type: any }> = {
	critical: { text: '严重', type: 'danger' },
	warning: { text: '警告', type: 'warning' },
	info: { text: '提示', type: 'info' },
};

export default defineComponent({
	name: 'alertManage',
	setup() {
		const activeTab = ref('alerts');
		const stateFilter = ref('');

		// 活跃告警
		const alerts = ref<any[]>([]);
		const alertsLoading = ref(false);
		const filteredAlerts = computed(() => {
			if (!stateFilter.value) return alerts.value;
			if (stateFilter.value === 'suppressed') return alerts.value.filter((a) => a.silenced);
			return alerts.value.filter((a) => !a.silenced);
		});

		// 静默
		const silences = ref<any[]>([]);
		const silencesLoading = ref(false);
		const hideExpired = ref(true);
		const silenceDialog = ref(false);
		const silenceSubmitting = ref(false);
		const silenceForm = ref({
			matchType: 'alertname',
			matchValue: '',
			matchRegex: false,
			customMatchers: [{ name: 'alertname', value: '', isRegex: false }],
			duration: 60,
			comment: '',
		});

		// 路由
		const route = ref<any>({});
		const receivers = ref<any[]>([]);
		const routeLoading = ref(false);

		// 详情
		const detailDialog = ref(false);
		const detail = ref<any>({});

		const severityType = (s: string) => SEVERITY_MAP[s]?.type || 'info';
		const severityText = (s: string) => SEVERITY_MAP[s]?.text || s || '-';

		const fmtTime = (t: string) => {
			if (!t) return '-';
			const d = new Date(t);
			if (isNaN(d.getTime())) return t;
			const pad = (x: number) => (x < 10 ? '0' + x : '' + x);
			return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
		};

		// 状态判定：优先用 Alertmanager 返回的权威 status.state（active / pending / expired），
		// 拿不到才退回用 endsAt 自己算。不要只靠 endsAt —— AM 的 state 才是唯一真值。
		const silenceState = (row: any) => {
			const st = ((row || {}).status || {}).state;
			if (st) return st;
			if (!row || !row.endsAt) return 'active';
			const t = new Date(row.endsAt).getTime();
			if (isNaN(t)) return 'active';
			return t > Date.now() ? 'active' : 'expired';
		};

		// 「生效中」= 还没失效（含 pending 待生效）
		const silenceActive = (row: any) => silenceState(row) !== 'expired';

		const silenceStateText = (row: any) => {
			const st = silenceState(row);
			return st === 'active' ? '生效中' : st === 'pending' ? '待生效' : '已过期';
		};

		const silenceStateType = (row: any) => {
			const st = silenceState(row);
			return st === 'active' ? 'success' : st === 'pending' ? 'warning' : 'info';
		};

		const activeSilenceCount = computed(() => silences.value.filter((s) => silenceActive(s)).length);
		const expiredCount = computed(() => silences.value.filter((s) => !silenceActive(s)).length);

		// Alertmanager 会把已失效的静默一并返回，默认只展示生效中的
		const visibleSilences = computed(() =>
			hideExpired.value ? silences.value.filter((s) => silenceActive(s)) : silences.value
		);

		// ---- 匹配条件：构造 / 预览 / 校验 ----
		const previewMatchers = computed(() => {
			const f = silenceForm.value;
			if (f.matchType === 'custom') {
				return (f.customMatchers || [])
					.filter((m: any) => (m.name || '').trim() && (m.value || '').trim())
					.map((m: any) => ({ name: (m.name || '').trim(), value: (m.value || '').trim(), isRegex: !!m.isRegex }));
			}
			const v = (f.matchValue || '').trim();
			if (!v) return [];
			return [{ name: f.matchType, value: v, isRegex: !!f.matchRegex }];
		});

		const regexError = computed(() => {
			for (const m of previewMatchers.value) {
				if (!m.isRegex) continue;
				try {
					new RegExp(m.value);
				} catch (e: any) {
					return `正则不合法（${m.name}=~${m.value}）：${e?.message || e}`;
				}
			}
			return '';
		});

		// 值里含正则符号却没开正则 → 精确匹配永远命中不了，提前拦住
		const regexHint = computed(() => {
			const bad = previewMatchers.value.filter((m) => !m.isRegex && /[*^$\\[\](){}|?+]/.test(m.value));
			if (!bad.length) return '';
			return `提示：「${bad.map((m) => m.value).join('、')}」含正则符号，但当前是精确匹配 → 会静默不生效，请把匹配规则切到正则（=~）`;
		});

		const addCustomMatcher = () => {
			silenceForm.value.customMatchers.push({ name: '', value: '', isRegex: false });
		};

		const removeCustomMatcher = (i: number) => {
			silenceForm.value.customMatchers.splice(i, 1);
		};

		const loadAlerts = async () => {
			alertsLoading.value = true;
			try {
				const res: any = await GetActiveAlerts();
				if (res.code === 2000) {
					alerts.value = res.data || [];
				} else {
					ElMessage.error(res.msg || '获取活跃告警失败');
				}
			} catch (e) {
				ElMessage.error('获取活跃告警失败');
			} finally {
				alertsLoading.value = false;
			}
		};

		const loadSilences = async () => {
			silencesLoading.value = true;
			try {
				const res: any = await GetSilences();
				if (res.code === 2000) {
					silences.value = res.data || [];
				} else {
					ElMessage.error(res.msg || '获取静默失败');
				}
			} catch (e) {
				ElMessage.error('获取静默失败');
			} finally {
				silencesLoading.value = false;
			}
		};

		const loadRoute = async () => {
			routeLoading.value = true;
			try {
				const res: any = await GetRouteSummary();
				if (res.code === 2000) {
					route.value = res.data?.route || {};
					receivers.value = res.data?.receivers || [];
				} else {
					ElMessage.error(res.msg || '获取路由配置失败');
				}
			} catch (e) {
				ElMessage.error('获取路由配置失败');
			} finally {
				routeLoading.value = false;
			}
		};

		const openSilence = (row: any) => {
			silenceForm.value = {
				matchType: 'alertname',
				matchValue: row?.alertname || '',
				matchRegex: false,
				customMatchers: [{ name: 'alertname', value: row?.alertname || '', isRegex: false }],
				duration: 60,
				comment: '',
			};
			silenceDialog.value = true;
		};

		const submitSilence = async () => {
			const f = silenceForm.value;
			if (regexError.value) {
				ElMessage.warning(regexError.value);
				return;
			}
			const matchers = previewMatchers.value.map((m) => ({ ...m, isEqual: true }));
			if (!matchers.length) {
				ElMessage.warning('请填写至少一个匹配条件（标签名 + 标签值）');
				return;
			}

			silenceSubmitting.value = true;
			try {
				const res: any = await CreateSilence({
					matchers,
					duration_minutes: f.duration,
					comment: f.comment,
				});
				if (res.code === 2000) {
					ElMessage.success('静默已创建');
					silenceDialog.value = false;
					loadSilences();
					loadAlerts();
				} else {
					ElMessage.error(res.msg || '创建静默失败');
				}
			} catch (e) {
				ElMessage.error('创建静默失败');
			} finally {
				silenceSubmitting.value = false;
			}
		};

		const doDeleteSilence = (row: any) => {
			ElMessageBox.confirm('确定删除该静默吗？删除后告警将立即恢复通知。', '删除静默', {
				confirmButtonText: '删除',
				cancelButtonText: '取消',
				type: 'warning',
			}).then(async () => {
				try {
					const res: any = await DeleteSilence(row.id);
					if (res.code === 2000) {
						// ★ Alertmanager 的 DELETE 只是把静默置为 expired，记录不会被移除
						//   （AM 只在自身保留期结束后由 GC 清理）→ 接口成功 ≠ 记录消失。
						//   这里先本地摘掉该行，再回读一次，保证「界面所见」和「实际是否还在拦告警」一致。
						silences.value = silences.value.filter((s) => s.id !== row.id);
						ElMessage.success('静默已删除，告警将恢复通知');
						loadSilences();
						loadAlerts();
					} else {
						ElMessage.error(res.msg || '删除静默失败');
					}
				} catch (e) {
					ElMessage.error('删除静默失败');
				}
			}).catch(() => {});
		};

		const showDetail = (row: any) => {
			detail.value = row;
			detailDialog.value = true;
		};

		onMounted(() => {
			loadAlerts();
			loadSilences();
			loadRoute();
		});

		return {
			activeTab, stateFilter, alerts, alertsLoading, filteredAlerts,
			silences, visibleSilences, silencesLoading, hideExpired,
			activeSilenceCount, expiredCount,
			silenceStateText, silenceStateType,
			silenceDialog, silenceSubmitting, silenceForm,
			previewMatchers, regexError, regexHint,
			addCustomMatcher, removeCustomMatcher,
			route, receivers, routeLoading, detailDialog, detail,
			severityType, severityText, fmtTime, silenceActive,
			loadAlerts, loadSilences, loadRoute, openSilence, submitSilence,
			doDeleteSilence, showDetail,
			Refresh, Plus, Bell, Delete,
		};
	},
});
</script>

<style scoped>
.alert-manage {
	padding: 4px;
}
.manage-tabs :deep(.el-tabs__header) {
	margin-bottom: 12px;
}
.tab-label {
	display: inline-flex;
	align-items: center;
}
.tab-badge {
	margin-left: 8px;
}
.tab-toolbar {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 12px;
}
.toolbar-tip {
	font-size: 13px;
	color: #909399;
}
.manage-table {
	width: 100%;
}
.matcher-tag {
	margin: 2px 4px 2px 0;
}
.toolbar-check {
	margin-left: 16px;
}
.toolbar-hint {
	margin-left: 10px;
	font-size: 12px;
	color: #e6a23c;
}
.op-muted {
	font-size: 12px;
	color: #c0c4cc;
	cursor: help;
}
.matcher-preview {
	width: 100%;
	line-height: 1.8;
}
.form-hint {
	margin-left: 10px;
	font-size: 12px;
	color: #909399;
}
.form-warn {
	font-size: 12px;
	color: #e6a23c;
	line-height: 1.5;
}
.matcher-row {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
}
.mr-name {
	width: 150px;
	flex: none;
}
.mr-regex {
	width: 118px;
	flex: none;
}
.mr-value {
	flex: 1;
}
.route-card {
	background: #fff;
	border: 1px solid #ebeef5;
	border-radius: 10px;
	padding: 16px;
	min-height: 260px;
}
.route-card-title {
	font-size: 15px;
	font-weight: 600;
	color: #303133;
	margin-bottom: 14px;
	padding-left: 10px;
	border-left: 4px solid #409eff;
	line-height: 1.2;
}
</style>

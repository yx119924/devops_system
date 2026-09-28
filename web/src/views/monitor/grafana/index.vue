<template>
  <div class="grafana-page">
    <div class="grafana-toolbar">
      <span class="grafana-title">监控大屏</span>

      <el-select v-model="sourceId" placeholder="选择 Grafana 数据源" style="width: 190px" @change="onSourceChange">
        <el-option v-for="s in sources" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>

      <el-select
        v-model="dashKey"
        filterable
        allow-create
        default-first-option
        :loading="dashLoading"
        placeholder="选择仪表盘"
        style="width: 340px"
        @change="loadFrame"
      >
        <el-option-group v-for="g in dashGroups" :key="g.label" :label="g.label">
          <el-option v-for="d in g.options" :key="d.url" :label="d.title" :value="d.url">
            <span class="dash-title">{{ d.title }}</span>
            <span class="dash-uid">{{ d.uid }}</span>
          </el-option>
        </el-option-group>
      </el-select>

      <el-select v-model="kioskMode" style="width: 132px" @change="onModeChange">
        <el-option label="TV 模式" value="tv" />
        <el-option label="完整界面" value="none" />
        <el-option label="全屏模式" value="full" />
      </el-select>

      <el-button type="primary" :loading="frameLoading" @click="loadFrame">加载</el-button>
      <el-button :loading="dashLoading" @click="loadDashboards">刷新列表</el-button>
      <el-button :disabled="!iframeSrc" @click="openNew">新窗口打开</el-button>
      <el-button @click="runDiagnose">环境诊断</el-button>
    </div>

    <el-alert
      v-if="tips.length"
      class="grafana-alert"
      type="warning"
      show-icon
      title="Grafana 接入诊断"
    >
      <ul class="tip-list">
        <li v-for="(t, i) in tips" :key="i">{{ t }}</li>
      </ul>
    </el-alert>

    <div class="grafana-body">
      <iframe
        v-if="iframeSrc"
        :src="iframeSrc"
        class="grafana-frame"
        referrerpolicy="no-referrer"
        allowfullscreen
      />
      <el-empty v-else :description="emptyText" :image-size="120" />
    </div>
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, onMounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { DiagnoseGrafana, GetDashboards, GetGrafanaList } from './api';

export default defineComponent({
  name: 'monitorGrafana',
  setup() {
    const sources = ref<any[]>([]);
    const sourceId = ref<number | null>(null);
    const dashboards = ref<any[]>([]);
    const dashKey = ref('');
    const iframeSrc = ref('');
    const kioskMode = ref('tv');
    const dashLoading = ref(false);
    const frameLoading = ref(false);
    const tips = ref<string[]>([]);

    const currentSource = computed(() => sources.value.find((s) => s.id === sourceId.value));
    const baseUrl = computed(() => (currentSource.value?.url || '').trim().replace(/\/+$/, ''));

    /** 按 Grafana 文件夹分组，下拉里好找 */
    const dashGroups = computed(() => {
      const map = new Map<string, any[]>();
      dashboards.value.forEach((d) => {
        const key = d.folder || '（未分组）';
        if (!map.has(key)) map.set(key, []);
        map.get(key)!.push(d);
      });
      return Array.from(map.entries()).map(([label, options]) => ({ label, options }));
    });

    const emptyText = computed(() => {
      if (!sources.value.length) return '还没有 Grafana 数据源，请先在「数据源管理」里添加';
      return '选择仪表盘后自动加载';
    });

    /** 拼 iframe 地址：Grafana 直连 + 可切换的 kiosk 显示模式 */
    const buildSrc = () => {
      const base = baseUrl.value;
      let path = (dashKey.value || '').trim();
      if (!base || !path) return '';
      // 允许直接粘贴完整 URL
      try {
        const asUrl = new URL(path);
        if (asUrl.origin !== new URL(base).origin) {
          ElMessage.error('只能嵌入当前数据源地址下的仪表盘');
          return '';
        }
        path = asUrl.pathname + asUrl.search;
      } catch (e) {
        // 相对路径，正常情况
      }
      if (!path.startsWith('/')) path = '/' + path;
      // 显示模式：tv 只隐藏侧边栏（保留顶部导航，含变量筛选栏与时间选择器）
      //           full 顶部导航 + 侧边栏全隐藏（kiosk 不带值即为 full）
      //           none 完整 Grafana 界面，与直接访问一致
      if (kioskMode.value === 'none') return `${base}${path}`;
      const sep = path.includes('?') ? '&' : '?';
      const val = kioskMode.value === 'tv' ? 'tv' : '';
      return `${base}${path}${sep}kiosk${val ? '=' + val : ''}`;
    };

    const loadFrame = () => {
      if (!sourceId.value) {
        ElMessage.warning('请先选择 Grafana 数据源');
        return;
      }
      const src = buildSrc();
      if (!src) {
        ElMessage.warning('请选择要展示的仪表盘');
        return;
      }
      frameLoading.value = true;
      iframeSrc.value = '';
      // 置空后下一帧再赋值，保证「加载」按钮能强制刷新同一个仪表盘
      window.setTimeout(() => {
        iframeSrc.value = src;
        frameLoading.value = false;
      }, 30);
    };

    const loadDashboards = async () => {
      if (!sourceId.value) return;
      dashLoading.value = true;
      dashboards.value = [];
      dashKey.value = '';
      iframeSrc.value = '';
      tips.value = [];
      try {
        const res: any = await GetDashboards(sourceId.value);
        if (res?.code === 2000) {
          dashboards.value = res.data || [];
          if (dashboards.value.length) {
            dashKey.value = dashboards.value[0].url; // 默认展示第一个
            loadFrame();
          } else {
            ElMessage.warning('该 Grafana 下没有可用的仪表盘');
          }
        } else {
          tips.value = [res?.msg || '获取仪表盘列表失败'];
          ElMessage.error(res?.msg || '获取仪表盘列表失败');
        }
      } catch (e: any) {
        ElMessage.error('获取仪表盘列表异常');
      } finally {
        dashLoading.value = false;
      }
    };

    const onSourceChange = () => {
      loadDashboards();
    };

    const onModeChange = () => {
      if (dashKey.value) loadFrame();
    };

    const openNew = () => {
      if (iframeSrc.value) window.open(iframeSrc.value, '_blank', 'noopener,noreferrer');
    };

    const runDiagnose = async () => {
      if (!sourceId.value) {
        ElMessage.warning('请先选择 Grafana 数据源');
        return;
      }
      try {
        const res: any = await DiagnoseGrafana(sourceId.value);
        if (res?.code === 2000) {
          const data = res.data || {};
          const probs: string[] = data.tips || [];
          tips.value = probs;
          if (!probs.length) {
            ElMessage.success(`诊断通过${data.version ? '（Grafana ' + data.version + '）' : ''}`);
          }
        } else {
          ElMessage.error(res?.msg || '诊断失败');
        }
      } catch (e: any) {
        ElMessage.error('诊断请求异常');
      }
    };

    onMounted(async () => {
      try {
        const res: any = await GetGrafanaList();
        if (res?.code === 2000) {
          sources.value = res.data || [];
          if (sources.value.length) {
            sourceId.value = sources.value[0].id;
            await loadDashboards();
          } else {
            ElMessage.warning('还没有 Grafana 数据源，请先在「数据源管理」里添加一个 Grafana 类型的数据源');
          }
        } else {
          ElMessage.error(res?.msg || '获取 Grafana 数据源失败');
        }
      } catch (e: any) {
        ElMessage.error('获取 Grafana 数据源异常');
      }
    });

    return {
      sources,
      sourceId,
      dashboards,
      dashKey,
      iframeSrc,
      dashLoading,
      frameLoading,
      tips,
      kioskMode,
      dashGroups,
      emptyText,
      loadFrame,
      loadDashboards,
      onSourceChange,
      onModeChange,
      openNew,
      runDiagnose,
    };
  },
});
</script>

<style scoped>
.grafana-page {
  height: calc(100vh - 130px);
  display: flex;
  flex-direction: column;
  padding: 16px;
  box-sizing: border-box;
}
.grafana-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: #fff;
  border-radius: 10px;
  margin-bottom: 12px;
  border: 1px solid #ebeef5;
  flex-wrap: wrap;
}
.grafana-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-right: 4px;
}
.grafana-alert {
  margin-bottom: 12px;
}
.tip-list {
  margin: 6px 0 0;
  padding-left: 18px;
}
.tip-list li {
  line-height: 1.7;
}
.grafana-body {
  flex: 1;
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #ebeef5;
}
.grafana-frame {
  width: 100%;
  height: 100%;
  border: none;
}
.dash-title {
  margin-right: 10px;
}
.dash-uid {
  color: #a8abb2;
  font-size: 12px;
  float: right;
}
</style>

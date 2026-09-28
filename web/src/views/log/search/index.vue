<template>
  <div class="log-search">
    <!-- 筛选栏 -->
    <div class="log-filter">
      <el-select v-model="sourceId" placeholder="选择 ES 数据源" style="width: 200px" @change="onSourceChange">
        <el-option v-for="s in sources" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>

      <el-select
        v-model="indexPattern"
        placeholder="索引模式"
        filterable
        allow-create
        default-first-option
        clearable
        :loading="indexLoading"
        style="width: 340px"
        @change="onIndexChange"
      >
        <el-option v-for="idx in indices" :key="idx.pattern" :label="idx.pattern" :value="idx.pattern">
          <span style="float: left">{{ idx.pattern }}</span>
          <span style="float: right; color: #909399; font-size: 12px; margin-left: 20px">
            {{ idx.count ? idx.count + ' 索引 · ' + fmtDocs(idx.docs) + ' · ' + fmtSize(idx.size) : '暂无索引' }}
          </span>
        </el-option>
      </el-select>
      <el-button :loading="indexLoading" @click="loadIndices">刷新索引</el-button>

      <el-date-picker
        v-model="timeRange"
        type="datetimerange"
        range-separator="至"
        start-placeholder="开始时间"
        end-placeholder="结束时间"
        value-format="YYYY-MM-DD HH:mm:ss"
        :shortcuts="shortcuts"
        style="width: 360px"
      />
      <el-select v-model="level" placeholder="级别" clearable style="width: 120px">
        <el-option v-for="l in levels" :key="l" :label="l" :value="l" />
      </el-select>
      <el-input v-model="keyword" placeholder="关键字（全文检索）" clearable style="width: 240px" @keyup.enter="doSearch" />
      <el-button type="primary" :loading="loading" @click="doSearch">查询</el-button>
    </div>

    <!-- 结果 -->
    <div class="log-result">
      <div class="log-meta">
        <template v-if="searched">
          <span>共 {{ totalExact ? total : '≥ ' + total }} 条日志</span>
          <span v-if="!totalExact" class="cap-tip">已达 ES 统计上限，实际更多（缩小时间范围可看准）</span>
          <span v-if="activeIndex"> · 索引 <code>{{ activeIndex }}</code></span>
        </template>
        <span v-else>请选择数据源与索引模式后查询</span>
      </div>
      <el-empty v-if="searched && !logs.length" description="无匹配日志" :image-size="100" />
      <div v-else class="log-list">
        <div v-for="(log, i) in logs" :key="i" class="log-item">
          <span class="log-time">{{ log.timestamp || '-' }}</span>
          <el-tag :type="levelTag(log.level)" size="small" effect="light">{{ log.level || '-' }}</el-tag>
          <div class="log-body">
            <div class="log-msg">{{ log.message || '-' }}</div>
            <div class="log-sub" :title="log.file || ''">
              <span v-if="log.host">{{ log.host }}</span>
              <template v-if="log.service"> · {{ log.service }}</template>
              <template v-if="log.env"> · {{ log.env }}</template>
              <template v-if="log.file"> · {{ shortFile(log.file) }}</template>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, onMounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { GetEsList, GetEsIndices, SearchLogs } from './api';

export default defineComponent({
  name: 'logSearch',
  setup() {
    const sources = ref<any[]>([]);
    const sourceId = ref<number | null>(null);
    const indices = ref<any[]>([]);
    const indexPattern = ref('');
    const indexLoading = ref(false);
    const activeIndex = ref('');
    const timeRange = ref<[string, string] | null>(null);
    const level = ref('');
    const keyword = ref('');
    const loading = ref(false);
    const searched = ref(false);
    const total = ref(0);
    const totalExact = ref(true);
    const logs = ref<any[]>([]);

    const levels = ['critical', 'error', 'warning', 'info', 'debug'];
    const shortcuts = [
      { text: '最近15分钟', value: () => { const e = new Date(); const s = new Date(e.getTime() - 15 * 60 * 1000); return [s, e]; } },
      { text: '最近1小时', value: () => { const e = new Date(); const s = new Date(e.getTime() - 60 * 60 * 1000); return [s, e]; } },
      { text: '最近1天', value: () => { const e = new Date(); const s = new Date(e.getTime() - 24 * 60 * 60 * 1000); return [s, e]; } },
    ];

    const levelTag = (lv: string) => {
      const m: any = { critical: 'danger', error: 'danger', warning: 'warning', info: 'info', debug: 'info' };
      return m[lv] || 'info';
    };

    /** 文档数格式化：12.5万 / 1.20亿 */
    const fmtDocs = (n: number) => {
      if (!n) return '0';
      if (n >= 100000000) return (n / 100000000).toFixed(2) + '亿';
      if (n >= 10000) return (n / 10000).toFixed(1) + '万';
      return String(n);
    };

    /** 存储占用格式化：1.2GB / 128MB */
    const fmtSize = (b: number) => {
      if (!b) return '0';
      const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
      let i = 0;
      let v = b;
      while (v >= 1024 && i < units.length - 1) {
        v /= 1024;
        i += 1;
      }
      return v.toFixed(v >= 100 || i === 0 ? 0 : 1) + units[i];
    };

    /** 日志路径只显示文件名，完整路径挂在 title 上 */
    const shortFile = (p: string) => {
      if (!p) return '';
      const i = p.lastIndexOf('/');
      return i >= 0 ? p.slice(i + 1) : p;
    };

    /** 拉取索引模式列表（滚动索引已在后端归并成通配模式） */
    const loadIndices = async () => {
      if (!sourceId.value) return;
      indexLoading.value = true;
      try {
        const res: any = await GetEsIndices(sourceId.value);
        if (res?.code === 2000) {
          indices.value = res.data?.list || [];
          // 优先选中数据源上配置的索引模式
          const cur = indices.value.find((x: any) => x.current) || indices.value[0];
          indexPattern.value = cur?.pattern || res.data?.current || '';
        } else {
          indices.value = [];
          ElMessage.error(res?.msg || '索引列表获取失败');
        }
      } catch (e) {
        ElMessage.error('索引列表获取异常');
      } finally {
        indexLoading.value = false;
      }
    };

    const onSourceChange = async () => {
      searched.value = false;
      logs.value = [];
      total.value = 0;
      totalExact.value = true;
      activeIndex.value = '';
      await loadIndices();
    };

    /** 切换索引后直接开查，省一次点击 */
    const onIndexChange = () => {
      if (sourceId.value && indexPattern.value) doSearch();
    };

    const doSearch = async () => {
      if (!sourceId.value) {
        ElMessage.warning('请先选择 ES 数据源');
        return;
      }
      if (!indexPattern.value) {
        ElMessage.warning('请先选择索引模式');
        return;
      }
      loading.value = true;
      try {
        const params: any = {
          index: indexPattern.value,
          keyword: keyword.value,
          level: level.value,
          size: 100,
          from_offset: 0,
        };
        if (timeRange.value && timeRange.value.length === 2) {
          params.from = timeRange.value[0];
          params.to = timeRange.value[1];
        }
        const res: any = await SearchLogs(sourceId.value, params);
        if (res?.code === 2000) {
          total.value = res.data?.total ?? 0;
          totalExact.value = res.data?.total_exact !== false;
          logs.value = res.data?.logs || [];
          activeIndex.value = res.data?.index || indexPattern.value;
          searched.value = true;
        } else {
          ElMessage.error(res?.msg || '查询失败');
        }
      } catch (e) {
        ElMessage.error('查询异常');
      } finally {
        loading.value = false;
      }
    };

    onMounted(async () => {
      try {
        const res: any = await GetEsList();
        if (res?.code === 2000) {
          sources.value = res.data || [];
          if (sources.value.length) {
            sourceId.value = sources.value[0].id;
            await loadIndices();
          }
        }
      } catch (e) {
        // 静默
      }
    });

    return {
      sources, sourceId, indices, indexPattern, indexLoading, activeIndex,
      timeRange, level, keyword, loading, searched, total, totalExact, logs,
      levels, shortcuts, levelTag, fmtDocs, fmtSize, shortFile, loadIndices, onSourceChange, onIndexChange, doSearch,
    };
  },
});
</script>

<style scoped>
.log-search {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.log-filter {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 14px 16px;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
}
.log-result {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  padding: 14px 16px;
  min-height: 400px;
}
.log-meta {
  font-size: 13px;
  color: #909399;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f2f5;
  margin-bottom: 6px;
}
.log-meta code {
  color: #409eff;
  background: #ecf5ff;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.cap-tip {
  color: #e6a23c;
  margin-left: 6px;
  font-size: 12px;
}
.log-list {
  display: flex;
  flex-direction: column;
}
.log-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 4px;
  border-bottom: 1px solid #f5f7fa;
  font-family: monospace;
}
.log-item:last-child { border-bottom: none; }
.log-time {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  min-width: 150px;
}
.log-body { flex: 1; min-width: 0; }
.log-msg {
  font-size: 13px;
  color: #303133;
  word-break: break-all;
  line-height: 1.5;
}
.log-sub {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 3px;
}
</style>

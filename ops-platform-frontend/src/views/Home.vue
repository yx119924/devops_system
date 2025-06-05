<template>
  <div class="home-container">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="box-card">
          <template #header>
            <div class="card-header">
              <span>系统概览</span>
            </div>
          </template>
          <div class="item">
            <span>当前用户：</span>
            <span>{{ userInfo?.username }}</span>
          </div>
          <div class="item">
            <span>上次登录：</span>
            <span>{{ formatDate(userInfo?.last_login) }}</span>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="box-card">
          <template #header>
            <div class="card-header">
              <span>快速操作</span>
            </div>
          </template>
          <div class="quick-actions">
            <el-button type="primary" plain>查看日志</el-button>
            <el-button type="success" plain>系统监控</el-button>
            <el-button type="warning" plain>告警信息</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="box-card">
          <template #header>
            <div class="card-header">
              <span>系统状态</span>
            </div>
          </template>
          <div class="status-list">
            <el-tag type="success">运行正常</el-tag>
            <div class="status-item">
              <span>CPU使用率：</span>
              <el-progress :percentage="30" />
            </div>
            <div class="status-item">
              <span>内存使用率：</span>
              <el-progress :percentage="45" />
            </div>
            <div class="status-item">
              <span>磁盘使用率：</span>
              <el-progress :percentage="60" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { computed } from 'vue'
import { useStore } from 'vuex'

export default {
  name: 'HomePage',
  setup() {
    const store = useStore()
    const userInfo = computed(() => store.getters['user/userInfo'])

    const formatDate = (dateString) => {
      if (!dateString) return '暂无记录'
      return new Date(dateString).toLocaleString()
    }

    return {
      userInfo,
      formatDate
    }
  }
}
</script>

<style scoped>
.home-container {
  padding: 20px;
}

.box-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.item {
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.status-item {
  margin-top: 10px;
}

.el-tag {
  margin-bottom: 10px;
}
</style>
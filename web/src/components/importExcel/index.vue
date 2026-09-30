<template>
  <div style="display: inline-block">
    <el-button  type="success" @click="handleImport()">
      <slot>{{ $t('message.components.importExcel.import') }}</slot>
    </el-button>
    <el-dialog :title="props.upload.title" v-model="uploadShow" width="400px" append-to-body>
      <div v-loading="loading">
        <el-upload
            ref="uploadRef"
            :limit="1"
            accept=".xlsx, .xls"
            :headers="props.upload.headers"
            :action="props.upload.url"
            :disabled="isUploading"
            :on-progress="handleFileUploadProgress"
            :on-success="handleFileSuccess"
            :on-error="handleFileUploadError"
            :auto-upload="false"
            drag
        >
          <i class="el-icon-upload" />
          <div class="el-upload__text">
            {{ $t('message.components.importExcel.dragDrop') }}，
            <em>{{ $t('message.components.importExcel.clickUpload') }}</em>
          </div>
          <div class="el-upload__tip" style="color:red">{{ $t('message.components.importExcel.uploadTip') }}</div>
        </el-upload>
        <div>
          <el-button type="warning" style="font-size:14px;margin-top: 20px" @click="importTemplate">{{ $t('message.components.importExcel.downloadTemplate') }}</el-button>
          <el-button type="warning" style="font-size:14px;margin-top: 20px" @click="updateTemplate">{{ $t('message.components.importExcel.batchUpdateTemplate') }}</el-button>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" :disabled="loading" @click="submitFileForm">{{ $t('message.components.importExcel.confirm') }}</el-button>
          <el-button :disabled="loading" @click="uploadShow = false">{{ $t('message.components.importExcel.cancel') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup name="importExcel">
import { request, downloadFile } from '/@/utils/service';
import {inject,ref} from "vue";
import { getBaseURL } from '/@/utils/baseUrl';
import { Session } from '/@/utils/storage';
import {  ElMessage, ElMessageBox } from 'element-plus'
import type { Action } from 'element-plus'
import { useI18n } from 'vue-i18n';
const { t } = useI18n();
const refreshView = inject('refreshView')

let props = defineProps({
  upload: {
    type: Object,
    default () {
      return {
        // 是否显示弹出层
        open: true,
        // 弹出层标题
        title: '',
        // 是否禁用上传
        isUploading: false,
        // 是否更新已经存在的用户数据
        updateSupport: 0,
        // 设置上传的请求头部
        headers: { Authorization: 'JWT ' + Session.get('token') },
        // 上传的地址
        url: getBaseURL() + 'api/system/file/'
      }
    }
  },
  api: { // 导入接口地址
    type: String,
    default () {
      return undefined
    }
  }
})

let loading = ref(false)
const uploadRef = ref()
const uploadShow = ref(false)
const isUploading = ref(false)
/** 导入按钮操作 */
const handleImport = function () {
  uploadShow.value = true
}

/** 下载模板操作 */
const importTemplate=function () {
  downloadFile({
    url: props.api + 'import_data/',
    params: {},
    method: 'get'
  })
}
/***
 * 批量更新模板
 */
const updateTemplate=function () {
  downloadFile({
    url: props.api + 'update_template/',
    params: {},
    method: 'get'
  })
}
// 文件上传中处理
const handleFileUploadProgress=function (event:any, file:any, fileList:any) {
  isUploading.value = true
}
// 文件上传失败处理
// ★ 原来没有绑定 on-error，上传失败（401 / 500 / 网络中断）完全静默，
//   用户只看到"点了没反应"。这里把原因显示出来。
const handleFileUploadError=function (err:any) {
  isUploading.value = false
  let detail = ''
  try {
    detail = JSON.parse(err?.message || '{}')?.msg || ''
  } catch (e) { /* 非 JSON 响应，忽略 */ }
  ElMessage.error({
    message: '文件上传失败：' + (detail || err?.message || '请检查登录状态或网络连接'),
    duration: 8000,
    showClose: true,
  })
}
// 文件上传成功处理
const handleFileSuccess=function (response:any, file:any, fileList:any) {
  isUploading.value = false
  loading.value = true
  uploadRef.value.clearFiles()
  // 是否更新已经存在的用户数据
  return request({
    url: props.api + 'import_data/',
    method: 'post',
    data: {
      url: response.data.url
    }
  }).then((response:any) => {
    loading.value = false
    ElMessageBox.alert(t('message.components.importExcel.importSuccessMsg'), t('message.components.importExcel.importSuccess'), {
      confirmButtonText: 'OK',
      callback: (action: Action) => {
        refreshView()
      },
    })
  }).catch((e:any)=>{
    loading.value = false
    // ★ 原来这里是**空 catch** ⇒ 后端返回的校验错误（如"机房不存在""必填项为空"）
    //   被完全吞掉，用户只看到"没导入成功"却不知道哪一行哪个字段错了。
    //   后端统一响应体是 {code, msg, data}，优先取 msg（与 AI 助手页面同一套处理）。
    ElMessage.error({
      message: e?.msg || e?.message || '导入失败，请查看后端日志（docker logs dvadmin3-django）',
      duration: 8000,
      showClose: true,
    })
  })

}
// 提交上传文件
const submitFileForm=function () {
  uploadRef.value.submit()
}

</script>

<style scoped>

</style>

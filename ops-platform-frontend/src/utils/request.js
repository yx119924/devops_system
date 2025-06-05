import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import store from '../store'

// 创建axios实例
const service = axios.create({
  baseURL: 'http://localhost:8000', // API的base_url
  timeout: 5000 // 请求超时时间
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    // 在发送请求之前做些什么
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    // 对请求错误做些什么
    console.error('请求错误：', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    // 对响应数据做点什么
    const res = response.data
    
    // 如果返回的是二进制数据，直接返回
    if (response.config.responseType === 'blob') {
      return res
    }
    
    return res
  },
  error => {
    // 对响应错误做点什么
    console.error('响应错误：', error)
    
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 400:
          ElMessage.error(data.message || '请求参数错误')
          break
        case 401:
          // token过期或未登录
          ElMessage.error(data.message || '登录已过期，请重新登录')
          store.dispatch('user/logout')
          router.push('/login')
          break
        case 403:
          ElMessage.error('没有权限访问该资源')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器错误，请稍后重试')
          break
        default:
          ElMessage.error(error.response.data.message || '未知错误')
      }
    } else {
      ElMessage.error('网络错误，请检查您的网络连接')
    }
    
    return Promise.reject(error)
  }
)

export default service
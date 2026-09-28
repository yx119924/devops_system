<template>
	<fs-page>
		<div class="container">
			<header>
				<div class="buttons-group">
					<el-button type="primary" :icon="FolderAdd" @click="tabsDrawer = true">
						{{ $t('message.pages.config.buttons.addGroup') }}
					</el-button>
					<el-button type="warning" :icon="Edit" @click="contentDrawer = true">
						{{ $t('message.pages.config.buttons.addContent') }}
					</el-button>
					<el-button type="danger" :icon="Delete" @click="handleDeleteGroup">
						{{ $t('message.pages.config.buttons.deleteGroup') }}
					</el-button>
				</div>
				<div class="search-box">
					<el-input
						v-model="searchQuery"
						:placeholder="$t('message.pages.config.header.searchPlaceholder')"
						clearable
						prefix-icon="Search"
					/>
				</div>
			</header>

			<div class="filters">
				<el-button
					v-for="tab in editableTabs"
					:key="tab.key"
					:type="editableTabsValue === tab.key ? 'primary' : 'default'"
					@click="editableTabsValue = tab.key"
					class="filter-btn"
				>
					{{ tab.title_i18n || tab.title }}
				</el-button>
			</div>

			<div class="config-grid">
				<div
					v-for="item in filteredFormList"
					:key="item.id"
					class="config-card"
				>
					<div class="card-header">
						<div>
							<div class="card-title">{{ item.title_i18n || item.title }}</div>
							<div v-if="item.placeholder" class="card-subtitle">{{ item.placeholder }}</div>
						</div>
						<div class="card-tags">
							<el-tag size="small" :type="getTagType(item.form_item_type_label)">
								{{ getLabel(item.form_item_type_label) }}
							</el-tag>
							<template v-if="item.rule && item.rule.length > 0">
								<el-tag 
									v-for="(rule, index) in parseRules(item.rule)" 
									:key="index" 
									size="small" 
									type="warning"
									class="rule-tag"
								>
									{{ getRuleLabel(rule) }}
								</el-tag>
							</template>
						</div>
					</div>
					<div class="card-content">
						<!-- Key 信息 -->
						<div class="card-meta">
							<el-icon><Key /></el-icon>
							<span class="meta-key">{{ editableTabsValue }}.{{ item.key }}</span>
						</div>
						
						<!-- 值展示区 -->
						<div class="card-value">
							<!-- 开关类型 -->
							<span v-if="item.form_item_type_label === '开关'" class="switch-value">
								<el-switch
									v-model="formData[item.key]"
									active-color="#13ce66"
									inactive-color="#ff4949"
									@change="handleConfigChange(item)"
								/>
							</span>
							<!-- 文本/长文本/数字/日期/时间/日期时间类型 - 编辑模式 -->
							<div v-else-if="['文本', '长文本', '数字', '日期', '时间', '日期时间'].includes(item.form_item_type_label) && editingItem?.id === item.id" class="edit-mode">
								<!-- 文本/长文本/数字类型使用输入框 -->
								<el-input
									v-if="['文本', '长文本', '数字'].includes(item.form_item_type_label)"
									v-model="editingValue"
									:type="item.form_item_type_label === '长文本' ? 'textarea' : 'text'"
									:rows="item.form_item_type_label === '长文本' ? 3 : 1"
									:placeholder="item.placeholder"
									@input="handleNumberInput(item)"
								/>
								<!-- 日期类型使用日期选择器 -->
								<el-date-picker
									v-else-if="item.form_item_type_label === '日期'"
									v-model="editingValue"
									type="date"
									:placeholder="item.placeholder || '请选择日期'"
									format="YYYY-MM-DD"
									value-format="YYYY-MM-DD"
								/>
								<!-- 时间类型使用时间选择器 -->
								<el-time-picker
									v-else-if="item.form_item_type_label === '时间'"
									v-model="editingValue"
									:placeholder="item.placeholder || '请选择时间'"
									format="HH:mm:ss"
									value-format="HH:mm:ss"
								/>
								<!-- 日期时间类型使用日期时间选择器 -->
								<el-date-picker
									v-else
									v-model="editingValue"
									type="datetime"
									:placeholder="item.placeholder || '请选择日期时间'"
									format="YYYY-MM-DD HH:mm:ss"
									value-format="YYYY-MM-DD HH:mm:ss"
								/>
							</div>
							<!-- 下拉/单选/多选类型 - 编辑模式 -->
							<div v-else-if="['下拉', '单选', '多选'].includes(item.form_item_type_label) && editingItem?.id === item.id" class="edit-mode">
								<!-- 下拉选择 -->
								<el-select
									v-if="item.form_item_type_label === '下拉'"
									v-model="editingValue"
									:placeholder="item.placeholder || '请选择'"
									clearable
									style="width: 100%"
								>
									<el-option
										v-for="opt in dictOptions"
										:key="opt.value"
										:label="opt.label"
										:value="opt.value"
									/>
								</el-select>
								<!-- 单选框组 -->
								<el-radio-group v-else-if="item.form_item_type_label === '单选'" v-model="editingValue">
									<el-radio
										v-for="opt in dictOptions"
										:key="opt.value"
										:value="opt.value"
									>
										{{ opt.label }}
									</el-radio>
								</el-radio-group>
								<!-- 多选框组 -->
								<el-checkbox-group v-else v-model="editingValue">
									<el-checkbox
										v-for="opt in dictOptions"
										:key="opt.value"
										:value="opt.value"
									>
										{{ opt.label }}
									</el-checkbox>
								</el-checkbox-group>
							</div>
							<!-- 图片/文件类型 - 编辑模式 -->
							<div v-else-if="['图片(单张)', '图片(多张)', '文件', '文件附件'].includes(item.form_item_type_label) && editingItem?.id === item.id" class="edit-mode">
								<!-- 单张图片 -->
								<div v-if="item.form_item_type_label === '图片(单张)'" class="image-single-edit">
									<!-- 图片预览（可点击替换） -->
									<div v-if="editingValue" class="image-preview-wrapper" @click="triggerUpload">
										<img :src="getFullImageUrl(editingValue)" alt="图片预览" @error="handleImageError" />
										<div class="replace-overlay">
											<el-icon><Refresh /></el-icon>
											<span>{{ $t('message.pages.config.buttons.replace') || '点击替换' }}</span>
										</div>
									</div>
									<!-- 隐藏的 file input -->
									<input
										ref="uploadRef"
										type="file"
										accept="image/*"
										@change="handleFileChange"
										style="display: none;"
									/>
									<!-- URL输入框（备选方案） -->
									<div class="url-input-section">
										<el-divider>{{ $t('message.pages.config.formContent.orInputUrl') || '或直接输入URL' }}</el-divider>
										<el-input
											v-model="editingValue"
											:placeholder="item.placeholder || '请输入图片URL'"
											clearable
										>
											<template #prepend>
												<el-icon><Link /></el-icon>
											</template>
										</el-input>
									</div>
								</div>
								<!-- 多张图片 -->
								<div v-else-if="item.form_item_type_label === '图片(多张)'" class="image-list">
									<!-- 上传按钮 -->
									<el-upload
										:action="uploadUrl"
										:headers="uploadHeaders"
										name="file"
										accept="image/*"
										multiple
										:on-success="(response: any) => handleUploadSuccess(response, 'multiple')"
										:on-error="handleUploadError"
										:limit="10"
										list-type="picture-card"
									>
										<el-icon><Plus /></el-icon>
									</el-upload>
									<!-- 已上传图片列表 -->
									<div v-for="(img, index) in editingValue" :key="index" class="image-item">
										<!-- 小图预览 -->
										<div v-if="img" class="image-thumb">
											<img :src="getFullImageUrl(img)" alt="图片" @error="handleImageError" />
										</div>
										<el-input v-model="editingValue[index]" placeholder="图片URL" clearable />
										<el-button type="danger" size="small" @click="editingValue.splice(index, 1)">删除</el-button>
									</div>
								</div>
								<!-- 单文件 -->
								<div v-else-if="item.form_item_type_label === '文件'" class="file-single-edit">
									<!-- 文件预览（可点击替换） -->
									<div v-if="editingValue" class="file-preview-wrapper" @click="triggerFileUpload">
										<div class="file-icon">
											<el-icon><Document /></el-icon>
										</div>
										<div class="file-info">
											<span class="file-name">{{ getFileName(editingValue) }}</span>
											<span class="file-url">{{ editingValue }}</span>
										</div>
										<div class="replace-overlay">
											<el-icon><Refresh /></el-icon>
											<span>{{ $t('message.pages.config.buttons.replace') || '点击替换' }}</span>
										</div>
									</div>
									<!-- 上传按钮（无文件时显示） -->
									<div v-else class="file-upload-button" @click="triggerFileUpload">
										<el-icon><Plus /></el-icon>
										<span>{{ $t('message.pages.config.buttons.uploadFile') || '上传文件' }}</span>
									</div>
									<!-- 隐藏的 file input -->
									<input
										ref="fileUploadRef"
										type="file"
										@change="handleFileUploadChange"
										style="display: none;"
									/>
									<!-- URL输入框（备选方案） -->
									<div class="url-input-section">
										<el-divider>{{ $t('message.pages.config.formContent.orInputUrl') || '或直接输入URL' }}</el-divider>
										<el-input
											v-model="editingValue"
											:placeholder="item.placeholder || '请输入文件URL'"
											clearable
										>
											<template #prepend>
												<el-icon><Link /></el-icon>
											</template>
										</el-input>
									</div>
								</div>
								<!-- 文件附件列表 -->
								<div v-else-if="item.form_item_type_label === '文件附件'" class="file-list">
									<div v-for="(file, index) in editingValue" :key="index" class="file-item">
										<el-input v-model="editingValue[index]" placeholder="文件URL" clearable />
										<el-button type="danger" size="small" @click="editingValue.splice(index, 1)">删除</el-button>
									</div>
									<el-button type="primary" size="small" @click="editingValue.push('')">添加文件</el-button>
								</div>
							</div>
							<!-- 数组类型 - 编辑模式 -->
							<div v-else-if="item.form_item_type_label === '数组' && editingItem?.id === item.id" class="edit-mode">
								<div class="array-list">
									<div v-for="(arrItem, index) in editingValue" :key="index" class="array-item">
										<el-input v-model="editingValue[index]" placeholder="数组元素" />
										<el-button type="danger" size="small" @click="editingValue.splice(index, 1)">删除</el-button>
									</div>
									<el-button type="primary" size="small" @click="editingValue.push('')">添加元素</el-button>
								</div>
							</div>
							<!-- 文本/长文本/数字/日期/时间/日期时间类型 - 查看模式 -->
							<span v-else-if="['文本', '长文本', '数字', '日期', '时间', '日期时间'].includes(item.form_item_type_label)" class="text-value">{{ displayValue(item) }}</span>
							<!-- 下拉/单选/多选类型 - 查看模式 -->
							<span v-else-if="['下拉', '单选', '多选'].includes(item.form_item_type_label)" class="text-value">{{ displayValue(item) }}</span>
							<!-- 图片/文件类型 - 查看模式 -->
							<div v-else-if="['图片(单张)', '图片(多张)', '文件', '文件附件'].includes(item.form_item_type_label)" class="image-view-mode">
								<!-- 单张图片 -->
								<div v-if="item.form_item_type_label === '图片(单张)' && item.value" class="single-image-preview" @click="handleImagePreview([getFullImageUrl(item.value)])">
									<img :src="getFullImageUrl(item.value)" alt="图片" @error="handleImageError" />
									<div class="preview-icon">
										<el-icon><ZoomIn /></el-icon>
									</div>
								</div>
								<!-- 多张图片 -->
								<div v-else-if="item.form_item_type_label === '图片(多张)' && Array.isArray(item.value) && item.value.length > 0" class="multiple-images-preview">
									<div 
										v-for="(img, index) in item.value" 
										:key="index" 
										class="thumb-item"
										@click="handleImagePreview(item.value.map((i: string) => getFullImageUrl(i)), index)"
									>
										<img :src="getFullImageUrl(img)" alt="图片" @error="handleImageError" />
										<div class="preview-icon">
											<el-icon><ZoomIn /></el-icon>
										</div>
									</div>
								</div>
								<!-- 单文件 -->
								<div v-else-if="item.form_item_type_label === '文件'" class="single-file-preview">
									<div v-if="item.value" class="file-display">
										<div class="file-icon-large">
											<el-icon><Document /></el-icon>
										</div>
										<div class="file-details">
											<span class="file-name">{{ getFileName(item.value) }}</span>
											<a :href="getFullImageUrl(item.value)" target="_blank" class="file-link">
												<el-icon><Link /></el-icon>
												下载文件
											</a>
										</div>
									</div>
								</div>
								<!-- 文件附件列表 -->
								<div v-else-if="item.form_item_type_label === '文件附件' && Array.isArray(item.value) && item.value.length > 0" class="file-list-display">
									<div v-for="(file, index) in item.value" :key="index" class="file-item-display">
										<div class="file-icon-small">
											<el-icon><Document /></el-icon>
										</div>
										<div class="file-info-display">
											<span class="file-name">{{ getFileName(file) }}</span>
											<a :href="getFullImageUrl(file)" target="_blank" class="file-link">
												<el-icon><Link /></el-icon>
												下载
											</a>
										</div>
									</div>
								</div>
								<!-- 无值时显示提示 -->
								<span v-else class="empty-text">暂无文件</span>
							</div>
							<!-- 数组类型 - 查看模式 -->
							<span v-else-if="item.form_item_type_label === '数组'" class="text-value">{{ displayValue(item) }}</span>
							<!-- 其他类型 -->
							<span v-else class="text-value">{{ displayValue(item) }}</span>
						</div>
					</div>
					<div class="card-footer">
						<div class="actions">
							<!-- 编辑模式下的确认和取消按钮 -->
							<template v-if="editingItem?.id === item.id">
								<el-button type="primary" size="small" @click="handleConfirmEdit(item)">
									确认
								</el-button>
								<el-button size="small" @click="handleCancelEdit">
									取消
								</el-button>
							</template>
							<!-- 正常模式下的编辑和删除按钮 - 开关类型不显示编辑按钮 -->
							<template v-else-if="item.form_item_type_label !== 'switch'">
								<el-button type="primary" link :icon="Edit" @click="handleEdit(item)">
									{{ $t('message.pages.config.buttons.edit') }}
								</el-button>
								<el-button type="danger" link :icon="Delete" @click="handleDelete(item)">
									{{ $t('message.pages.config.buttons.delete') }}
								</el-button>
							</template>
							<!-- 开关类型只显示删除按钮 -->
							<template v-else>
								<el-button type="danger" link :icon="Delete" @click="handleDelete(item)">
									{{ $t('message.pages.config.buttons.delete') }}
								</el-button>
							</template>
						</div>
					</div>
				</div>
			</div>

			<!-- 新增分组抽屉 -->
			<el-drawer
				v-model="tabsDrawer"
				:title="$t('message.pages.config.dialog.addGroup')"
				direction="rtl"
				size="30%"
			>
				<addTabs @success="handleTabsSuccess"></addTabs>
			</el-drawer>

			<!-- 新增内容抽屉 -->
			<el-drawer
				v-model="contentDrawer"
				:title="$t('message.pages.config.dialog.addContent')"
				direction="rtl"
				size="30%"
			>
				<addContent @success="handleContentSuccess"></addContent>
			</el-drawer>
		</div>
		<!-- 图片预览组件 -->
		<ElImageViewer
			v-if="showImagePreview"
			:url-list="previewSrcList"
			:initial-index="previewInitialIndex"
			@close="showImagePreview = false"
		/>
	</fs-page>
</template>

<script lang="ts" setup name="config">
import { useI18n } from 'vue-i18n';
import { Edit, FolderAdd, Delete, Key, Link, Plus, Picture, ZoomIn, Refresh, Document } from '@element-plus/icons-vue';
import * as api from './api';
import addTabs from './components/addTabs.vue';
import addContent from './components/addContent.vue';
import { ref, onMounted, watch, computed } from 'vue';
import { storeToRefs } from 'pinia';
import pinia from '/@/stores/index';
import { useThemeConfig } from '/@/stores/themeConfig';
import { ElMessage, ElMessageBox, ElImageViewer } from 'element-plus';
import { getBaseURL } from '/@/utils/baseUrl';
import { Session } from '/@/utils/storage';
import { request } from '/@/utils/service';

let tabsDrawer = ref(false);
let contentDrawer = ref(false);
let editableTabsValue = ref('base');
let editableTabs: any = ref([]);
let formList = ref<any[]>([]);
let formData = ref<any>({});
let searchQuery = ref('');
let editingItem = ref<any>(null);
let editingValue = ref<any>('');
let dictOptions = ref<any[]>([]); // 字典选项

const { t } = useI18n();
const { themeConfig } = storeToRefs(useThemeConfig(pinia));

// 获取标签类型
const getTagType = (type: string) => {
	const typeMap: any = {
		'switch': 'success',
		'select': 'warning',
		'radio': 'primary',
		'checkbox': 'info',
		'text': 'info',
		'textarea': 'info',
		'number': 'danger',
		'img': 'warning',
		'imgs': 'warning',
	};
	return typeMap[type] || 'info';  // 默认使用 info,避免空字符串
};

// 获取类型标签
const getLabel = (type: string) => {
	const labelMap: any = {
		'text': '文本',
		'textarea': '长文本',
		'number': '数字',
		'date': '日期',
		'time': '时间',
		'datetime': '日期时间',
		'select': '下拉',
		'checkbox': '多选',
		'radio': '单选',
		'switch': '开关',
		'img': '图片',
		'imgs': '多图片',
		'array': '数组',
		'file': '文件',
	};
	return labelMap[type] || type;
};

// 解析校验规则
const parseRules = (rule: any) => {
	if (!rule) return [];
	try {
		// rule 可能是字符串、数组或对象
		if (typeof rule === 'string') {
			return [JSON.parse(rule)];
		}
		if (Array.isArray(rule)) {
			// 数组中的元素可能是字符串或对象
			return rule.map(item => {
				if (typeof item === 'string') {
					return JSON.parse(item);
				}
				return item;
			});
		}
		// 如果是对象，直接包装成数组
		if (typeof rule === 'object') {
			return [rule];
		}
		return [rule];
	} catch (e) {
		console.error('[parseRules] 解析失败:', e);
		return [];
	}
};

// ==================== 图片上传相关 ====================
// 上传组件引用
const uploadRef = ref<any>(null);

// 文件上传组件引用
const fileUploadRef = ref<HTMLInputElement | null>(null);

// 触发上传（点击图片时调用）
const triggerUpload = () => {
	console.log('[triggerUpload] 开始触发上传');
	console.log('[triggerUpload] uploadRef.value:', uploadRef.value);
	
	if (uploadRef.value) {
		try {
			// uploadRef.value 可能是一个数组或对象，需要获取实际的 DOM 元素
			let inputElement: HTMLElement | null = null;
			
			// 如果是数组，取第一个元素
			if (Array.isArray(uploadRef.value)) {
				inputElement = uploadRef.value[0];
			} else if (uploadRef.value.$el) {
				// 如果是组件实例，获取 $el
				inputElement = uploadRef.value.$el;
			} else {
				// 直接使用
				inputElement = uploadRef.value as HTMLElement;
			}
			
			console.log('[triggerUpload] inputElement:', inputElement);
			
			// 确保是 input 元素且类型为 file
			if (inputElement && inputElement.tagName === 'INPUT' && (inputElement as HTMLInputElement).type === 'file') {
				console.log('[triggerUpload] 点击 file input');
				(inputElement as HTMLInputElement).click();
			} else {
				console.error('[triggerUpload] 不是有效的 file input 元素');
				ElMessage.error('无法触发文件选择，请刷新页面重试');
			}
		} catch (error) {
			console.error('[triggerUpload] 触发上传失败:', error);
			ElMessage.error('触发上传失败，请重试');
		}
	} else {
		console.error('[triggerUpload] uploadRef.value 为空');
	}
};

// 处理文件选择
const handleFileChange = async (event: Event) => {
	const target = event.target as HTMLInputElement;
	const file = target.files?.[0];
	
	if (!file) return;
	
	// 验证文件类型
	if (!file.type.startsWith('image/')) {
		ElMessage.error(t('message.pages.config.messages.invalidFileType'));
		return;
	}
	
	// 验证文件大小（限制为5MB）
	if (file.size > 5 * 1024 * 1024) {
		ElMessage.error(t('message.pages.config.messages.fileTooLarge'));
		return;
	}
	
	try {
		// 创建 FormData
		const formData = new FormData();
		formData.append('file', file);
		
		// 发送上传请求
		const response = await fetch(uploadUrl.value, {
			method: 'POST',
			headers: uploadHeaders.value,
			body: formData
		});
		
		const result = await response.json();
		
		if (result.code === 2000 && result.data?.url) {
			const fullUrl = getBaseURL() + result.data.url;
			editingValue.value = fullUrl;
			ElMessage.success(t('message.pages.config.messages.uploadSuccess'));
		} else {
			ElMessage.error(result.msg || t('message.pages.config.messages.uploadFailed'));
		}
	} catch (error) {
		console.error('上传失败:', error);
		ElMessage.error(t('message.pages.config.messages.uploadFailed'));
	} finally {
		// 清空 input，允许重复选择同一文件
		if (target) {
			target.value = '';
		}
	}
};

// ==================== 文件上传相关 ====================
// 触发文件上传（点击文件时调用）
const triggerFileUpload = () => {
	console.log('[triggerFileUpload] 开始触发文件上传');
	console.log('[triggerFileUpload] fileUploadRef.value:', fileUploadRef.value);
	
	if (fileUploadRef.value) {
		try {
			// fileUploadRef.value 可能是一个数组或对象，需要获取实际的 DOM 元素
			let inputElement: HTMLElement | null = null;
			
			// 如果是数组，取第一个元素
			if (Array.isArray(fileUploadRef.value)) {
				inputElement = fileUploadRef.value[0];
			} else if (fileUploadRef.value.$el) {
				// 如果是组件实例，获取 $el
				inputElement = fileUploadRef.value.$el;
			} else {
				// 直接使用
				inputElement = fileUploadRef.value as HTMLElement;
			}
			
			console.log('[triggerFileUpload] inputElement:', inputElement);
			
			// 确保是 input 元素且类型为 file
			if (inputElement && inputElement.tagName === 'INPUT' && (inputElement as HTMLInputElement).type === 'file') {
				console.log('[triggerFileUpload] 点击 file input');
				(inputElement as HTMLInputElement).click();
			} else {
				console.error('[triggerFileUpload] 不是有效的 file input 元素');
				ElMessage.error('无法触发文件选择，请刷新页面重试');
			}
		} catch (error) {
			console.error('[triggerFileUpload] 触发文件上传失败:', error);
			ElMessage.error('触发文件上传失败，请重试');
		}
	} else {
		console.error('[triggerFileUpload] fileUploadRef.value 为空');
	}
};

// 处理文件上传
const handleFileUploadChange = async (event: Event) => {
	const target = event.target as HTMLInputElement;
	const file = target.files?.[0];
	
	if (!file) return;
	
	// 验证文件大小（限制为50MB）
	if (file.size > 50 * 1024 * 1024) {
		ElMessage.error(t('message.pages.config.messages.fileTooLarge'));
		return;
	}
	
	try {
		// 创建 FormData
		const formData = new FormData();
		formData.append('file', file);
		
		// 发送上传请求
		const response = await fetch(uploadUrl.value, {
			method: 'POST',
			headers: uploadHeaders.value,
			body: formData
		});
		
		const result = await response.json();
		
		if (result.code === 2000 && result.data?.url) {
			const fullUrl = getBaseURL() + result.data.url;
			editingValue.value = fullUrl;
			ElMessage.success(t('message.pages.config.messages.uploadSuccess'));
		} else {
			ElMessage.error(result.msg || t('message.pages.config.messages.uploadFailed'));
		}
	} catch (error) {
		console.error('文件上传失败:', error);
		ElMessage.error(t('message.pages.config.messages.uploadFailed'));
	} finally {
		// 清空 input，允许重复选择同一文件
		if (target) {
			target.value = '';
		}
	}
};

// 获取文件名
const getFileName = (url: string) => {
	if (!url) return '未知文件';
	// 提取 URL 中的文件名
	const parts = url.split('/');
	return parts[parts.length - 1] || '未知文件';
};

// 上传URL
const uploadUrl = computed(() => getBaseURL() + 'api/system/file/');

// 上传请求头
const uploadHeaders = computed(() => ({
	Authorization: 'JWT ' + Session.get('token'),
}));

// 获取完整的图片URL（处理相对路径）
const getFullImageUrl = (url: string) => {
	if (!url) return '';
	
	// 如果已经是完整URL（包含 http:// 或 https://），直接返回
	if (url.startsWith('http://') || url.startsWith('https://')) {
		return url;
	}
	
	// 如果是相对路径（以 / 开头），添加base URL
	if (url.startsWith('/')) {
		return getBaseURL() + url;
	}
	
	// 其他情况（可能是文件名或其他格式），也添加base URL
	return getBaseURL() + url;
};

// 图片加载错误处理
const handleImageError = (event: Event) => {
	const img = event.target as HTMLImageElement;
	if (img) {
		img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjVmNWY1Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuaXoOWvhua6kOivgeS4lueggTwvdGV4dD48L3N2Zz4=';
	}
};

// ==================== 图片预览相关 ====================
// 图片预览状态
const showImagePreview = ref(false);
const previewSrcList = ref<string[]>([]);
const previewInitialIndex = ref(0);

// 图片预览处理
const handleImagePreview = (srcList: string[], initialIndex?: number) => {
	previewSrcList.value = srcList;
	previewInitialIndex.value = initialIndex || 0;
	showImagePreview.value = true;
};

// 上传成功处理
const handleUploadSuccess = (response: any, type: 'single' | 'multiple') => {
	const { code, data } = response;
	if (code === 2000 && data?.url) {
		const fullUrl = getBaseURL() + data.url;
		
		if (type === 'single') {
			// 单张图片：直接替换
			editingValue.value = fullUrl;
		} else if (type === 'multiple') {
			// 多张图片：添加到数组
			if (!Array.isArray(editingValue.value)) {
				editingValue.value = [];
			}
			editingValue.value.push(fullUrl);
		}
		ElMessage.success(t('message.pages.config.messages.uploadSuccess'));
	} else {
		ElMessage.error(t('message.pages.config.messages.uploadFailed'));
	}
};

// 上传失败处理
const handleUploadError = () => {
	ElMessage.error(t('message.pages.config.messages.uploadFailed'));
};

// 获取校验规则标签
const getRuleLabel = (rule: any) => {
	if (!rule) return '';
	if (rule.required) return '必填';
	if (rule.type === 'email') return '邮箱';
	if (rule.type === 'url') return 'URL';
	return '校验';
};

// 字典选项缓存
const dictOptionsCache = ref<Record<string, any[]>>({});

// 显示值
const displayValue = (item: any) => {
	const value = formData.value[item.key];
	if (value === null || value === undefined) return '-';
	
	// 对于下拉、单选、多选类型，需要根据字典选项转换
	if (['下拉', '单选', '多选'].includes(item.form_item_type_label)) {
		// 优先使用缓存中的字典选项
		let options = dictOptionsCache.value[item.setting] || item.data_options;
		
		// 如果是数组（多选），需要转换每个值
		if (Array.isArray(value)) {
			return value.map(v => {
				// 尝试从 options 中查找对应的标签
				if (options && Array.isArray(options)) {
					const option = options.find((opt: any) => opt.value === v);
					return option ? (option.label || opt.name || v) : v;
				}
				return v;
			}).join(', ');
		}
		// 单个值（下拉、单选）
		if (options && Array.isArray(options)) {
			const option = options.find((opt: any) => opt.value === value);
			return option ? (option.label || opt.name || value) : String(value);
		}
	}
	
	if (Array.isArray(value)) return value.join(', ');
	return String(value);
};

// 过滤后的配置列表
const filteredFormList = computed(() => {
	if (!searchQuery.value) return formList.value;
	const query = searchQuery.value.toLowerCase();
	return formList.value.filter(item => 
		(item.title_i18n || item.title).toLowerCase().includes(query) ||
		item.key.toLowerCase().includes(query)
	);
});

// 获取配置列表
const getFormList = async () => {
	const res: any = await api.GetDetail(editableTabsValue.value, themeConfig.value.globalI18n);
	formList.value = res.data || [];
	formData.value = {};
	formList.value.forEach(item => {
		formData.value[item.key] = item.value;
	});
	
	// 为下拉/单选/多选类型的配置项预加载字典选项
	for (const item of formList.value) {
		if (['下拉', '单选', '多选'].includes(item.form_item_type_label) && item.setting && !item.data_options) {
			// 如果缓存中没有，则从API加载
			if (!dictOptionsCache.value[item.setting]) {
				try {
					const dictRes: any = await request({
						url: '/api/init/dictionary/',
						method: 'get',
						params: {
							dictionary_key: item.setting,
						},
					});
					dictOptionsCache.value[item.setting] = dictRes.data || [];
					console.log(`[getFormList] 加载字典选项 ${item.setting}:`, dictRes.data);
				} catch (error) {
					console.error(`加载字典选项 ${item.setting} 失败:`, error);
				}
			}
		}
	}
};

// 获取Tab列表
const getTabs = () => {
	api
		.GetList({
			limit: 999,
			parent__isnull: true,
			language: themeConfig.value.globalI18n,
		})
		.then((res: any) => {
			let data = res.data;
			editableTabs.value = data;
			if (data.length > 0 && !editableTabsValue.value) {
				editableTabsValue.value = data[0].key;
			}
			getFormList();
		});
};

// 处理配置变更
const handleConfigChange = async (item: any) => {
	try {
		await api.UpdateObj({
			id: item.id,
			value: formData.value[item.key]
		});
		ElMessage.success(t('message.pages.config.messages.updateSuccess'));
	} catch (error) {
		// 重新获取数据以恢复原值
		getFormList();
		ElMessage.error(t('message.pages.config.messages.updateFailed'));
	}
};

// 编辑配置
const handleEdit = (item: any) => {
	// 对文本、长文本、数字、日期、时间、日期时间类型进行内联编辑
	const inlineEditTypes = ['文本', '长文本', '数字', '日期', '时间', '日期时间'];
	if (inlineEditTypes.includes(item.form_item_type_label)) {
		editingItem.value = item;
		editingValue.value = formData.value[item.key] !== null && formData.value[item.key] !== undefined ? String(formData.value[item.key]) : '';
	}	
	// 下拉、单选、多选类型也需要内联编辑
	else if (['下拉', '单选', '多选'].includes(item.form_item_type_label)) {
		editingItem.value = item;
		// 这些类型的值可能是数组或字符串
		if (Array.isArray(formData.value[item.key])) {
			editingValue.value = formData.value[item.key];
		} else {
			editingValue.value = formData.value[item.key] !== null && formData.value[item.key] !== undefined ? String(formData.value[item.key]) : '';
		}
		// 加载字典选项
		loadDictOptions(item);
	}
	else if (['图片(单张)', '图片(多张)', '文件', '文件附件', '数组'].includes(item.form_item_type_label)) {
		editingItem.value = item;
		// 图片/文件/数组类型的值可能是字符串或数组
		if (item.form_item_type_label === '图片(多张)' || item.form_item_type_label === '文件附件' || item.form_item_type_label === '数组') {
			editingValue.value = formData.value[item.key] !== null && formData.value[item.key] !== undefined ? formData.value[item.key] : [];
			if (typeof editingValue.value === 'string' && editingValue.value) {
				try {
					editingValue.value = JSON.parse(editingValue.value);
				} catch (e) {
					editingValue.value = [editingValue.value];
				}
			}
			if (!Array.isArray(editingValue.value)) {
				editingValue.value = [];
			}
		} else {
			editingValue.value = formData.value[item.key] !== null && formData.value[item.key] !== undefined ? String(formData.value[item.key]) : '';
		}
	}
	else {
		// 其他类型打开抽屉编辑
		contentDrawer.value = true;
		// TODO: 传递编辑参数
	}
};

// 加载字典选项
const loadDictOptions = async (item: any) => {
	if (!item.setting) {
		dictOptions.value = [];
		return;
	}
	try {
		// setting 是字典的 value，使用专用的初始化接口
		const res: any = await request({
			url: '/api/init/dictionary/',
			method: 'get',
			params: {
				dictionary_key: item.setting,
			},
		});
		dictOptions.value = res.data || [];
	} catch (error) {
		console.error('加载字典选项失败:', error);
		dictOptions.value = [];
	}
};

// 确认编辑
const handleConfirmEdit = async (item: any) => {
	try {
		// 检查是否有校验规则
		if (item.rule && Array.isArray(item.rule)) {
			const rules = parseRules(item.rule);
			
			// 1. 验证必填项
			const hasRequiredRule = rules.some((rule: any) => rule.required === true);
			if (hasRequiredRule) {
				// 验证值是否为空
				if (editingValue.value === null || editingValue.value === undefined || editingValue.value === '') {
					ElMessage.error('该字段为必填项，请填写');
					return;
				}
				// 对于数组类型（图片(多张)、文件附件、数组），检查数组是否为空
				if (['图片(多张)', '文件附件', '数组'].includes(item.form_item_type_label)) {
					let arrayValue: any = editingValue.value;
					if (typeof arrayValue === 'string' && arrayValue) {
						try {
							arrayValue = JSON.parse(arrayValue);
						} catch (e) {
							arrayValue = [arrayValue];
						}
					}
					if (!Array.isArray(arrayValue) || arrayValue.length === 0) {
						ElMessage.error('该字段为必填项，请至少上传一个文件/图片');
						return;
					}
				}
			}
			
			// 2. 验证邮箱格式
			const hasEmailRule = rules.some((rule: any) => rule.type === 'email');
			if (hasEmailRule && editingValue.value) {
				const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
				if (!emailRegex.test(editingValue.value)) {
					ElMessage.error('请输入正确的邮箱地址');
					return;
				}
			}
			
			// 3. 验证URL格式
			const hasUrlRule = rules.some((rule: any) => rule.type === 'url');
			if (hasUrlRule && editingValue.value) {
				const urlRegex = /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/;
				if (!urlRegex.test(editingValue.value)) {
					ElMessage.error('请输入正确的URL地址');
					return;
				}
			}
		}
		
		// 数字类型需要转换为数字
		let valueToSave: any = editingValue.value;
		if (item.form_item_type_label === 'number') {
			if (editingValue.value === '' || editingValue.value === null || editingValue.value === undefined) {
				valueToSave = null;
			} else {
				const numValue = Number(editingValue.value);
				if (isNaN(numValue)) {
					ElMessage.error('请输入有效的数字');
					return;
				}
				valueToSave = numValue;
			}
		}
		// 图片/文件/数组类型 - JSONField 可以直接保存数组对象
		else if (item.form_item_type_label === '图片(多张)' || item.form_item_type_label === '文件附件' || item.form_item_type_label === '数组') {
			// 如果是字符串，尝试解析为数组
			if (typeof editingValue.value === 'string' && editingValue.value) {
				try {
					valueToSave = JSON.parse(editingValue.value);
				} catch (e) {
					valueToSave = [editingValue.value];
				}
			} else if (Array.isArray(editingValue.value)) {
				valueToSave = editingValue.value;
			} else {
				valueToSave = [];
			}
		}
			
		await api.UpdateObj({
			id: item.id,
			value: valueToSave
		});
		// 更新本地状态
		formData.value[item.key] = valueToSave;
		ElMessage.success(t('message.pages.config.messages.updateSuccess'));
		// 清除编辑状态
		editingItem.value = null;
		editingValue.value = '';
		dictOptions.value = [];
		// 重新加载配置数据以刷新卡片显示
		getFormList();
	} catch (error) {
		console.error('[handleConfirmEdit] 更新失败:', error);
		// 尝试获取详细的错误信息
		let errorMsg = t('message.pages.config.messages.updateFailed');
		if (error && typeof error === 'object') {
			if (error.response) {
				const { data, status } = error.response;
				console.error('[handleConfirmEdit] 响应状态:', status);
				console.error('[handleConfirmEdit] 响应数据:', data);
				if (data && data.msg) {
					errorMsg = data.msg;
				} else if (data && data.detail) {
					errorMsg = data.detail;
				}
			} else if (error.message) {
				errorMsg = error.message;
			}
		}
		ElMessage.error(errorMsg);
	}
};

// 取消编辑
const handleCancelEdit = () => {
	editingItem.value = null;
	editingValue.value = '';
	dictOptions.value = [];
};

// 数字输入处理
const handleNumberInput = (item: any) => {
	if (item.form_item_type_label === '数字') {
		let value = editingValue.value;
		// 只允许输入数字、小数点、负号
		value = value.replace(/[^0-9.-]/g, '');
		// 确保只有一个小数点
		const parts = value.split('.');
		if (parts.length > 2) {
			value = parts[0] + '.' + parts.slice(1).join('');
		}
		// 确保负号只在开头
		const hasMinus = value.startsWith('-');
		value = value.replace(/-/g, '');
		if (hasMinus) {
			value = '-' + value;
		}
		// 确保只有一个负号
		if (value.indexOf('-') !== value.lastIndexOf('-')) {
			value = value.replace(/-/g, '');
			if (value.charAt(0) === '-') {
				value = '-' + value.substring(1);
			}
		}
		editingValue.value = value;
	}
};

// 删除配置
const handleDelete = (item: any) => {
	ElMessageBox.confirm(
		t('message.pages.config.messages.deleteConfirm'),
		t('message.pages.config.buttons.delete'),
		{
			confirmButtonText: t('message.pages.config.buttons.confirm'),
			cancelButtonText: t('message.pages.config.buttons.cancel'),
			type: 'warning',
		}
	).then(async () => {
		try {
			await api.DelObj(item.id);
			ElMessage.success(t('message.pages.config.messages.deleteSuccess'));
			getFormList();
		} catch (error) {
			ElMessage.error(t('message.pages.config.messages.deleteFailed'));
		}
	}).catch(() => {});
};

// Tab添加成功
const handleTabsSuccess = () => {
	tabsDrawer.value = false;
	getTabs();
};

// 内容添加成功
const handleContentSuccess = () => {
	contentDrawer.value = false;
	getFormList();
};

// 删除当前分组
const handleDeleteGroup = () => {
	ElMessageBox.confirm(
		t('message.pages.config.messages.deleteGroupConfirm'),
		t('message.pages.config.buttons.deleteGroup'),
		{
			confirmButtonText: t('message.pages.config.buttons.confirm'),
			cancelButtonText: t('message.pages.config.buttons.cancel'),
			type: 'warning',
		}
	).then(async () => {
		try {
			// 查找当前分组的ID
			const currentGroup = editableTabs.value.find((tab: any) => tab.key === editableTabsValue.value);
			if (!currentGroup) {
				ElMessage.error(t('message.pages.config.messages.groupNotFound'));
				return;
			}
			
			await api.DelObj(currentGroup.id);
			ElMessage.success(t('message.pages.config.messages.deleteGroupSuccess'));
			
			// 重新获取分组列表
			await getTabs();
			
			// 如果分组列表不为空,切换到第一个分组
			if (editableTabs.value.length > 0) {
				editableTabsValue.value = editableTabs.value[0].key;
			}
		} catch (error) {
			ElMessage.error(t('message.pages.config.messages.deleteGroupFailed'));
		}
	}).catch(() => {});
};

onMounted(() => {
	getTabs();
});

// 语言切换时刷新
watch(
	() => themeConfig.value.globalI18n,
	() => {
		getTabs();
	}
);

// Tab切换时刷新配置列表
watch(editableTabsValue, () => {
	getFormList();
});
</script>

<style scoped>
.container {
	max-width: 100%;
	margin: 0 auto;
	padding: 20px;
}

header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 30px;
}

.buttons-group {
	display: flex;
	align-items: center;
	gap: 12px;
}

.search-box {
	width: 300px;
}

.filters {
	display: flex;
	gap: 12px;
	margin-bottom: 25px;
	flex-wrap: wrap;
}

.filter-btn {
	padding: 8px 20px;
	border-radius: 20px;
	transition: all 0.3s ease;
}

.config-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
	gap: 25px;
}

.config-card {
	background: var(--el-bg-color);
	border-radius: 12px;
	overflow: hidden;
	box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
	transition: transform 0.3s ease, box-shadow 0.3s ease;
	border: 1px solid var(--el-border-color-lighter);
	display: flex;
	flex-direction: column;
}

.config-card:hover {
	transform: translateY(-5px);
	box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
}

.card-header {
	padding: 20px;
	border-bottom: 1px solid var(--el-border-color-lighter);
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.card-tags {
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: wrap;
	justify-content: flex-end;
}

.rule-tag {
	margin-left: 4px;
}

.card-title {
	font-size: 18px;
	font-weight: 600;
	color: var(--el-text-color-primary);
}

.card-subtitle {
	font-size: 13px;
	color: var(--el-text-color-secondary);
	margin-top: 6px;
}

.card-content {
	padding: 20px;
	padding-bottom: 0;
	flex: 1;
}

.card-meta {
	display: flex;
	align-items: center;
	color: var(--el-text-color-secondary);
	font-size: 14px;
	margin-bottom: 15px;
	gap: 6px;
}

.meta-key {
	font-family: 'Courier New', monospace;
	background: var(--el-fill-color);
	padding: 2px 8px;
	border-radius: 4px;
	font-size: 13px;
}

.card-value {
	color: var(--el-text-color-regular);
	line-height: 1.6;
	min-height: 40px;
	display: flex;
	align-items: center;
}

.switch-value {
	display: flex;
	align-items: center;
}

.text-value {
	word-break: break-all;
}

/* 图片查看模式样式 */
.image-view-mode {
	width: 100%;
}

.single-image-preview {
	width: 50px;
	height: 50px;
	min-width: 50px;
	border-radius: 6px;
	overflow: hidden;
	border: 1px solid var(--el-border-color-lighter);
	background-color: var(--el-fill-color-lighter);
	display: flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	transition: all 0.3s ease;
	position: relative;
}

.single-image-preview:hover {
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	transform: scale(1.05);
}

.single-image-preview img {
	width: 100%;
	height: 100%;
	display: block;
	object-fit: contain;
}

.multiple-images-preview {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
}

.thumb-item {
	width: 40px;
	height: 40px;
	min-width: 40px;
	border-radius: 4px;
	overflow: hidden;
	border: 1px solid var(--el-border-color-lighter);
	background-color: var(--el-fill-color-lighter);
	display: flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	transition: all 0.3s ease;
	position: relative;
}

.thumb-item:hover {
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	transform: scale(1.1);
}

.thumb-item img {
	width: 100%;
	height: 100%;
	object-fit: cover;
}

.preview-icon {
	position: absolute;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background: rgba(0, 0, 0, 0.3);
	display: flex;
	align-items: center;
	justify-content: center;
	color: white;
	font-size: 16px;
	opacity: 0;
	transition: opacity 0.3s ease;
}

.single-image-preview:hover .preview-icon,
.thumb-item:hover .preview-icon {
	opacity: 1;
}

.empty-text {
	color: var(--el-text-color-secondary);
	font-style: italic;
}

/* 编辑模式样式 */
.edit-mode {
	width: 100%;
}

.edit-mode :deep(.el-input__wrapper) {
	box-shadow: 0 0 0 1px var(--el-color-primary) inset;
}

/* 上传组件样式 */
/* 单张图片编辑模式 - 上传组件 50x50 */
.image-single-edit :deep(.el-upload--picture-card) {
	width: 50px;
	height: 50px;
	line-height: 50px;
}

.image-single-edit :deep(.el-upload-list--picture-card .el-upload-list__item) {
	width: 50px;
	height: 50px;
}

/* 多张图片编辑模式 - 上传组件保持默认大小 */
.image-list :deep(.el-upload--picture-card) {
	width: 100px;
	height: 100px;
	line-height: 100px;
}

.image-list :deep(.el-upload-list--picture-card .el-upload-list__item) {
	width: 100px;
	height: 100px;
}

.url-input-section {
	margin-top: 8px;
}

.url-input-section :deep(.el-divider__text) {
	font-size: 12px;
	color: var(--el-text-color-secondary);
}

/* ElImageViewer 样式覆盖 */
:deep(.el-image-viewer__wrapper) {
	z-index: 9999 !important;
}

:deep(.el-image-viewer__mask) {
	background-color: rgba(0, 0, 0, 0.8) !important;
}

/* 图片和文件列表样式 */
.image-single-edit {
	width: 100%;
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.image-preview {
	width: 50px;
	height: 50px;
	min-width: 50px;
	border-radius: 6px;
	overflow: hidden;
	border: 1px solid var(--el-border-color-lighter);
	background-color: var(--el-fill-color-lighter);
	display: flex;
	align-items: center;
	justify-content: center;
}

.image-preview img {
	width: 100%;
	height: 100%;
	display: block;
	object-fit: contain;
}

/* 单张图片编辑模式 - 图片预览包装器 */
.image-preview-wrapper {
	width: 50px;
	height: 50px;
	min-width: 50px;
	border-radius: 6px;
	overflow: hidden;
	border: 1px solid var(--el-border-color-lighter);
	background-color: var(--el-fill-color-lighter);
	display: flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	transition: all 0.3s ease;
	position: relative;
}

.image-preview-wrapper:hover {
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	transform: scale(1.05);
}

.image-preview-wrapper img {
	width: 100%;
	height: 100%;
	display: block;
	object-fit: contain;
}

/* 替换图层 */
.replace-overlay {
	position: absolute;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background: rgba(0, 0, 0, 0.5);
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	color: white;
	opacity: 0;
	transition: opacity 0.3s ease;
	z-index: 10;
}

.image-preview-wrapper:hover .replace-overlay {
	opacity: 1;
}

.replace-overlay .el-icon {
	font-size: 18px;
	margin-bottom: 4px;
}

.replace-overlay span {
	font-size: 12px;
	text-align: center;
	padding: 0 4px;
	line-height: 1.2;
	word-break: keep-all;
}

.image-thumb {
	width: 60px;
	height: 60px;
	min-width: 60px;
	border-radius: 4px;
	overflow: hidden;
	border: 1px solid var(--el-border-color-lighter);
	background-color: var(--el-fill-color-lighter);
	display: flex;
	align-items: center;
	justify-content: center;
}

.image-thumb img {
	width: 100%;
	height: 100%;
	object-fit: cover;
}

/* 单文件编辑模式 - 文件预览包装器 */
.file-preview-wrapper {
	width: 200px;
	min-height: 80px;
	border-radius: 6px;
	overflow: hidden;
	border: 1px solid var(--el-border-color-lighter);
	background-color: var(--el-fill-color-lighter);
	display: flex;
	align-items: center;
	padding: 12px;
	cursor: pointer;
	transition: all 0.3s ease;
	position: relative;
}

.file-preview-wrapper:hover {
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	transform: scale(1.02);
}

/* 文件上传按钮（无文件时显示） */
.file-upload-button {
	width: 200px;
	height: 80px;
	border-radius: 6px;
	border: 2px dashed var(--el-border-color-lighter);
	background-color: var(--el-fill-color-lighter);
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	transition: all 0.3s ease;
	color: var(--el-text-color-secondary);
}

.file-upload-button:hover {
	border-color: var(--el-color-primary);
	color: var(--el-color-primary);
	background-color: var(--el-color-primary-light-9);
}

.file-icon {
	width: 40px;
	height: 40px;
	border-radius: 6px;
	background-color: var(--el-color-primary-light-9);
	display: flex;
	align-items: center;
	justify-content: center;
	color: var(--el-color-primary);
	font-size: 20px;
	margin-right: 12px;
}

.file-info {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 4px;
	overflow: hidden;
}

.file-name {
	font-size: 14px;
	font-weight: 500;
	color: var(--el-text-color-primary);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.file-url {
	font-size: 12px;
	color: var(--el-text-color-secondary);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

/* 单文件查看模式 */
.single-file-preview {
	width: 100%;
}

.file-display {
	display: flex;
	align-items: center;
	padding: 12px 16px;
	border-radius: 8px;
	background-color: var(--el-fill-color-lighter);
	border: 1px solid var(--el-border-color-lighter);
}

.file-icon-large {
	width: 40px;
	height: 40px;
	border-radius: 8px;
	background-color: var(--el-color-primary-light-9);
	display: flex;
	align-items: center;
	justify-content: center;
	color: var(--el-color-primary);
	font-size: 20px;
	margin-right: 12px;
}

.file-details {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.file-link {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	color: var(--el-color-primary);
	text-decoration: none;
	font-size: 14px;
	transition: color 0.3s ease;
}

.file-link:hover {
	color: var(--el-color-primary-dark-2);
	text-decoration: underline;
}

/* 文件列表显示 */
.file-list-display {
	width: 100%;
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.file-item-display {
	display: flex;
	align-items: center;
	padding: 12px;
	border-radius: 6px;
	background-color: var(--el-fill-color-lighter);
	border: 1px solid var(--el-border-color-lighter);
}

.file-icon-small {
	width: 32px;
	height: 32px;
	border-radius: 4px;
	background-color: var(--el-color-primary-light-9);
	display: flex;
	align-items: center;
	justify-content: center;
	color: var(--el-color-primary);
	font-size: 16px;
	margin-right: 12px;
}

.file-info-display {
	flex: 1;
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
}

.file-info-display .file-name {
	flex: 1;
	font-size: 14px;
	color: var(--el-text-color-primary);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.file-info-display .file-link {
	font-size: 13px;
}

.edit-tips {
	font-size: 12px;
	color: var(--el-text-color-secondary);
	line-height: 1.5;
}

.image-list,
.file-list,
.array-list {
	width: 100%;
	display: flex;
	flex-direction: column;
	gap: 10px;
}

.image-item,
.file-item,
.array-item {
	display: flex;
	gap: 10px;
	align-items: center;
}

.image-item .el-input,
.file-item .el-input,
.array-item .el-input {
	flex: 1;
}

/* 额外信息展示区 */
.card-extra-info {
	margin-top: 12px;
}

.info-row {
	display: flex;
	align-items: center;
	gap: 8px;
	margin-bottom: 8px;
	font-size: 13px;
}

.info-row:last-child {
	margin-bottom: 0;
}

.info-label {
	color: var(--el-text-color-secondary);
	font-weight: 500;
	min-width: 40px;
}

.info-value {
	color: var(--el-text-color-regular);
	flex: 1;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.rule-tags {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
	flex: 1;
}

.card-footer {
	padding: 15px 20px;
	background: var(--el-fill-color-lighter);
	display: flex;
	justify-content: flex-end;
	align-items: center;
}

.actions {
	display: flex;
	gap: 12px;
}

@media (max-width: 768px) {
	.config-grid {
		grid-template-columns: 1fr;
	}

	header {
		flex-direction: column;
		align-items: flex-start;
	}

	.search-box {
		width: 100%;
	}

	.filters {
		width: 100%;
	}
}
</style>

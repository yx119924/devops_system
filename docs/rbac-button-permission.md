# RBAC 按钮权限与「只读角色按钮隐藏」实现说明

> 本文说明 XwOps 业务 CRUD 页面如何做到「普通运维(ops) 可见增删改按钮、只读查看(readonly) 隐藏增删改按钮」，并记录一处**必须的框架层补丁**。

## 一、后端：三层权限模型

DVAdmin3 的权限是三层：

| 层 | 模型 | 作用 |
| -- | ---- | ---- |
| 菜单可见 | `RoleMenuPermission` | 用户 `role` M2M → 菜单是否显示 |
| 接口访问 | `RoleMenuButtonPermission` | `CustomPermission` 按「API 路径 + HTTP 方法」匹配 `MenuButton.api` + `MenuButton.method` |
| 前端按钮显隐 | `BtnPermissionStore` | 读 `user.current_role`（FK），非 `role` M2M |

业务 CRUD 页（继承 `CustomModelViewSet`）**必须注册 `MenuButton`**，否则非 superuser 访问增删改接口会被拒（前端红框提示）。注册脚本：

```bash
docker exec dvadmin3-django python register_business_buttons.py    # 幂等，可重复执行
```

该脚本同时创建两个标准角色：`ops`（普通运维，含全部按钮）、`readonly`（只读查看，仅 GET 类按钮：查询/查看/列表/测试）。

## 二、前端：按钮显隐（业务视图内，已在本仓库）

每个业务 `crud.tsx` 统一用以下模式（以 `server` 为例）：

```tsx
import { ..., compute } from '@fast-crud/fast-crud';
import { BtnPermissionStore } from '/@/plugin/permission/store.permission';

const btnStore = BtnPermissionStore();
const hasAuth = (code: string) => (btnStore.data || []).includes(code);

// actionbar 的「添加」：必须用 eager boolean（不能用 compute，见下方说明）
actionbar: { buttons: { add: { show: hasAuth('server:Create') } } },

// rowHandle 的「编辑/删除」：用 compute()（fs-row-handle.vue 内部走 doComputed 解析）
rowHandle: {
  buttons: {
    edit:   { show: compute(() => hasAuth('server:Update')) },
    remove: { show: compute(() => hasAuth('server:Delete')) },
    // 自定义按钮（如「终端」）保持 show: true
  },
},
```

**关键结论（fast-crud 1.21.2 源码验证）**：

- `actionbar/index.vue` 只做 `value.show !== false` 判断，**不解析 `compute()`**，故 actionbar 的 `show` 必须传 eager boolean，否则 `compute()` 对象恒为 truthy 导致按钮永远显示。
- `fs-row-handle.vue` 通过 `doComputed()` 解析 `ComputeValue`，故 rowHandle 可用 `compute()`。
- 普通函数/`{row: fn}` 形式会被当作 truthy（永远显示），不要用。

## 三、框架层补丁（必须，不在本仓库）

`frontend/` 只包含 XwOps 业务视图，**DVAdmin3 框架代码不在此仓库**。但以下两处框架文件需补丁，否则 actionbar 的 eager boolean 会在首屏因异步竞态误判（按钮权限 store 尚未加载完成时 `hasAuth()` 返回 false，导致 ops 的「添加」被隐藏）：

### 1. `web/src/plugin/permission/store.permission.ts`

`getBtnPermissionStore()` 声明了 `async` 但内部用 `.then()` 且不 `return`/`await`，导致函数体同步返回、`await` 它不会等 HTTP 完成。改为真正 `await`：

```diff
         async getBtnPermissionStore() {
-            request({
-                url: '/api/system/menu_button/menu_button_all_permission/',
-                method: 'get',
-            }).then((ret: {
-                data: []
-            }) => {
-                // 转换数据格式并保存到pinia
-                let dataList = ret.data
-                this.data=dataList
-            })
+            const ret: any = await request({
+                url: '/api/system/menu_button/menu_button_all_permission/',
+                method: 'get',
+            });
+            // 转换数据格式并保存到pinia
+            let dataList = ret.data
+            this.data=dataList
         },
```

### 2. `web/src/router/backEnd.ts`

`getBackEndControlRoutes()` 原为 fire-and-forget 调用按钮权限 store，改为 `async` + `await`，确保路由挂载前权限已就绪：

```diff
-export function getBackEndControlRoutes() {
+export async function getBackEndControlRoutes() {
 	//获取所有的按钮权限
-	BtnPermissionStore().getBtnPermissionStore();
+	await BtnPermissionStore().getBtnPermissionStore();
```

> 打补丁后需重建 `dvadmin3-web` 镜像：`docker compose build dvadmin3-web && docker compose up -d dvadmin3-web`。

## 四、验证

- 后端：`readonly` 角色仅有 GET 类按钮（23 个，无任何 `:Create`）；`ops` 含全部按钮。
- 前端 E2E：`deploy/test_vauth_e2e.py`（Playwright）对比 ops/readonly 两账号在 10 个业务页的按钮显隐，全部通过后输出 `E2E ALL PASS`。

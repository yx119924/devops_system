import {defineStore} from "pinia";
import {DictionaryStates} from "/@/stores/interface";
import {request} from "/@/utils/service";

export const BtnPermissionStore = defineStore('BtnPermission', {
    state: (): DictionaryStates => ({
        data: []
    }),
    actions: {
        async getBtnPermissionStore() {
            const ret: any = await request({
                url: '/api/system/menu_button/menu_button_all_permission/',
                method: 'get',
            });
            // 转换数据格式并保存到pinia
            let dataList = ret.data
            this.data=dataList
        },
    },
    persist: {
        enabled: true,
    },
});

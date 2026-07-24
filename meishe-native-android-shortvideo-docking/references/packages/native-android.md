# 原生 Android 官方包事实

- 下载 `iOS&Android vX.x.x`，输入为 `native/android/ShortVideo/app/libs/NvShortVideoCore.aar`。
- 目标项目使用项目本地 `<app-module>/libs/NvShortVideoCore.aar`，这是唯一直接 AAR 接入路线。
- 官方调用锚点包括 `NvModuleManager.init/initSdk/initModel/initConfig`、`downloadPrefabricatedMaterial`、`openCapture`、`openEdit`、`startDualCapture` 和 `openDraftActivity`。
- 发布回调由 `NvModuleManagerCallback.publishWithInfo(...)` 驱动；生成项目路由到本 skill 的作品发布页。

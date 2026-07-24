# Flutter 官方包事实

- 下载 `Flutter工程 vX.x.x`，输入为 `flutter/nvshortvideo`，插件名是 `nvshortvideo`。
- 应用通过本地 path dependency 引用该插件，入口为 `shortVideoOperator()`。
- 已确认 API 包括服务配置、预置素材下载、拍摄、合拍、编辑、草稿列表/重编/删除、编辑/草稿/编译事件、发布信息、保存草稿、编译和退出编辑。
- 官方编辑流程由 `NvVideoEditEvent.publish` 驱动外层作品发布页。

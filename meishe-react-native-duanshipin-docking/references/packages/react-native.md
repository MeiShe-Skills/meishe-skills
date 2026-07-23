# React Native 官方包事实

- 下载 `React Native工程 vX.x.x`，输入为 `react_native/react-native-nvshortvideo`，npm 包名相同。
- 应用使用项目本地 `file:` dependency，入口为 `NvShortVideo.shareInstance()`。
- 官方源码保留 `startVideoCaptrue`、`startVideoDualCaptrue`、`startVideoDualCaptrueWithVideo`、`startSeleteFilesForEdit` 等拼写。
- 已确认 API 包括服务配置、预置素材、草稿、编辑事件、保存草稿、编译、发布信息和退出编辑。
- 选择素材方法返回仅表示 SDK 页面已启动，作品发布由 `VideoEditResultEvent` 驱动。

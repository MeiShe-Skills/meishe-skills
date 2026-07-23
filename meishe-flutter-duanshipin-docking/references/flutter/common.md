# Flutter 公共接入规则

## 输入与自包含

- 官方下载项为 `Flutter工程 vX.x.x`，必需目录是 `flutter/nvshortvideo`。
- `--plugin-path` 只作为复制源；验证 `pubspec.yaml` 包含 `name: nvshortvideo` 后复制到 `vendor/meishe/nvshortvideo`。
- 应用 `pubspec.yaml` 必须使用 `path: vendor/meishe/nvshortvideo`。不得引用下载目录，也不得生成假的插件目录。
- 自动搜索仅限 `--target-root` 内的非生成目录；找不到有效插件时，在修改项目之前停止并要求用户提供准确路径。
- Android 原生库完整性在写入前检查；SDK 通过临时目录校验后整体替换，旧版本进入 `.meishe_docking_backup`，不覆盖合并不同版本。
- 同一个官方 Flutter 插件服务于目标中存在的 Flutter 子平台。单端项目只校验和执行该子平台，不要求另一端目录；License 只复制到当前目标端实际存在的运行时资源目录。未提供真实 License 时保留水印路径。
- `--package-name` 保留为双端相同身份的兼容入口；双端身份不同时使用 `--android-package-name` 和 `--ios-bundle-identifier`。公共参数与平台专属参数冲突时写入前失败；未传入时保持工程已有身份。
- 当前任务新建且包含 iOS 的项目必须传 `--ios-bundle-identifier com.meishe.duanshipindemo`。已有项目未要求改身份时保持 App Target 现有值；非官方值必须明确提示官方素材服务不可用，并让用户在官方 Demo 临时身份与客户服务路径之间选择。

## 生成层

- 生成 `lib/meishe_short_video_docking.dart`，服务修改入口为 `MeisheShortVideoDocking.defaultServerConfig`。
- 生成首页、作品发布页和本地草稿箱，并遵循 `references/demo-ui-style.md`。
- 编辑入口必须等待 `NvVideoEditEvent.publish` 再进入作品发布页；`startSelectFilesForEdit()` 返回不代表编辑流程完成。
- 发布页覆盖 `getPublishInfo()`、`saveDraft(...)`、`compileCurrentTimeline(...)`、编译事件和 `exitEdit(projectId)`。
- 草稿页覆盖 `getDraftList()`、`reeditDraft(...)`、`deleteDraft(...)` 和草稿更新事件。
- 素材准备在首帧后启动并保持 single-flight；前台恢复只在未完成时重试。Android 拍摄、合拍、编辑点击路径不得发起服务配置或素材下载。Flutter iOS `2.0.2.1` 官方 Demo 身份按 iOS 子路由在点击时确认服务配置并非阻塞刷新素材；任何平台都不得因准备失败禁用入口。
- 复制 banner 和功能图标到应用 `assets/` 并写入 `pubspec.yaml`。仅替换仍为默认计数器模板的 `main.dart`，否则报告路由接线步骤。
- 在现有 `README.md` 的 `BEGIN/END MEISHE_FLUTTER_RUN_GUIDE` 标记块内生成运行说明，保留用户原文并支持重复执行。单端只写当前端，双端分别列出 Android、iOS 的准确目录、依赖命令、运行方式、workspace 和用户签名边界。

## 服务与校验

- 客户服务器配置遵循 `references/customer-server.md`；只有用户提供真实 host、接口、凭据、白名单和测试数据后才能声明服务验收通过。
- 报告在应用根目录登记 `flutter pub get`，但脚本不执行；先按 `references/dependency-installation.md` 让用户选择 `用户执行` 或 `自动执行`。依赖完成后用 `flutter analyze lib` 校验生成代码，`vendor/meishe` 诊断作为第三方 SDK 输出单独记录。
- 接入结束后检查 `pubspec.yaml`、锁文件和插件元数据，确保不再引用外部下载路径。

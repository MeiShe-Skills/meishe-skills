# React Native 公共接入规则

## 输入与自包含

- 官方下载项为 `React Native工程 vX.x.x`，必需目录是 `react_native/react-native-nvshortvideo`。
- 验证插件 `package.json` 和官方包结构后，复制到 `vendor/meishe/react-native-nvshortvideo`。
- `package.json` 和支持的 lockfile 必须使用 `file:vendor/meishe/react-native-nvshortvideo`。只修补项目本地副本，不修改下载目录。
- 自动搜索仅限 `--target-root`。缺包时在目标写入前停止，说明官方下载入口和准确目录；不得创建假的 npm 包。
- Android 原生库完整性在写入前检查；SDK 通过临时目录校验后整体替换，旧版本进入 `.meishe_docking_backup`，不覆盖合并不同版本。
- 同一个官方 RN npm 包服务于目标中实际存在的 RN 子平台。单端项目只校验和执行该子平台，不要求另一端目录；License 只写入当前目标端资源目录。不得把原生 AAR 或原生 CocoaPods 包变成 RN 的正常附加输入。

## JS/TS 生成层

- 生成 `src/meisheShortVideoDocking.ts|js`、首页、作品发布页和本地草稿箱，并遵循 `references/demo-ui-style.md`。
- 包装官方保留拼写错误的方法名，并把正确拼写仅作为兼容回退。
- 编辑器下一步必须由原生 `VideoEditMethodChannel` 的 `VideoEditResultEvent` 驱动作品发布页，不能把选择素材方法 resolve 当成流程结束。
- 发布页覆盖发布信息、保存草稿、编译、编译进度和退出编辑；草稿页覆盖列表、继续编辑、删除和刷新。
- 素材准备延后到初始交互完成后，保持 single-flight；恢复前台只在未完成时重试。Android 功能点击路径保持与准备任务解耦；RN iOS `2.0.2.1` 的已验证点击顺序只从 `references/react-native/ios.md` 读取，不得扩散到其他子平台。
- 更新现有包管理器声明；已有 `node_modules` 时仅处理本地插件链接/副本。脚本不执行联网安装。依赖、构建和设备操作遵循 `references/dependency-installation.md` 的 `用户执行` / `自动执行` 二选一协议。ESLint、Jest 和备份目录与第三方 SDK 输出隔离；Jest 的 `NvVideoConfig` mock 必须包含 album、template、capture 三层配置及拍摄底部菜单枚举，保证生成后的默认 App 测试可执行。
- 保留用户原 README，仅维护带标记的 RN 运行说明区块。按目标实际存在的平台写入 JS 依赖、Metro、Android 或 iOS 的准确目录和命令；iOS 必须指向 `.xcworkspace`，单端项目不得出现另一端运行说明。

## 服务与校验

- 服务修改入口是 `src/meisheShortVideoDocking.ts|js` 的 `meisheServerConfig`，遵循 `references/customer-server.md`。
- `--package-name` 用于双端相同身份；双端不同时使用 `--android-package-name` 和 `--ios-bundle-identifier`。每个平台都必须完整同步 namespace、applicationId、源码包或 Bundle Identifier，冲突参数写入前失败。
- 当前任务新建且包含 iOS 的项目必须传 `--ios-bundle-identifier com.meishe.duanshipindemo`。已有项目未要求改身份时保持 App Target 现有值；非官方值必须明确提示官方素材服务不可用，并让用户在官方 Demo 临时身份与客户服务路径之间选择。
- 依赖安装完成后，生成代码用项目现有 ESLint 命令校验，`vendor/meishe`、Pods 和构建目录不参与应用 lint；不得用会临时下载包的裸 `npx` 绕过依赖审批。
- 接入结束后扫描配置和锁文件，确保不存在外部下载路径。

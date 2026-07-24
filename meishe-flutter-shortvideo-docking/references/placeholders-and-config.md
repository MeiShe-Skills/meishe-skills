# 占位符与通用配置原则

有用户提供的真实文件和值时直接使用；否则完成代码接入，在 `meishe_docking_report.md` 中列出当前路由的准确填写位置。License、密钥和服务鉴权不创建可被误发送或误打包的字面占位值。

## 服务字段

生成配置可能包含以下字段：host、assetRequestUrl、assetCategoryUrl、assetMusiciansUrl、assetFontUrl、assetDownloadUrl、assetPrefabricatedUrl、assetAutoCutUrl、assetTagUrl、clientId、clientSecret、assemblyId、isAbroad。

字段默认值和应用限制只能从当前路由文档读取。共享文档不定义某个平台的 host、Bundle Identifier、package name、接口路径或补丁。替换服务值前读取 references/customer-server.md，并获得真实服务合同、白名单、测试环境和预期素材；静态配置不等于运行验证。

## License

优先使用 --license-path。未提供时：

- 不创建占位 meishesdk.lic。
- 保留目标项目或所选官方包中已经存在的 License。
- 报告无授权运行会产生 MEISHE 水印。
- 说明正式 License 必须在美摄后台按最终应用身份申请并经过商务授权。
- 除非用户明确指定，不从其他示例工程复制 License。
- Flutter 只保留当前官方插件中已经存在且身份匹配的 Demo License，或使用用户通过 `--license-path` 提供的真实文件；不扫描 Downloads 或其他项目寻找 License。

## 生成配置

只生成当前路由所需的最小配置。完整官方 Demo 配置若引用额外图片、模型或素材，只有在这些资源也完整进入目标项目时才能复制。路线专属的配置文件、默认开关和资源要求记录在对应路由文档中。

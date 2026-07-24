# 美摄 Agent Skills

[English](README.md)

本仓库为美摄产品相关的Agent Skill仓库。

仓库后续可以继续增加新的 Skill。请始终通过 `--list` 查看当前版本实际提供的
Skill。

## Agent 兼容性

仓库内的 Skill 遵循开放的 Agent Skills 格式，不依赖某一家 Agent 的专属运行
API。可以通过 `skills` CLI 安装到 Codex、Cursor、Qoder、Claude Code，以及
市面上的主流Agent。

常用 Agent 参数如下：

| Agent | `--agent` 参数 |
| --- | --- |
| Codex | `codex` |
| Cursor | `cursor` |
| Qoder | `qoder` |
| Claude Code | `claude-code` |

不指定 `--agent` 时，CLI 会检测本机已经安装的 Agent，并显示交互选择。

## 环境要求

- Node.js 18 或更高版本。
- 能够运行 `npx`。
- 已安装所选 Skill 需要的开发工具链，例如iOS需要Xcode，android需要Android Studio和Java等。
- 已准备对应美摄产品要求的 SDK 包、License、服务配置或签名材料。

每个产品的具体前置条件和限制以对应 Skill 内部文档为准。

## 查看当前可用 Skill

在准备使用 Skill 的项目根目录执行：

```sh
npx skills add MeiShe-Skills/meishe-skills --list
```

也可以使用完整 GitHub 地址：

```sh
npx skills add https://github.com/MeiShe-Skills/meishe-skills --list
```

该命令的输出是当前仓库版本所包含 Skill 的准确清单。

## 当前 ShortVideo Skill

当前已经发布的 ShortVideo 接入路线使用以下名称：

| Skill | 目标平台 |
| --- | --- |
| `meishe-react-native-shortvideo-docking` | React Native Android、iOS 单端或双端 |
| `meishe-flutter-shortvideo-docking` | Flutter Android、iOS 单端或双端 |
| `meishe-native-ios-shortvideo-docking` | 原生 iOS |
| `meishe-native-android-shortvideo-docking` | 原生 Android |

该表只说明当前 ShortVideo 接入路线，不是写死的仓库完整清单。请使用 `--list`
查看包括后续新增 Skill 在内的全部可用内容。

## 交互安装

让 CLI 检测 Agent，并交互选择需要安装的 Skill：

```sh
npx skills add MeiShe-Skills/meishe-skills
```

默认安装到当前项目。添加 `--global` 后安装到用户级别，可供多个项目使用：

```sh
npx skills add MeiShe-Skills/meishe-skills --global
```

## 安装到指定 Agent

将仓库当前提供的全部 Skill 安装到一个 Agent：

```sh
npx skills add MeiShe-Skills/meishe-skills \
  --skill '*' \
  --agent codex
```

可以把 `codex` 替换为 `cursor`、`qoder`、`claude-code` 或 CLI 支持的其他
Agent 参数。追加 `--global` 可进行用户级安装，追加 `--yes` 可跳过交互确认。

同时安装到多个 Agent：

```sh
npx skills add MeiShe-Skills/meishe-skills \
  --skill '*' \
  --agent codex \
  --agent cursor \
  --agent qoder \
  --agent claude-code
```

将全部 Skill 安装到本地 CLI 支持的全部 Agent：

```sh
npx skills add MeiShe-Skills/meishe-skills --all
```

## 安装指定 Skill

先执行 `--list`，然后选择输出中的实际名称。例如：

```sh
npx skills add MeiShe-Skills/meishe-skills \
  --skill meishe-react-native-shortvideo-docking \
  --agent cursor
```

重复使用 `--skill` 可以一次安装多个指定 Skill：

```sh
npx skills add MeiShe-Skills/meishe-skills \
  --skill SKILL_NAME_1 \
  --skill SKILL_NAME_2 \
  --agent claude-code
```

## 从美摄官网下载

如果访问 GitHub 速度较慢或无法连接，可以前往
[美摄开发者中心](https://www.meishesdk.com/developers/)下载最新版美摄
Agent Skills 压缩包，并解压到本地目录。

查看下载包内包含的 Skill：

```sh
npx skills add /你的绝对路径/meishe-skills --list
```

从本地下载包交互安装：

```sh
npx skills add /你的绝对路径/meishe-skills
```

将本地下载包中的全部 Skill 安装到指定 Agent：

```sh
npx skills add /你的绝对路径/meishe-skills \
  --skill '*' \
  --agent cursor
```

本地路径安装同样支持 `--global`、`--agent`、`--skill`、`--all` 和 `--yes`
参数。

## 确认安装结果

查看已经安装的 Skill：

```sh
npx skills list
```

按 Agent 筛选：

```sh
npx skills list --agent codex
npx skills list --agent cursor
npx skills list --agent qoder
npx skills list --agent claude-code
```

只查看用户级 Skill：

```sh
npx skills list --global
```

## 更新

更新当前项目中的全部 Skill：

```sh
npx skills update --project
```

更新用户级的全部 Skill：

```sh
npx skills update --global
```

更新指定 Skill：

```sh
npx skills update meishe-react-native-shortvideo-docking
```

## 注意事项

- 每个 Skill 必须完整包含自己的 `SKILL.md`、脚本、参考资料和资源。
- 只使用所选 Skill 支持的官方包类型和版本。
- 遵守所选 Skill 的设备要求。移动端 SDK Demo 可能必须连接 Android 或 iOS
  真机运行，不一定支持模拟器。

## 相关链接

- [美摄开发者中心](https://www.meishesdk.com/developers/)
- [GitHub 仓库](https://github.com/MeiShe-Skills/meishe-skills)
- [skills CLI 文档](https://skills.sh/docs/cli)
- [skills CLI 源码](https://github.com/vercel-labs/skills)

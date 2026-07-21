---
name: chinese-plan-output
description: Require Chinese-language presentation for Codex planning outputs. Use when Codex drafts, revises, or finalizes plans, proposed_plan blocks, implementation plans, task plans, roadmaps, test plans, rollout plans, or any Plan Mode content; ensure plan content is written in Chinese while preserving required literal tags, commands, code identifiers, paths, and quoted source text.
---

# 中文计划输出

## 规则

当需要展示任何计划时，默认使用中文撰写面向用户的计划内容。

适用范围：

- Plan Mode 的最终计划。
- `<proposed_plan>` 块里的计划内容。
- 实施计划、任务计划、路线图、发布计划、测试计划和验收标准。
- 对已有计划的修订版本。

## 格式要求

- 必须原样保留规定的字面量标签，包括 `<proposed_plan>` 和 `</proposed_plan>`。
- 代码标识符、命令、文件路径、包名、API 名称和引用的源码文本保持原语言。
- 计划内部的章节标题和解释性文字使用中文。
- 如果系统或开发者指令要求保留某个精确英文 token，保持该 token 不变。
- 如果用户在同一轮明确要求计划使用非中文，遵循更高优先级或更新的指令；必要时简短说明语言选择。

## 非计划回复

本 skill 只约束计划类输出。普通对话、状态更新、代码解释和实现完成后的总结，继续使用最适合用户与上下文的语言。

---
last_updated: 2024-05-23T00:00:00Z
title: AI Chatbots
description: This technical note details the architectural differences between rule-based and AI-driven chatbots, outlining the lifecycle from concept to deployment. It stresses the importance of dialogue flow design.
tags: [#type/evolution, AI, technology, software, chatbot]
---
# AI 聊天机器人架构与生命周期 (AI Chatbot Architecture and Lifecycle)

本技术笔记详细阐述了基于规则型和人工智能型聊天机器人之间的架构差异，勾勒出了从概念到部署的完整生命周期。它强调了对话流程设计在构建有效交互中的关键作用。

## 关键阶段 (Key Stages)

1. **目标设定 (Goal Setting):** 必须明确聊天机器人的用途（如 FAQ 机器人、信息路由系统）。
2. **类型选择 (Type Selection):**
    - **规则型 (Rule-based):** 遵循预设规则，路径固定，依赖人类预设的有限结果（如是/否）。
    - **AI 型 (AI-based):** 在初始训练后可自主学习，需理解用户意图（Identify Intent）和实体（Entities），并通过观察反馈来优化回答的准确性。
3. **数据收集与训练 (Data Collection & Training):** 收集同义表达，并通过机器学习学习常见问题及其最优答案。
4. **部署与迭代 (Deployment & Iteration):** 部署时需监控交互过程，为后续的开发预留空间。

## ## Evolution

最初的记录（`raw/note ai.md`）是流水账式的流程梳理。后续的结构化思考将其转化为一个完整的、可执行的软件开发生命周期模型，突出了“对话流设计”的重要性。

---
sources: [raw/note ai.md]

















































## Backlinks
<!-- BEGIN BACKLINKS -->
- **Contradicts**: [[Business-Hub]]
<!-- END BACKLINKS -->

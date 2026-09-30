# Agent 协同开发准则 (Multi-Agent Protocol)

欢迎协助开发本项目 Context Cockpit。本项目采用 **Git 黑板协作模式**。所有进入本项目的 AI 必须严格遵守以下工作流：

## 必读工作流 (SOP)
1. **开工前**：必须首先读取 `.context/system.md`（掌握约束）和 `.context/state.md`（掌握当前进展与上个 Agent 的留言）。
2. **作业中**：严格遵循 `decisions.md` 中的架构决策，不自作主张推翻已有技术选型与分层原则。
3. **收工前**：必须就地更新 `.context/state.md`，包括：
   - 勾选已完成的任务；
   - 更新 `Handover Note`（交接便签），详细说明你修改了什么文件、当前留下了什么半成品、下一步建议。

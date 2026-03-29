# Codex Automation Prompt

在仓库根目录 `/workspace` 中完成今天的 AI 情报日报更新。

目标：

1. 运行日报流水线，尽量使用仓库内现有脚本，不要手写临时逻辑。
2. 如果环境还没初始化，先执行：
   - `./scripts/setup_cloud.sh`
3. 然后执行：
   - `./scripts/run_pipeline_cloud.sh`
4. 检查 `reports/`、`public/`、`data/last30days/` 相关输出是否成功更新。
5. 如果流水线失败，先阅读错误并尽量修复；只有在无法安全修复时才停止，并把阻塞原因写进最终说明。
6. 如果生成结果为空，但流程成功，也要保留更新后的站点与报告文件，并在最终说明里指出“内容为空的原因更可能是信号不足或数据源不足，而不是流水线失败”。
7. 查看 `git status`。
8. 如果没有文件变化，输出简短说明并结束，不要强行提交空提交。
9. 如果有文件变化：
   - 用清晰的提交信息提交
   - 推送到当前分支的远端

提交信息建议：

- `chore: refresh AI signal briefing`
- 如果你修了流水线问题，可改为 `fix: repair briefing pipeline`

输出要求：

1. 用简短中文总结今天做了什么。
2. 明确说明：
   - 是否成功运行流水线
   - 是否有新的 report / public 更新
   - 是否已经 commit
   - 是否已经 push
3. 如果失败，给出最小必要的失败原因和下一步建议。

注意事项：

- 优先复用仓库已有脚本：
  - `scripts/setup_cloud.sh`
  - `scripts/run_pipeline_cloud.sh`
  - `scripts/run_pipeline.py`
- 不要改动与日报任务无关的文件。
- 不要删除历史报告。
- 如果需要 `last30days` upstream，请通过仓库里的 bootstrap 逻辑获取，不要假设本机一定存在 `~/.agents/skills/last30days`。

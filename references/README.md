# references/（本地文献库）

把你希望 AI 参考的资料放在这个目录里，后端会在对话时做**轻量关键词检索**并把少量摘录注入提示词（用于更严谨、更一致的回答）。

## 支持的格式（当前版本）
- `.txt`
- `.md`

> 不直接解析 PDF：请你把 PDF 内容手动/工具转换成 `.txt` 或 `.md` 再放进来。

## 建议的文件组织方式
```
references/
  autism_communication/
    paper_2020_xyz.md
    notes_parent_training.txt
  sensory_regulation/
    guidelines_summary.md
```

## 注意
- 这里的资料可能包含敏感内容；如果你要开源仓库，请确认你有分享/公开的权限。
- 即使有资料，AI 也不能替代临床诊断或治疗。建议把输出当成“沟通建议/参考信息”，必要时咨询专业人士。


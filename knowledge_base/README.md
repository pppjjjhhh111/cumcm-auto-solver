# cumcm-auto-solver 本地知识库

## 知识库用途
该目录为本地 RAG 知识库，服务于数学建模自动求解流程。开启本地知识库增强后，系统会检索方法卡、论文模板、题型套路、通用经验和代码套路，用于辅助模型选择、公式生成、图表规划、论文写作和代码结构建议。

## 目录结构
- `methods/`：数学建模方法卡，按 evaluation、prediction、optimization、classification、simulation、network 分类。
- `paper_templates/`：不同题型的论文结构和写作套路。
- `problems/`：常见题型、小问模式和建模路线选择规则。
- `notes/`：灵敏度分析、鲁棒性、图表设计、摘要写作等通用经验。
- `code_patterns/`：安全、可复现的代码实现套路。

## RAG 使用方式
`methods` 主要用于建模策略和公式生成；`paper_templates` 用于论文结构；`notes` 用于图表、验证和写作质量；`code_patterns` 用于代码生成提示；`problems` 用于题型识别和路线选择。

## 添加新卡片
每个 Markdown 文件只写一个主题。标题、关键词、适用场景、输入输出、步骤、公式、图表建议和常见扣分点应完整。优先使用原创结构化总结，不复制论文、教材或网页原文。

## 构建索引
```bash
python main.py --build-kb knowledge_base/
```

## 命令行启用
```bash
python main.py --problem path/to/problem.pdf --data path/to/data_dir --use-rag
```

## UI 启用
在 Streamlit 侧边栏打开“启用本地知识库增强”。

## 内容质量规范
卡片应主题单一、关键词明确、公式清晰、输入输出具体，并说明不适用场景和常见扣分点。

## 不建议放入的内容
不要放 API key、个人数据、未整理的大段 PDF、完整论文原文、实时竞赛材料、无来源大段复制文本或空占位文件。

## 后续维护建议
定期检查检索命中质量；优先补充高频题型和高频方法；删除重复或过时卡片；保持 20 到 80 张高质量卡片而不是堆积低质量材料。

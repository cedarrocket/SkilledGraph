# 子图复用与执行追踪

`workflow_cn.md` 两次引用同一个 `review_cn.md`，分别命名为 InitialReview 和 FinalReview。每个文件独立采用默认 MessagesState，共享 messages 传递草稿与审查意见；父层不覆盖子图 Schema，子图不启动 Host。

离线示例（脚本回复，不调用 API，不代表模型质量）：

```bash
printf '说明如何检查一个数学命题。\n' | .venv/bin/sgraph examples/19-subgraphs/workflow_cn.md -- --model-factory python:./model_cn.py:create
```

使用已配置的真实模型时，省略 `--model-factory` 及参数。标准 chat Host 以 `InitialReview / Examine` 等名称显示内部节点回复，同一消息只显示一次。追踪元数据输出到 stderr，不自动进入模型上下文。子图 @End 返回父图；子文件也可通过相同命令形式独立执行。

自定义 Host 可以向 load_graph 传入 TraceRecorder，显式保存 JSONL 或把 render() 放入下一轮规划上下文。修改图文件后重新构建，已运行的编译图不会热替换。任意累加型 reducer 都可能在子图返回时重复累计输入，需要转换时使用原生 Python 适配。

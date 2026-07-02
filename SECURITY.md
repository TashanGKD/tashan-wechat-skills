# Security

请勿在本仓库提交任何密钥。Do not publish secrets in this repository.

## 禁止提交 / Never commit

- API keys、bearer token（如 `DASHSCOPE_API_KEY`、`AI_GENERATION_API_KEY`、`DMXAPI_KEY`）
- cookies、bind key
- SSH 私钥、云凭据
- 凭据文件的具体位置或内容（credential file paths or contents）
- 可能含用户数据的原始模型日志

## 密钥处理约定 / Expected secret handling

调用外部服务的 skill（本仓库主要是 `ai-image-generator` 调 DashScope）必须**从环境变量读取密钥**，不得打印密钥值，也不得写入运行清单、报告、提示词、示例、测试或最终消息。

常用环境变量：

- `DASHSCOPE_API_KEY`（首选，直连 DashScope 图片端点）
- `AI_GENERATION_API_KEY`
- `LLM_API_KEY`

⚠️ 形如 `sk-sp-...` 的后端代理 key 不能直连 DashScope 图片接口（返回 401）。

## 报告问题 / Reporting

如发现泄漏的凭据、不安全默认值或可复现漏洞，请开私有 security advisory 或联系仓库所有者，不要公开 issue。

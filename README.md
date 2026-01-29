# AgentCore Browser + Chrome Extension Demo

演示如何在AWS AgentCore Browser中加载Chrome Extension，并自动配置临时AWS凭证。

## 功能特性

- ✅ 自动获取1小时有效的临时AWS凭证
- ✅ 自动配置Extension的AWS凭证和默认Rule
- ✅ 支持多个Extensions同时加载（最多10个）
- ✅ Stealth Extension - 绕过机器人检测
- ✅ Bedrock Summary Extension - AI网页摘要（Claude 3 Haiku）

## 快速开始

### 前置要求

```bash
# 配置AWS凭证
aws configure

# 需要的权限：
# - s3:CreateBucket, s3:PutObject, s3:GetObject
# - bedrock-agentcore:StartBrowserSession
# - bedrock:InvokeModel
# - sts:GetSessionToken
```

### 3步启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 创建Extensions
python create_stealth_extension.py
python setup_bedrock_summary_extension.py

# 3. 运行Demo
python main.py \
  --extension-zip stealth-extension.zip \
  --extension-zip bedrock-summary-extension.zip
```

## Extensions说明

### 1. Stealth Extension (3.7 KB)

**功能**: 绕过机器人检测
- 覆盖 `navigator.webdriver`
- 修改User-Agent
- 随机化浏览器指纹
- 移除自动化相关headers

**使用**: 访问google.com等检测自动化的网站

**注意**: 
- ✅ 直接访问URL效果最好
- ⚠️ 快速自动化操作可能仍被检测（行为模式）

### 2. Bedrock Summary Extension (140 KB)

**功能**: AI网页摘要
- 使用Claude 3 Haiku模型
- 自动配置AWS凭证
- 自动配置默认Rule

**默认Rule**: `<p>(.*?)</p>|<h[1-6]>(.*?)</h[1-6]>|<li>(.*?)</li>|<article>(.*?)</article>`

**使用**:
1. 访问任意网页
2. 点击extension图标
3. 查看自动生成的摘要

## 命令行选项

```bash
# 单个extension
python main.py --extension-zip stealth-extension.zip

# 多个extensions
python main.py \
  --extension-zip stealth-extension.zip \
  --extension-zip bedrock-summary-extension.zip

# 自定义S3 bucket
python main.py --bucket my-bucket --extension-zip stealth-extension.zip

# 自定义region
python main.py --region us-west-2 --extension-zip stealth-extension.zip

# 只准备不创建browser
python main.py --prepare-only --extension-zip stealth-extension.zip
```

## 工作原理

```
1. 获取临时AWS凭证 (STS - 1小时有效)
   ↓
2. 注入凭证到Extension源码
   ↓
3. 构建并打包Extension
   ↓
4. 上传到S3 Bucket
   ↓
5. 创建Browser Session (自动加载Extensions)
```

## 文件说明

| 文件 | 功能 |
|------|------|
| `main.py` | 主程序，支持多extensions |
| `create_stealth_extension.py` | 生成Stealth extension |
| `setup_bedrock_summary_extension.py` | 构建Bedrock Summary extension |
| `setup_extension.py` | Extension准备模块 |
| `s3_manager.py` | S3管理模块 |
| `browser_with_extension.py` | Browser管理模块 |
| `cleanup.sh` | 清理脚本 |

## 故障排除

| 问题 | 解决方案 |
|------|---------|
| AWS凭证错误 | 运行 `aws configure` |
| S3权限错误 | 检查IAM权限 |
| Browser创建失败 | 确认region支持AgentCore Browser |
| Extension未加载 | 检查S3 URI和extension格式 |
| git/npm未安装 | `brew install git node` |
| 临时凭证过期 | 重新运行demo（1小时有效期） |
| Bedrock权限错误 | 确保有bedrock:InvokeModel权限 |
| Claude模型未启用 | 在Bedrock console启用Claude 3模型 |
| 摘要一直转圈 | 检查Bedrock权限和模型访问 |
| Google仍要求验证 | 直接访问URL，避免快速自动化操作 |

### 详细问题

#### boto3版本过旧
```bash
pip install --upgrade boto3 botocore awscli
```

#### Claude模型未启用
1. 访问: https://console.aws.amazon.com/bedrock/home?region=us-west-2#/modelaccess
2. 点击"Manage model access"
3. 启用"Claude 3"模型
4. 等待访问授权

#### Extension功能异常
- 右键extension图标 -> "检查弹出内容" -> 查看Console
- 检查AWS凭证是否填充
- 检查Rule是否设置
- 验证Bedrock API访问

## 清理资源

```bash
# 使用清理脚本
./cleanup.sh

# 或手动清理
aws s3 rb s3://browser-extension-demo-zihangh-20260129 --force
rm -rf stealth_extension/ amazon-bedrock-summary-client-for-chrome/
rm -f *.zip
```

## 限制说明

- Extension大小: 最大10MB
- Extensions数量: 最多10个/session
- 临时凭证: 1小时有效期
- S3 bucket: 必须与browser在同一账户
- Stealth限制: 只能绕过浏览器指纹检测，无法模拟人类行为模式

## 参考文档

- [AgentCore Browser Extensions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-extensions.html)
- [Amazon Bedrock Summary Extension](https://github.com/aws-samples/amazon-bedrock-summary-client-for-chrome)
- [AWS STS临时凭证](https://docs.aws.amazon.com/STS/latest/APIReference/API_GetSessionToken.html)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.


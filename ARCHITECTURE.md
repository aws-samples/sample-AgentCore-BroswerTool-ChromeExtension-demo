# AgentCore Browser + Chrome Extension 架构图

## 整体架构概览

```mermaid
graph TB
    subgraph "用户操作层"
        USER[用户] -->|1. 运行命令| MAIN[main.py<br/>主程序编排器]
    end

    subgraph "Extension准备阶段"
        MAIN -->|2. 准备Extensions| SETUP[setup_extension.py<br/>Extension准备模块]
        SETUP -->|2.1 请求临时凭证| STS[AWS STS<br/>GetSessionToken API]
        STS -->|返回1小时临时凭证| SETUP
        SETUP -->|2.2 提取Extension| ZIP[Extension ZIP]
        SETUP -->|2.3 注入AWS凭证| INJECT[凭证注入<br/>修改popup.js/html]
        INJECT -->|2.4 打包| PKG[Extension Package<br/>.zip文件]
    end

    subgraph "S3存储阶段"
        MAIN -->|3. 上传到S3| S3MGR[s3_manager.py<br/>S3管理模块]
        S3MGR -->|3.1 检查/创建Bucket| S3BUCKET[S3 Bucket<br/>browser-extension-demo]
        S3MGR -->|3.2 上传Extension| S3OBJ[S3 Object<br/>s3://bucket/extensions/xxx.zip]
        S3MGR -->|3.3 验证访问| S3OBJ
    end

    subgraph "Browser会话阶段"
        MAIN -->|4. 创建Browser| BROWSER[browser_with_extension.py<br/>Browser管理模块]
        BROWSER -->|4.1 调用StartBrowserSession| AGENTCORE[AWS Bedrock AgentCore<br/>Browser Service]
        AGENTCORE -->|4.2 从S3加载Extensions| S3OBJ
        AGENTCORE -->|4.3 返回Session ID| SESSION[Browser Session<br/>30分钟超时]
        BROWSER -->|4.4 验证Extension加载| SESSION
    end

    subgraph "Extension功能"
        SESSION -->|加载| EXT1[Stealth Extension<br/>3.7 KB]
        SESSION -->|加载| EXT2[Bedrock Summary Extension<br/>140 KB]

        EXT1 -->|绕过检测| STEALTH[• navigator.webdriver<br/>• User-Agent修改<br/>• 浏览器指纹随机化]

        EXT2 -->|使用凭证| BEDROCK[AWS Bedrock<br/>InvokeModel API]
        BEDROCK -->|Claude 3 Haiku| SUMMARY[AI网页摘要]
    end

    style USER fill:#e1f5ff
    style MAIN fill:#fff4e6
    style SETUP fill:#f3e5f5
    style S3MGR fill:#e8f5e9
    style BROWSER fill:#fff3e0
    style SESSION fill:#e0f2f1
    style EXT1 fill:#fce4ec
    style EXT2 fill:#f1f8e9
```

## 详细技术实现流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Main as main.py
    participant Setup as setup_extension.py
    participant STS as AWS STS
    participant S3Mgr as s3_manager.py
    participant S3 as S3 Bucket
    participant Browser as browser_with_extension.py
    participant AgentCore as AgentCore Browser
    participant Extension as Chrome Extension

    User->>Main: python main.py --extension-zip xxx.zip

    rect rgb(240, 240, 255)
        Note over Main,Setup: 阶段1: Extension准备
        Main->>Setup: prepare_extension()
        Setup->>STS: get_session_token(duration=3600s)
        STS-->>Setup: AccessKeyId + SecretKey + SessionToken
        Setup->>Setup: 提取Extension ZIP
        Setup->>Setup: 注入凭证到popup.js/popup.html
        Setup->>Setup: 重新打包为ZIP
        Setup-->>Main: extension.zip路径
    end

    rect rgb(240, 255, 240)
        Note over Main,S3: 阶段2: S3存储
        Main->>S3Mgr: setup_and_upload(extension.zip)
        S3Mgr->>S3: create_bucket() if not exists
        S3->>S3Mgr: bucket created/exists
        S3Mgr->>S3: upload_file(extension.zip)
        S3-->>S3Mgr: s3://bucket/extensions/xxx.zip
        S3Mgr->>S3: head_object() 验证
        S3-->>S3Mgr: 验证成功
        S3Mgr-->>Main: S3 URI
    end

    rect rgb(255, 240, 240)
        Note over Main,AgentCore: 阶段3: Browser创建
        Main->>Browser: create_browser_session([s3_uri])
        Browser->>AgentCore: start_browser_session({<br/>  browserIdentifier: 'aws.browser.v1',<br/>  extensions: [{s3: {bucket, prefix}}],<br/>  sessionTimeoutSeconds: 1800<br/>})
        AgentCore->>S3: GetObject(s3://bucket/extensions/xxx.zip)
        S3-->>AgentCore: Extension ZIP内容
        AgentCore->>AgentCore: 解压并加载Extension
        AgentCore-->>Browser: sessionId
        Browser->>Browser: verify_extension_loaded()
        Browser-->>Main: session_details
    end

    rect rgb(255, 255, 240)
        Note over Main,Extension: 阶段4: Extension运行
        Main->>User: 显示Browser控制台链接
        User->>AgentCore: 打开Browser控制台
        AgentCore->>Extension: 加载Extension到浏览器
        Extension->>Extension: 从localStorage读取AWS凭证
        User->>Extension: 访问网页 + 点击Extension图标
        Extension->>AgentCore: 使用注入的凭证调用Bedrock
        AgentCore-->>Extension: AI摘要结果
        Extension->>User: 显示摘要
    end
```

## 核心组件技术栈

```mermaid
graph LR
    subgraph "Python后端"
        A[boto3] -->|AWS SDK| B[STS Client]
        A -->|AWS SDK| C[S3 Client]
        A -->|AWS SDK| D[Bedrock AgentCore Client]
        E[rich] -->|终端UI| F[Console输出]
        G[pathlib] -->|文件操作| H[ZIP处理]
    end

    subgraph "AWS服务"
        B -->|临时凭证| I[AWS STS]
        C -->|存储| J[S3 Bucket]
        D -->|Browser会话| K[AgentCore Browser]
        K -->|AI模型| L[Bedrock Claude 3]
    end

    subgraph "Chrome Extension"
        M[manifest.json] -->|配置| N[Extension元数据]
        O[popup.js] -->|逻辑| P[AWS凭证注入点]
        Q[popup.html] -->|UI| R[Extension界面]
        P -->|调用| L
    end

    style A fill:#3776ab
    style I fill:#ff9900
    style J fill:#569a31
    style K fill:#ff9900
    style L fill:#ff9900
```

## 数据流向图

```mermaid
flowchart TD
    subgraph "凭证流"
        A1[AWS IAM用户] -->|长期凭证| A2[STS GetSessionToken]
        A2 -->|临时凭证<br/>1小时有效| A3[注入到Extension]
        A3 -->|localStorage存储| A4[Extension运行时]
        A4 -->|调用Bedrock| A5[Claude 3 Haiku模型]
    end

    subgraph "Extension流"
        B1[Extension源码] -->|提取| B2[临时目录]
        B2 -->|凭证注入| B3[修改后的Extension]
        B3 -->|ZIP打包| B4[Extension.zip]
        B4 -->|上传| B5[S3 Object]
        B5 -->|引用| B6[Browser Session]
    end

    subgraph "Browser流"
        C1[start_browser_session API] -->|传入S3 URI| C2[AgentCore服务]
        C2 -->|下载Extension| C3[加载到Browser]
        C3 -->|用户访问| C4[网页内容]
        C4 -->|Extension处理| C5[提取文本]
        C5 -->|发送Bedrock| C6[AI摘要]
    end

    style A2 fill:#ff9900
    style A5 fill:#ff9900
    style B5 fill:#569a31
    style C2 fill:#ff9900
```

## Extension技术细节

### Stealth Extension (3.7 KB)

```javascript
// 核心功能实现
const stealthTechniques = {
  // 1. 覆盖navigator.webdriver
  webdriver: () => {
    Object.defineProperty(navigator, 'webdriver', {
      get: () => undefined
    });
  },

  // 2. 修改User-Agent
  userAgent: () => {
    Object.defineProperty(navigator, 'userAgent', {
      get: () => 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...'
    });
  },

  // 3. 随机化浏览器指纹
  fingerprint: () => {
    // Canvas, WebGL, Audio指纹随机化
    // Plugins, Languages等随机化
  },

  // 4. 移除自动化headers
  headers: () => {
    // 移除 'HeadlessChrome', 'Chrome-Lighthouse' 等
  }
};
```

### Bedrock Summary Extension (140 KB)

```javascript
// AWS凭证自动配置
(function() {
  const credentials = {
    accessKeyId: '${AccessKeyId}',
    secretAccessKey: '${SecretAccessKey}',
    sessionToken: '${SessionToken}'
  };
  localStorage.setItem('keys', JSON.stringify(credentials));
})();

// 默认提取规则
const defaultRule = '<p>(.*?)</p>|<h[1-6]>(.*?)</h[1-6]>|<li>(.*?)</li>|<article>(.*?)</article>';

// Bedrock调用
const summaryContent = async (content) => {
  const response = await bedrockClient.invokeModel({
    modelId: 'anthropic.claude-3-haiku-20240307-v1:0',
    body: JSON.stringify({
      anthropic_version: 'bedrock-2023-05-31',
      messages: [{
        role: 'user',
        content: `请总结以下内容: ${content}`
      }],
      max_tokens: 1024
    })
  });
  return response;
};
```

## IAM权限要求

```yaml
Required IAM Permissions:
  STS:
    - sts:GetSessionToken  # 获取临时凭证

  S3:
    - s3:CreateBucket      # 创建bucket
    - s3:PutObject         # 上传extension
    - s3:GetObject         # 下载extension
    - s3:HeadObject        # 验证存在

  Bedrock AgentCore:
    - bedrock-agentcore:StartBrowserSession  # 创建browser
    - bedrock-agentcore:StopBrowserSession   # 关闭browser

  Bedrock:
    - bedrock:InvokeModel  # Extension调用Claude
```

## 限制与约束

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| Extension大小 | 最大10MB | 超过会导致加载失败 |
| Extensions数量 | 最多10个/session | API限制 |
| 临时凭证有效期 | 1小时 | STS GetSessionToken限制 |
| Session超时 | 30分钟 | 可配置，最长2小时 |
| S3 Bucket | 同账户 | 必须与Browser在同一AWS账户 |
| Region | 特定区域 | 不是所有region都支持AgentCore |

## 安全考虑

```mermaid
graph TD
    A[安全机制] --> B[临时凭证]
    A --> C[S3权限控制]
    A --> D[Session超时]

    B --> B1[仅1小时有效]
    B --> B2[无法获取长期凭证]
    B --> B3[定期自动过期]

    C --> C1[Bucket ACL]
    C --> C2[IAM Policy限制]
    C --> C3[同账户访问]

    D --> D1[30分钟自动关闭]
    D --> D2[防止资源泄露]
    D --> D3[成本控制]

    style A fill:#ff6b6b
    style B fill:#4ecdc4
    style C fill:#45b7d1
    style D fill:#96ceb4
```

## 使用场景

1. **Web Scraping**: Stealth Extension绕过检测
2. **内容分析**: Bedrock Summary自动摘要
3. **自动化测试**: 真实浏览器环境测试
4. **AI辅助浏览**: 智能网页分析和总结
5. **企业内部工具**: 定制化Extension部署

## 扩展可能性

- 支持更多Extension类型（广告拦截、隐私保护等）
- 集成更多Bedrock模型（Claude Opus、Sonnet等）
- 添加Extension热更新机制
- 实现Extension版本管理
- 支持Extension配置动态更新

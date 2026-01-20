# 塔罗牌应用后端 API 接口文档

## 概述

本文档描述了塔罗牌应用的所有后端 API 接口。这些接口实现了用户认证、配额管理、塔罗牌解读、历史记录等功能。

**Base URL**: `http://localhost:5000/api`

**认证方式**: Basic Auth（登录接口除外）

**响应格式**: 所有接口均返回 HTTP 200 状态码，成功或失败信息都在响应体中。

---

## 通用规范

### 请求头

所有需要认证的接口都需要在请求头中包含 Authorization：

```
Authorization: Basic <base64(email:password)>
```

**注意**：登录接口 `/api/auth/login` 不需要在请求头中包含 Authorization，但会在请求体中验证凭证。

### 响应格式

#### 成功响应

```json
{
  "success": true,
  "data": { /* 业务数据 */ },
  "message": "可选的成功消息"
}
```

#### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "用户友好的错误信息",
    "details": "详细错误信息（可选）"
  }
}
```

### 错误代码

| 错误代码 | 说明 |
|---------|------|
| `INTERNAL_ERROR` | 服务器内部错误 |
| `INVALID_REQUEST` | 请求参数无效 |
| `UNAUTHORIZED` | 未授权 |
| `FORBIDDEN` | 禁止访问 |
| `NOT_FOUND` | 资源不存在 |
| `INVALID_CREDENTIALS` | 凭证无效 |
| `USER_EXISTS` | 用户已存在 |
| `USER_NOT_FOUND` | 用户不存在 |
| `QUOTA_EXCEEDED` | 配额超限 |
| `INVALID_CARDS` | 无效的塔罗牌 |
| `INVALID_SPREAD` | 无效的牌阵 |
| `INTERPRETATION_FAILED` | 解读失败 |
| `LLM_ERROR` | LLM 错误 |
| `LLM_TIMEOUT` | LLM 超时 |
| `LLM_RATE_LIMIT` | LLM 速率限制 |
| `DATABASE_ERROR` | 数据库错误 |
| `DATABASE_CONNECTION_ERROR` | 数据库连接错误 |
| `NETWORK_ERROR` | 网络错误 |
| `NO_READER` | 无法读取响应流 |
| `INVALID_RESPONSE` | 无效的响应格式 |

---

## 认证相关接口

### 1. 用户登录

**接口地址**: `POST /auth/login`

**是否需要认证**: 否

**请求头**:
```
Content-Type: application/json
Authorization: Basic <base64(email:password)>  // 可选
```

**请求体**:
```json
{
  "email": "demo@mentobai.com",
  "password": "Demo123!"
}
```

**响应示例**（成功）:
```json
{
  "success": true,
  "data": {
    "id": "demo-user-id",
    "username": "Demo User",
    "email": "demo@mentobai.com",
    "isActive": true,
    "isDemo": true,
    "unlimitedQuota": true
  },
  "message": "Login successful"
}
```

**响应示例**（失败）:
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password"
  }
}
```

**说明**:
- 当前版本仅支持演示账号登录
- 演示账号邮箱: `demo@mentobai.com`
- 演示账号密码: `Demo123!`
- 演示账号拥有无限配额

---

### 2. 用户注册

**接口地址**: `POST /auth/register`

**是否需要认证**: 否

**请求头**:
```
Content-Type: application/json
```

**请求体**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应示例**（成功）:
```json
{
  "success": true,
  "data": {
    "id": "user-id-123",
    "username": "user",
    "email": "user@example.com",
    "isActive": true
  },
  "message": "Registration successful"
}
```

**响应示例**（失败）:
```json
{
  "success": false,
  "error": {
    "code": "USER_EXISTS",
    "message": "Email already exists"
  }
}
```

**说明**:
- 用户名自动从邮箱前缀提取（@之前的部分）
- 密码会自动哈希存储

---

### 3. 查询用户配额

**接口地址**: `GET /auth/quota`

**是否需要认证**: 是

**请求头**:
```
Authorization: Basic <base64(email:password)>
```

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| userId | string | 是 | 用户ID |

**响应示例**（演示账号）:
```json
{
  "success": true,
  "data": {
    "remaining": 999999,
    "used": 0,
    "total": "Unlimited",
    "isDemo": true
  }
}
```

**响应示例**（普通账号）:
```json
{
  "success": true,
  "data": {
    "remaining": 2,
    "used": 1,
    "total": 3,
    "isDemo": false
  }
}
```

**说明**:
- 演示账号拥有无限配额
- 普通账号每日免费额度为 3 次
- 配额每天重置

---

## 塔罗牌相关接口

### 4. 塔罗牌解读（流式）

**接口地址**: `POST /tarot/interpret`

**是否需要认证**: 是

**请求头**:
```
Content-Type: application/json
Authorization: Basic <base64(email:password)>
```

**请求体**:
```json
{
  "userId": "demo-user-id",
  "question": "我的工作发展前景如何？",
  "spread": {
    "id": "three",
    "name": "三张牌阵",
    "description": "过去-现在-未来，了解事情的演变",
    "positions": [
      {
        "id": "position1",
        "name": "过去",
        "description": "影响过去的情况"
      },
      {
        "id": "position2",
        "name": "现在",
        "description": "当前的状况"
      },
      {
        "id": "position3",
        "name": "未来",
        "description": "可能的未来结果"
      }
    ]
  },
  "cards": [
    {
      "id": 0,
      "name": "愚人",
      "nameEn": "The Fool",
      "meaning": "新的开始、冒险、天真、自由",
      "reversedMeaning": "鲁莽、轻率、盲目",
      "image": "/images/cards/0.jpg",
      "isReversed": false,
      "imageUrl": "https://example.com/cards/0.jpg",
      "nameJa": "愚者",
      "keywords": ["开始", "冒险", "天真"]
    }
  ]
}
```

**响应格式**:
- 流式响应，使用 `text/event-stream` 格式
- 每个数据块包含部分解读内容
- 成功时返回流式文本，失败时返回 JSON 错误

**成功响应**:
```
（流式文本内容）
```

**错误响应**:
```json
{
  "success": false,
  "error": {
    "code": "QUOTA_EXCEEDED",
    "message": "今日解读次数已用完，请明天再来"
  }
}
```

**说明**:
- 使用 LLM 进行流式解读
- 解读完成后自动保存到数据库
- 自动扣除用户配额
- 支持的牌阵：
  - `single`: 单张牌
  - `three`: 三张牌阵
  - `cross`: 凯尔特十字
  - `diamond`: 钻石牌阵
  - `star`: 六芒星牌阵
- 最多支持 10 张牌

---

### 5. 获取建议问题

**接口地址**: `POST /tarot/suggest`

**是否需要认证**: 否（建议前端在调用时添加认证）

**请求头**:
```
Content-Type: application/json
```

**请求体**:
```json
{
  "question": "我的工作发展前景如何？",
  "cards": [
    {
      "id": 0,
      "name": "愚人",
      "isReversed": false
    }
  ],
  "interpretation": "（完整的解读文本）"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "suggestion": "基于您的工作发展问题，我建议您可以继续探索以下方向：\n\n1. 职业技能提升\n...\n\n鼓励您持续探索！"
  }
}
```

**说明**:
- 根据用户问题和解读结果，推荐 3-4 个相关的探索方向
- 使用 LLM 生成建议

---

### 6. 获取历史记录

**接口地址**: `GET /tarot/history`

**是否需要认证**: 是

**请求头**:
```
Authorization: Basic <base64(email:password)>
```

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| userId | string | 是 | 用户ID |

**响应示例**:
```json
{
  "success": true,
  "data": {
    "interpretations": [
      {
        "id": "interpretation-id-1",
        "userId": "demo-user-id",
        "question": "我的工作发展前景如何？",
        "spreadType": "three",
        "cards": "[{\"id\":0,\"name\":\"愚人\",\"isReversed\":false}]",
        "interpretation": "完整的解读文本...",
        "createdAt": "2024-01-20T03:00:00.000Z"
      }
    ]
  }
}
```

**说明**:
- 返回用户最近的 20 条解读记录
- 按时间倒序排列

---

## 调试接口

### 7. 获取配置信息

**接口地址**: `GET /debug/config`

**是否需要认证**: 否

**响应示例**:
```json
{
  "success": true,
  "data": {
    "timestamp": "2024-01-20T03:00:00.000Z",
    "environment": {
      "NODE_ENV": "development",
      "APP_NAME": "Mentob AI",
      "APP_URL": "http://localhost:5000",
      "APP_VERSION": "1.0.0"
    },
    "llm": {
      "config": {
        "model": "doubao-seed-1-6-thinking-250715",
        "temperature": 0.8,
        "thinking": "enabled",
        "systemPromptLength": 216
      },
      "isValid": true
    },
    "database": {
      "config": {},
      "isValid": true
    },
    "app": {
      "config": {
        "app": {
          "name": "Mentob AI",
          "description": "AI-Powered Tarot Readings"
        },
        "features": {
          "dailyQuota": {
            "free": 3,
            "paid": 999
          },
          "aiInterpretation": {
            "enabled": true
          }
        }
      },
      "isValid": true
    },
    "demoAccount": {
      "enabled": true,
      "email": "demo@mentobai.com",
      "passwordLength": 8,
      "id": "demo-user-id"
    }
  }
}
```

**说明**:
- 返回所有配置信息，包括 LLM、数据库、应用配置等
- 仅用于调试，生产环境应禁用

---

### 8. 获取演示账号信息

**接口地址**: `GET /debug/demo-account`

**是否需要认证**: 否

**响应示例**:
```json
{
  "success": true,
  "data": {
    "enabled": true,
    "email": "demo@mentobai.com",
    "passwordLength": 8,
    "passwordMasked": "********",
    "passwordChars": [
      {
        "char": "D",
        "code": 68
      },
      {
        "char": "e",
        "code": 101
      }
    ],
    "environment": "development",
    "envDemoEmail": "demo@mentobai.com",
    "envDemoPassword": "SET",
    "envDemoEnabled": "true"
  }
}
```

**说明**:
- 返回演示账号的配置信息
- 仅用于调试

---

### 9. 解读功能测试

**接口地址**: `POST /debug/interpret-test`

**是否需要认证**: 否

**请求头**:
```
Content-Type: application/json
```

**请求体**:
```json
{
  "userId": "demo-user-id",
  "skipLLM": false
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "timestamp": "2024-01-20T03:00:00.000Z",
    "tests": [
      {
        "name": "Quota Check",
        "status": "success",
        "duration": 15,
        "data": {
          "canInterpret": true,
          "userId": "demo-user-id",
          "isDemo": true
        }
      },
      {
        "name": "LLM Client",
        "status": "success",
        "duration": 1234,
        "data": {
          "model": "doubao-seed-1-6-thinking-250715",
          "responseLength": 42,
          "chunkCount": 5,
          "responsePreview": "Test successful"
        }
      },
      {
        "name": "Database Write",
        "status": "success",
        "duration": 25,
        "data": {
          "interpretationId": "test-id-1",
          "userId": "demo-user-id-test",
          "question": "Debug test question"
        }
      },
      {
        "name": "Database Read",
        "status": "success",
        "duration": 10,
        "data": {
          "count": 1,
          "hasData": true
        }
      }
    ],
    "totalDuration": 1284,
    "summary": {
      "totalTests": 4,
      "successCount": 4,
      "failedCount": 0
    }
  }
}
```

**说明**:
- 测试配额检查、LLM 客户端、数据库写入、数据库读取等功能
- `skipLLM`: 是否跳过 LLM 测试
- 仅用于调试

---

## 系统接口

### 10. 初始化系统

**接口地址**: `POST /init`

**是否需要认证**: 否

**响应示例**（已存在）:
```json
{
  "success": true,
  "data": {
    "message": "Admin user already exists",
    "user": {
      "id": "admin-id",
      "username": "admin",
      "email": "admin@mentobai.com"
    }
  }
}
```

**响应示例**（新创建）:
```json
{
  "success": true,
  "data": {
    "message": "Admin user created successfully",
    "user": {
      "id": "admin-id",
      "username": "admin",
      "email": "admin@mentobai.com"
    },
    "credentials": {
      "email": "admin@mentobai.com",
      "password": "Admin123!"
    }
  }
}
```

**说明**:
- 创建默认管理员账号
- 仅在首次部署时使用
- 生产环境应禁用

---

## 数据模型

### 用户 (User)

```typescript
interface User {
  id: string;
  username: string;
  email: string;
  password: string;  // 哈希存储
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}
```

### 塔罗牌 (TarotCard)

```typescript
interface TarotCard {
  id: number;
  name: string;
  nameEn: string;
  meaning: string;
  reversedMeaning: string;
  image: string;
  imageUrl?: string;
  nameJa?: string;
  keywords?: string[];
  suit?: 'Wands' | 'Cups' | 'Swords' | 'Pentacles';
  number?: number;
  isReversed: boolean;
}
```

### 牌阵 (Spread)

```typescript
interface Spread {
  id: string;
  name: string;
  description: string;
  positions: SpreadPosition[];
}

interface SpreadPosition {
  id: string;
  name: string;
  description: string;
}
```

### 解读记录 (Interpretation)

```typescript
interface Interpretation {
  id: string;
  userId: string;
  question: string;
  spreadType: string;
  cards: string;  // JSON 字符串
  interpretation: string;
  createdAt: Date;
}
```

### 每日配额 (DailyQuota)

```typescript
interface DailyQuota {
  id: string;
  userId: string;
  date: Date;  // YYYY-MM-DD
  count: number;
  createdAt: Date;
  updatedAt: Date;
}
```

---

## 环境变量

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `NODE_ENV` | 运行环境 | `development` |
| `APP_NAME` | 应用名称 | `Mentob AI` |
| `APP_URL` | 应用URL | `http://localhost:5000` |
| `APP_VERSION` | 应用版本 | `1.0.0` |
| `LLM_MODEL` | LLM 模型 | `doubao-seed-1-6-thinking-250715` |
| `LLM_TEMPERATURE` | LLM 温度参数 | `0.8` |
| `LLM_MAX_TOKENS` | LLM 最大tokens | - |
| `LLM_THINKING` | 是否启用思考 | `enabled` |
| `DAILY_QUOTA_FREE` | 每日免费额度 | `3` |
| `DAILY_QUOTA_PAID` | 每日付费额度 | `999` |
| `AI_INTERPRETATION_ENABLED` | 是否启用AI解读 | `true` |
| `DEMO_ACCOUNT_ENABLED` | 是否启用演示账号 | `true` |
| `DEMO_ACCOUNT_EMAIL` | 演示账号邮箱 | `demo@mentobai.com` |
| `DEMO_ACCOUNT_PASSWORD` | 演示账号密码 | `Demo123!` |

---

## 技术栈

- **框架**: Next.js 16 (App Router)
- **语言**: TypeScript 5
- **数据库**: PostgreSQL + Drizzle ORM
- **AI 服务**: coze-coding-dev-sdk (豆包 LLM)
- **认证**: Basic Auth
- **错误处理**: 统一的错误响应格式

---

## 最佳实践

### 1. 认证

- 使用 Basic Auth 进行身份验证
- 登录成功后，前端应存储凭证并在后续请求中添加 Authorization header
- 密码不应在前端明文存储

### 2. 流式响应

- `/api/tarot/interpret` 使用流式响应
- 前端应使用 `fetch` 的 `body.getReader()` 读取流
- 建议使用打字机效果逐字显示

### 3. 错误处理

- 所有接口都返回 200 状态码
- 成功/失败信息在响应体中
- 前端应根据 `success` 字段判断结果
- 给用户显示友好错误提示

### 4. 配额管理

- 每次解读前检查配额
- 配额每天自动重置
- 演示账号拥有无限配额

### 5. 调试接口

- 生产环境应禁用 `/api/debug/*` 接口
- 通过环境变量控制开关

---

## 示例代码

### 登录

```typescript
const response = await fetch('/api/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'demo@mentobai.com',
    password: 'Demo123!'
  })
});

const result = await response.json();

if (result.success) {
  // 存储用户信息和凭证
  localStorage.setItem('user', JSON.stringify(result.data));
  localStorage.setItem('credentials', btoa('demo@mentobai.com:Demo123!'));
}
```

### 带认证的请求

```typescript
const credentials = localStorage.getItem('credentials');

const response = await fetch('/api/tarot/history?userId=demo-user-id', {
  method: 'GET',
  headers: {
    'Authorization': `Basic ${credentials}`
  }
});

const result = await response.json();
```

### 流式解读

```typescript
const response = await fetch('/api/tarot/interpret', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Basic ${credentials}`
  },
  body: JSON.stringify({
    userId: 'demo-user-id',
    question: '我的工作发展前景如何？',
    spread: { /* 牌阵信息 */ },
    cards: [ /* 卡牌数组 */ ]
  })
});

const reader = response.body?.getReader();
const decoder = new TextDecoder();
let result = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  result += text;
  console.log(text);  // 逐块显示
}
```

---

## 更新日志

### v1.0.0 (2024-01-20)
- 初始版本
- 实现用户认证、配额管理、塔罗牌解读等功能
- 统一错误响应格式
- 支持流式 AI 解读

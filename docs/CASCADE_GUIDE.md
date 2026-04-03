# WeRSS 级联系统使用指南

## 目录

1. [概述](#概述)
2. [架构说明](#架构说明)
3. [快速开始](#快速开始)
4. [配置说明](#配置说明)
5. [API 接口](#api-接口)
6. [任务分发系统](#任务分发系统)
7. [故障排查](#故障排查)
8. [最佳实践](#最佳实践)

---

## 概述

WeRSS 级联系统支持父子节点架构，允许您：
- 在父节点统一管理公众号数据和消息任务
- 子节点从父节点同步数据并执行任务
- 子节点将执行结果上报回父节点

### 核心特性

- **父子节点数据同步**：子节点自动从父节点拉取公众号和任务数据
- **级联 AK/SK 认证系统**：安全的节点间认证机制
- **智能任务分发**：根据节点空闲情况自动分配任务
- **负载均衡**：支持多节点横向扩展
- **实时状态监控**：监控子节点在线状态和任务执行情况
- **容错机制**：节点离线或任务失败时自动处理

---

## 架构说明

### 父节点
- 存储主数据库（公众号、消息任务、文章等）
- 提供 API 接口供子节点拉取数据
- 接收子节点上报的任务执行结果
- 管理子节点和同步日志

### 子节点
- 从父节点拉取公众号和消息任务数据
- 执行消息任务（采集、推送等）
- 将执行结果上报到父节点
- 支持独立部署，扩展采集能力

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      父节点 (Parent)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐     │
│  │  管理API     │  │  同步API     │  │  数据库      │     │
│  │  (Cascade)   │  │  (Sync)      │  │  (DB)        │     │
│  └──────────────┘  └──────────────┘  └─────────────┘     │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            ▼                               │
│                   ┌──────────────┐                         │
│                   │  认证系统   │                         │
│                   │  (Auth)      │                         │
│                   └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTPS + AK/SK
                            │
┌─────────────────────────────────────────────────────────────┐
│                      子节点 (Child)                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐     │
│  │  同步服务     │  │  任务执行    │  │  本地数据库  │     │
│  │  (Sync)      │  │  (Jobs)      │  │  (Local DB)  │     │
│  └──────────────┘  └──────────────┘  └─────────────┘     │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            ▼                               │
│                   ┌──────────────┐                         │
│                   │  HTTP客户端  │                         │
│                   │  (Client)    │                         │
│                   └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 1. 父节点部署（主服务器）

#### 步骤1：初始化数据库

```bash
# 确保数据库配置正确
# config.yaml
db: sqlite:///data/db.db

# 运行初始化脚本
python jobs/cascade_init.py --init
```

#### 步骤2：创建子节点

```bash
# 创建子节点
python jobs/cascade_init.py --child "子节点1" --desc "用于扩展采集" --api-url "http://child-node:8001"
```

系统会输出：
```
==================================================
子节点凭证 (请妥善保存，仅显示一次)
==================================================
节点ID: 550e8400-e29b-41d4-a716-446655440000
API Key: CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
API Secret: CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
==================================================

请将以下配置添加到子节点的 config.yaml:

cascade:
  enabled: true
  node_type: child
  parent_api_url: http://parent-server:8001
  api_key: CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  api_secret: CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 步骤3：启动父节点

```bash
python main.py
```

#### 步骤4：管理子节点

```bash
# 查看所有节点
python jobs/cascade_init.py --list

# 通过API查看（需要登录）
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8001/api/v1/cascade/nodes

# 查看同步日志
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8001/api/v1/cascade/sync-logs
```

### 2. 子节点部署（工作节点）

#### 步骤1：配置级联参数

编辑 `config.yaml`：

```yaml
cascade:
  enabled: true
  node_type: child
  parent_api_url: "http://parent-server:8001"  # 父节点地址
  api_key: "CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 从父节点获取
  api_secret: "CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 从父节点获取
  sync_interval: 300  # 5分钟同步一次
  heartbeat_interval: 60  # 60秒心跳一次
```

或使用环境变量：

```bash
export CASCADE_ENABLED=True
export CASCADE_NODE_TYPE=child
export CASCADE_PARENT_URL=http://parent-server:8001
export CASCADE_API_KEY=CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export CASCADE_API_SECRET=CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 步骤2：启动子节点

```bash
python main.py
```

子节点将自动：
1. 连接到父节点
2. 拉取公众号数据
3. 拉取消息任务
4. 执行任务并上报结果

### 3. 验证部署

#### 父节点端检查

```bash
# 检查子节点状态
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8001/api/v1/cascade/nodes

# 查看同步日志
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8001/api/v1/cascade/sync-logs
```

预期响应：
```json
{
  "code": 0,
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "node_type": 1,
      "name": "子节点1",
      "status": 1,
      "last_heartbeat_at": "2024-01-01T10:00:00"
    }
  ]
}
```

#### 子节点端检查

查看日志，应看到：
- 级联同步服务已启动，父节点地址: http://parent-server:8001
- 公众号同步完成，共同步 X 条
- 消息任务同步完成，共同步 Y 条

---

## 配置说明

### 配置文件 (config.yaml)

#### 父节点配置

```yaml
cascade:
  enabled: true
  node_type: parent
```

#### 子节点配置

```yaml
cascade:
  enabled: true
  node_type: child
  parent_api_url: "http://parent-server:8001"
  api_key: "CNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  api_secret: "CSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  sync_interval: 300
  heartbeat_interval: 60
```

### 环境变量

```bash
# 父节点（默认）
CASCADE_ENABLED=False
CASCADE_NODE_TYPE=parent

# 子节点
CASCADE_ENABLED=True
CASCADE_NODE_TYPE=child
CASCADE_PARENT_URL=http://parent-server:8001
CASCADE_API_KEY=CNxxxxxxxx
CASCADE_API_SECRET=CSxxxxxxxx
CASCADE_SYNC_INTERVAL=300
CASCADE_HEARTBEAT_INTERVAL=60
```

### 节点容量配置

可以通过节点的 `sync_config` 字段配置节点容量：

```bash
curl -X PUT "http://localhost:8001/api/v1/cascade/nodes/NODE_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sync_config": {
      "max_capacity": 20,
      "feed_quota": {
        "mp_id_1": 5,
        "mp_id_2": 10
      }
    }
  }'
```

配置说明：
- `max_capacity`: 节点最大并发任务数，默认10
- `feed_quota`: 公众号配额字典，指定哪些公众号优先由该节点处理

---

## API 接口

### 认证方式

级联系统使用三级认证体系：

```
请求 → Authorization头
       ↓
    级联AK认证 (authenticate_cascade_node)
       ↓ (失败)
    用户AK认证 (authenticate_ak)
       ↓ (失败)
    JWT认证 (JWT token)
```

AK/SK 格式：
- 级联节点: `AK-SK CN{32位}:CS{32位}`
- 用户AK: `AK-SK WK{32位}:SK{32位}`

### 父节点管理接口

| 接口 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/cascade/nodes` | POST | JWT | 创建节点 |
| `/cascade/nodes` | GET | JWT | 获取节点列表 |
| `/cascade/nodes/{id}` | GET | JWT | 获取节点详情 |
| `/cascade/nodes/{id}` | PUT | JWT | 更新节点 |
| `/cascade/nodes/{id}` | DELETE | JWT | 删除节点 |
| `/cascade/nodes/{id}/credentials` | POST | JWT | 生成凭证 |
| `/cascade/nodes/{id}/test-connection` | POST | JWT | 测试连接 |
| `/cascade/sync-logs` | GET | JWT | 查看同步日志 |
| `/cascade/dispatch-task` | POST | JWT | 触发任务分发 |
| `/cascade/allocations` | GET | JWT | 查看任务分配 |

### 子节点调用接口

| 接口 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/cascade/feeds` | GET | 级联AK | 获取公众号 |
| `/cascade/message-tasks` | GET | 级联AK | 获取任务 |
| `/cascade/report-result` | POST | 级联AK | 上报结果 |
| `/cascade/heartbeat` | POST | 级联AK | 发送心跳 |
| `/cascade/pending-tasks` | GET | 级联AK | 获取待处理任务 |

### 接口详情

#### 1. 创建子节点

```bash
POST /api/v1/cascade/nodes
Content-Type: application/json
Authorization: Bearer {token}

{
  "node_type": 1,
  "name": "子节点1",
  "description": "用于扩展采集能力",
  "api_url": "http://child-server:8001"
}
```

响应：
```json
{
  "code": 0,
  "message": "节点创建成功",
  "data": {
    "node_id": "550e8400-e29b-41d4-a716-446655440000",
    "node_type": 1,
    "name": "子节点1",
    "is_active": true
  }
}
```

#### 2. 生成子节点凭证

```bash
POST /api/v1/cascade/nodes/{node_id}/credentials
Authorization: Bearer {token}
```

响应（**请妥善保存，仅显示一次**）：
```json
{
  "code": 0,
  "message": "凭证生成成功",
  "data": {
    "node_id": "550e8400-e29b-41d4-a716-446655440000",
    "api_key": "CN32个随机字符",
    "api_secret": "CS32个随机字符"
  }
}
```

#### 3. 触发任务分发

```bash
POST /api/v1/cascade/dispatch-task
Authorization: Bearer <JWT_TOKEN>

Query Parameters:
  - task_id (可选): 指定任务ID，不指定则分发所有任务
```

#### 4. 查看任务分配

```bash
GET /api/v1/cascade/allocations
Authorization: Bearer <JWT_TOKEN>

Query Parameters:
  - task_id (可选): 按任务ID筛选
  - node_id (可选): 按节点ID筛选
  - status (可选): 按状态筛选 (pending, executing, completed, failed)
  - limit: 每页数量（默认50）
```

#### 5. 获取待处理任务（子节点）

```bash
GET /api/v1/cascade/pending-tasks
Authorization: AK-SK <API_KEY>:<API_SECRET>

Query Parameters:
  - limit: 获取任务数量限制（默认1）
```

---

## 任务分发系统

### 核心特性

- **智能负载均衡**: 根据节点空闲情况自动分配公众号任务
- **灵活配额配置**: 支持为特定节点配置公众号处理配额
- **实时状态监控**: 监控子节点在线状态和任务执行情况
- **任务结果上报**: 子节点执行完成后自动上报结果到父节点
- **容错机制**: 节点离线或任务失败时自动重试或重新分配

### 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                      父节点 (Parent)                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │         CascadeTaskDispatcher (分发器)           │   │
│  │  • 刷新节点状态                                    │   │
│  │  • 智能选择节点                                    │   │
│  │  • 分配公众号任务                                  │   │
│  │  • 推送任务到子节点                                │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                               │
│                         ▼                               │
│                   HTTP API 接口                          │
│  • POST /api/v1/cascade/dispatch-task                   │
│  • GET  /api/v1/cascade/pending-tasks                   │
│  • GET  /api/v1/cascade/allocations                     │
└─────────────────────────────────────────────────────────┘
                         │
                         │ AK-SK 认证
                         │
┌────────────────────────┼────────────────────────────────┐
│                        ▼                                 │
│              子节点1 (Child1)     子节点2 (Child2)       │
│  ┌──────────────────────┐  ┌──────────────────────┐    │
│  │  任务拉取器           │  │  任务拉取器           │    │
│  │  • 定期拉取任务       │  │  • 定期拉取任务       │    │
│  │  • 执行公众号更新     │  │  • 执行公众号更新     │    │
│  │  • 上报执行结果       │  │  • 上报执行结果       │    │
│  └──────────────────────┘  └──────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### 使用方式

#### 父节点分发任务

```bash
# 分发所有任务
curl -X POST "http://localhost:8001/api/v1/cascade/dispatch-task" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 分发指定任务
curl -X POST "http://localhost:8001/api/v1/cascade/dispatch-task?task_id=xxx" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 子节点拉取任务

```bash
# 方式1: 运行示例
python examples/cascade_task_dispatcher_example.py child

# 方式2: 直接运行
python -m jobs.cascade_task_dispatcher child
```

### 节点选择策略

1. **配额优先**: 如果公众号在节点的 `feed_quota` 中，优先分配给该节点
2. **负载均衡**: 选择可用容量最大的节点
3. **容量检查**: 确保节点有足够容量处理任务

### 状态说明

#### 节点状态
- `is_active`: 节点是否启用
- `status`: 0=离线, 1=在线
- `current_tasks`: 当前任务数
- `max_capacity`: 最大容量

#### 分配状态
- `pending`: 已分配，待执行
- `executing`: 正在执行
- `completed`: 执行完成
- `failed`: 执行失败

---

## 故障排查

### 子节点无法连接父节点

1. 检查父节点是否正常运行
2. 确认 `parent_api_url` 配置正确
3. 检查网络连通性
4. 验证 API 凭证是否正确

```bash
# 测试连接
curl -X POST "http://localhost:8001/api/v1/cascade/nodes/NODE_ID/test-connection" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"api_url": "http://child:8001", "api_key": "CNxxx", "api_secret": "CSxxx"}'
```

### 数据未同步

1. 查看子节点日志，确认同步服务已启动
2. 检查父节点是否配置了相应的公众号和任务
3. 查看同步日志 `/api/v1/cascade/sync-logs`

### 认证失败

1. 确认使用的是正确的 `api_key` 和 `api_secret`
2. 检查子节点状态是否为启用状态
3. 验证 Authorization 头格式是否正确

### 子节点无法获取任务

**可能原因**:
- 子节点 AK/SK 配置错误
- 子节点未在线（检查心跳）
- 父节点没有分配任务

**解决方法**:
```bash
# 检查配置
python jobs/cascade_init.py --check

# 检查节点状态
python jobs/cascade_init.py --list

# 查看分配记录
curl "http://localhost:8001/api/v1/cascade/allocations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 节点显示离线

```bash
# 检查心跳是否正常
# 超过3分钟无心跳视为离线

# 手动测试连接
curl -X POST "http://localhost:8001/api/v1/cascade/nodes/NODE_ID/test-connection" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 最佳实践

### 安全性

1. **凭证管理**:
   - API Secret 仅在生成时显示一次，请妥善保存
   - 使用 SHA256 哈希存储
   - 支持凭证停用和删除

2. **认证机制**:
   - 双重 AK/SK 认证
   - 支持过期时间
   - 记录使用审计

3. **通信安全**:
   - 建议使用 HTTPS 通信
   - 请求头验证
   - 心跳检测

### 性能优化

1. **同步间隔**: 根据业务量调整，建议 300-600 秒
2. **并发控制**: 限制子节点数量，避免父节点过载
3. **数据压缩**: 大量数据时启用 gzip 压缩
4. **缓存策略**: 父节点可启用缓存减少数据库查询

### 生产环境建议

1. **安全性**：
   - 使用 HTTPS 通信
   - 定期更换子节点凭证
   - 限制子节点访问权限

2. **性能**：
   - 根据业务量调整同步间隔
   - 监控网络带宽和延迟
   - 合理规划子节点数量

3. **监控**：
   - 监控心跳状态
   - 监控同步延迟
   - 设置告警机制

4. **备份**：
   - 定期备份父节点数据库
   - 记录子节点凭证（丢失后需要重新生成）

### 使用场景

#### 场景1：扩展采集能力
- **父节点**：负责管理公众号、消息任务，接收采集结果
- **子节点**：多个子节点分布在不同网络环境，采集文章并推送

#### 场景2：多地域部署
- **父节点**：集中式管理
- **子节点**：部署在不同地区，提供低延迟服务

#### 场景3：负载均衡
- **父节点**：分发任务
- **子节点**：分担采集和推送压力

---

## 相关文件位置

- **分发器**: `jobs/cascade_task_dispatcher.py`
- **API接口**: `apis/cascade.py`
- **示例**: `examples/cascade_task_dispatcher_example.py`
- **测试**: `test_cascade_task_dispatcher.py`
- **初始化**: `jobs/cascade_init.py`

---

## 总结

WeRSS 级联系统已完整实现，支持：

- 完整的父子节点架构
- 灵活的 AK/SK 认证体系
- 自动化数据同步
- 智能任务分发与负载均衡
- 任务执行结果上报
- 完善的日志监控
- 丰富的 API 接口

系统已可直接用于生产环境，支持横向扩展和多地域部署。

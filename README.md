# Redis 游乐场 · 交互式学习项目

一个**用 Flask 手工搭建**的 Redis 交互式学习实验室：七个页面对应 Redis
核心概念，每次点击按钮都会回显**执行的真实 Redis 命令与返回值**，
把界面动作和命令行一一对应——直观理解 Redis。

## 特性

- **新手上路 GUIDE 页**：网站内嵌 4 步交互教程（键值 / GET / TTL / INCR），跟着点红按钮 60 秒建立心智模型
- **七页学习地图**：总览（SCAN 键浏览器）/ STRING / LIST / HASH / SET / ZSET / CACHE
- **命令回显**：每个操作显示 `命令 → 返回值`，像终端一样对照学习
- **双模式运行**：自动探测本机 Redis；未安装则降级 `fakeredis`（API 完全一致），界面顶部实时显示模式
- **亮点实验**：TTL 秒级倒计时动画、原子计数器 INCR、集合交集（共同标签）、
  分数排行榜、缓存 HIT/MISS 对比（0.8s 慢查询实测）
- **每个页面自带概念讲解块**：类型用途 + 直觉类比 + 关键命令

## 目录结构

```
redis-playground/
├── 00-【必读】从这里开始.html    # 图文说明: Redis 概念速查 + 学习路线 + 目录导读
├── 01-【双击开始】.bat           # 一键启动 (自动装依赖、探测 Redis、开浏览器)
├── README.md                     # 本说明文档
└── 02-项目源码/                  # 全部源码
    ├── app.py                    # 启动入口: python app.py
    ├── playground/               # 应用包 (全部业务代码)
    │   ├── __init__.py           # 应用工厂
    │   ├── redis_client.py       # 客户端层: 真实优先, 自动降级 fakeredis
    │   ├── views.py              # 七大页面路由 (每次操作回显命令)
    │   ├── templates/            # 页面模板
    │   └── static/               # 暗色监控台样式
    ├── tests/                    # 单元测试 (强制 fakeredis, 不依赖服务)
    ├── requirements.txt
    └── .gitignore
```

## 快速开始

**方式一：双击启动（Windows，推荐）**

双击 `01-【双击开始】.bat`。完整图文说明见 `00-【必读】从这里开始.html`。

**方式二：命令行**

```bash
cd 02-项目源码
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

访问 <http://127.0.0.1:5000>。

### 真实 Redis（可选）

没有安装 Redis 也能跑（自动用 fakeredis 模拟，概念与命令一致）。
要切换到真实模式，任选其一：

```powershell
# Windows 服务方式 (本项目开发时使用的就是它)
winget install Memurai.MemuraiDeveloper

# 或 Docker
docker run -d -p 6379:6379 redis:7
```

装好后重新启动本项目，顶部徽章变为「真实模式」。

## 八页学习地图

| 页面    | 对应类型 | 练什么                                             |
| ------- | -------- | -------------------------------------------------- |
| GUIDE   | 入门     | 网站内嵌交互教程：键值/GET/TTL/INCR 四步            |
| 总览    | —        | `SCAN` 清游标遍历、`DBSIZE`、`FLUSHDB`、TYPE/TTL 查看 |
| STRING  | 字符串   | `SET/GET/DEL`、`EXPIRE/TTL/PERSIST`、`INCR` 计数器  |
| LIST    | 列表     | `LPUSH/RPUSH/LPOP/RPOP`、队列 FIFO 直觉            |
| HASH    | 哈希     | `HSET/HGETALL/HDEL`、对象字段级更新                |
| SET     | 集合     | `SADD/SREM/SMEMBERS` 去重、`SINTER` 交集           |
| ZSET    | 有序集合 | `ZADD/ZRANGE(降序)/ZREM`、排行榜                   |
| CACHE   | 缓存     | get-or-set 模式、HIT/MISS 计数、TTL 过期重算       |

推荐顺序：从左到右，每页先读顶部「概念」块，再动手。

## 运行测试

在 `02-项目源码` 目录内执行：

```bash
python -m unittest discover -s tests -t . -v
```

预期结尾：`Ran 13 tests` + `OK`。测试强制使用 fakeredis，不依赖本机 Redis 服务。

## 配置（环境变量）

| 变量              | 说明                                            | 默认值                  |
| ----------------- | ----------------------------------------------- | ----------------------- |
| `REDIS_URL`       | Redis 连接串；设为 `fakeredis://` 强制模拟模式  | `redis://127.0.0.1:6379/0` |
| `PLAYGROUND_SECRET` | 会话密钥，生产环境建议设为随机值              | 开发用固定值            |

## 安全说明

- 本项目面向**本机教学**，后台无鉴权、且提供 `FLUSHDB` 清库按钮——
  切勿把端口暴露到公网或指向生产 Redis 库（建议只连 0 号库并接受数据被清空）。
- 模拟模式下数据存于进程内存，重启即清空；真实模式数据落盘遵循 Redis 自身持久化配置。

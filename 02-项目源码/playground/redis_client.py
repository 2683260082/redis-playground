# -*- coding: utf-8 -*-
"""Redis 客户端层: 优先连接真实服务器, 不可用时自动降级 fakeredis。

设计说明:
    1. 默认连接 redis://127.0.0.1:6379/0, 可用环境变量 REDIS_URL 覆盖。
    2. REDIS_URL=fakeredis:// 时强制使用内存模拟器 (单元测试用)。
    3. 真实服务器不可达时自动降级, 界面顶部会显示当前模式, 便于教学:
       命令与 API 完全一致, 连上真实 Redis 无需改任何代码。
"""
import os

import fakeredis
import redis

DEFAULT_URL = "redis://127.0.0.1:6379/0"

_client = None
_mode = None  # "真实" | "模拟"


def get_redis():
    """获取全局共享的 Redis 客户端 (进程内单例)"""
    global _client, _mode
    if _client is not None:
        return _client

    url = os.environ.get("REDIS_URL") or DEFAULT_URL

    if url.startswith("fakeredis://"):
        _client = fakeredis.FakeRedis(decode_responses=True)
        _mode = "模拟"
        return _client

    try:
        client = redis.from_url(
            url, decode_responses=True, socket_connect_timeout=1,
            socket_timeout=2,
        )
        client.ping()
        _client, _mode = client, "真实"
    except Exception:
        _client = fakeredis.FakeRedis(decode_responses=True)
        _mode = "模拟"
    return _client


def get_mode():
    """当前模式: 真实 / 模拟 (先确保客户端已初始化)"""
    get_redis()
    return _mode


def server_info():
    """汇总服务器状态供总览页展示, 任何字段缺失都不致命"""
    r = get_redis()
    info = {}
    try:
        for section in ("server", "memory", "clients"):
            info.update(r.info(section) or {})
    except Exception:
        pass
    try:
        info["dbsize"] = r.dbsize()
    except Exception:
        info["dbsize"] = "?"
    info["mode"] = get_mode()
    info["version"] = (
        info.get("redis_version")
        or info.get("memurai_version")
        or ("fakeredis (内存模拟)" if get_mode() == "模拟" else "unknown")
    )
    info["used_memory_human"] = info.get("used_memory_human", "-")
    info["connected_clients"] = info.get("connected_clients", "-")
    return info


def scan_keys(limit=100):
    """SCAN 遍历键 (生产安全的游标遍历, 不用 KEYS), 返回 [(键, 类型, TTL)]"""
    r = get_redis()
    found = []
    cursor = 0
    while True:
        cursor, batch = r.scan(cursor=cursor, count=50)
        for key in batch:
            ktype = r.type(key)
            ttl = r.ttl(key)  # -1=永不过期  -2=键不存在
            found.append((key, ktype, ttl))
            if len(found) >= limit:
                return found
        if cursor == 0:
            return found


def flash_payload(value, limit=120):
    """把返回值截断成一行, 用于命令回显"""
    s = value if isinstance(value, str) else repr(value)
    s = s.replace("\n", "\\n")
    return s if len(s) <= limit else s[:limit] + "…"

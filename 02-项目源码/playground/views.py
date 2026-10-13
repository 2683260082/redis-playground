# -*- coding: utf-8 -*-
"""七大页面路由。

教学设计: 每次操作都用 flash 回显「执行的 Redis 命令 → 返回值」,
让使用者把界面动作和真实命令一一对应起来。
"""
import hashlib
import time

from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template,
    request, url_for,
)

from . import redis_client as rc

bp = Blueprint("views", __name__)


# ----------------------------- 公共工具 -----------------------------
def _r():
    return rc.get_redis()


def flash_cmd(cmd, result):
    """回显「命令 → 返回」, 样式为终端行"""
    flash(f"{cmd}  →  {rc.flash_payload(result)}", "cmd")


def _key(required=True):
    key = (request.form.get("key") or "").strip()
    if not key and required:
        flash("键 (key) 不能为空", "error")
        return None
    return key


def _back(endpoint, **kwargs):
    return redirect(url_for(endpoint, **kwargs))


# ----------------------------- 总览 -----------------------------
@bp.route("/")
def index():
    info = rc.server_info()
    keys = rc.scan_keys(limit=100)
    return render_template("index.html", info=info, keys=keys)


@bp.route("/guide")
def guide():
    """新手上路: 交互式四步教程 (键值/GET/TTL/INCR)"""
    return render_template("guide.html")


@bp.route("/flush", methods=["POST"])
def flush():
    try:
        _r().flushdb()
        flash_cmd("FLUSHDB", "OK")
        flash("0 号库已清空", "ok")
    except Exception as e:
        flash(f"失败: {e}", "error")
    return _back("views.index")


@bp.route("/api/ttl")
def api_ttl():
    key = (request.args.get("key") or "").strip()
    r = _r()
    if not key or not r.exists(key):
        return jsonify({"exists": False, "ttl": -2})
    return jsonify({"exists": True, "ttl": r.ttl(key)})


# ----------------------------- 字符串 STRING -----------------------------
@bp.route("/string")
def string_page():
    key = (request.args.get("key") or "").strip()
    r = _r()
    view = None
    if key and r.exists(key):
        view = {
            "key": key,
            "type": r.type(key),
            "value": r.get(key) if r.type(key) == "string" else None,
            "ttl": r.ttl(key),
        }
    elif key:
        view = {"key": key, "type": "none", "value": None, "ttl": -2}
    return render_template("string.html", view=view)


@bp.route("/string/set", methods=["POST"])
def string_set():
    key = _key()
    if key is None:
        return _back("views.string_page")
    value = (request.form.get("value") or "").strip()
    if not value:
        flash("值 (value) 不能为空", "error")
        return _back("views.string_page", key=key)
    ttl = request.form.get("ttl", type=int) or 0
    try:
        r = _r()
        if ttl > 0:
            r.set(key, value, ex=ttl)
            flash_cmd(f'SET {key} "{value}" EX {ttl}', "OK")
        else:
            r.set(key, value)
            flash_cmd(f'SET {key} "{value}"', "OK")
    except Exception as e:
        flash(f"命令失败: {e}", "error")
    return _back("views.string_page", key=key)


@bp.route("/string/get", methods=["POST"])
def string_get():
    key = _key()
    if key is None:
        return _back("views.string_page")
    return _back("views.string_page", key=key)


@bp.route("/string/incr", methods=["POST"])
def string_incr():
    key = _key() or "visit:count"
    try:
        val = _r().incr(key)
        flash_cmd(f"INCR {key}", str(val))
    except Exception as e:
        flash(f"INCR 失败 (该键的值必须是整数): {e}", "error")
    return _back("views.string_page", key=key)


@bp.route("/string/expire", methods=["POST"])
def string_expire():
    key = _key()
    if key is None:
        return _back("views.string_page")
    ttl = request.form.get("ttl", type=int) or 60
    try:
        ok = _r().expire(key, ttl)
        flash_cmd(f"EXPIRE {key} {ttl}", "1" if ok else "0 (键不存在)")
    except Exception as e:
        flash(f"失败: {e}", "error")
    return _back("views.string_page", key=key)


@bp.route("/string/persist", methods=["POST"])
def string_persist():
    key = _key()
    if key is None:
        return _back("views.string_page")
    try:
        ok = _r().persist(key)
        flash_cmd(f"PERSIST {key}", "1 (已取消过期)" if ok else "0 (无过期时间)")
    except Exception as e:
        flash(f"失败: {e}", "error")
    return _back("views.string_page", key=key)


@bp.route("/string/del", methods=["POST"])
def string_del():
    key = _key()
    if key is None:
        return _back("views.string_page")
    try:
        n = _r().delete(key)
        flash_cmd(f"DEL {key}", str(n))
    except Exception as e:
        flash(f"失败: {e}", "error")
    return _back("views.string_page")


# ----------------------------- 列表 LIST -----------------------------
@bp.route("/list")
def list_page():
    key = (request.args.get("key") or "").strip() or "demo:queue"
    r = _r()
    ktype = r.type(key)
    items = r.lrange(key, 0, 29) if ktype == "list" else []
    length = r.llen(key) if ktype == "list" else 0
    return render_template(
        "list.html", key=key, items=items, length=length, ktype=ktype,
    )


@bp.route("/list/push", methods=["POST"])
def list_push():
    key = _key() or "demo:queue"
    value = (request.form.get("value") or "").strip()
    side = request.form.get("side", "right")
    if not value:
        flash("元素不能为空", "error")
        return _back("views.list_page", key=key)
    try:
        r = _r()
        if side == "left":
            r.lpush(key, value)
            flash_cmd(f"LPUSH {key} {value}", str(r.llen(key)))
        else:
            r.rpush(key, value)
            flash_cmd(f"RPUSH {key} {value}", str(r.llen(key)))
    except Exception as e:
        flash(f"命令失败 (该键可能不是 list 类型): {e}", "error")
    return _back("views.list_page", key=key)


@bp.route("/list/pop", methods=["POST"])
def list_pop():
    key = _key() or "demo:queue"
    side = request.form.get("side", "left")
    try:
        r = _r()
        if side == "left":
            val = r.lpop(key)
            cmd = f"LPOP {key}"
        else:
            val = r.rpop(key)
            cmd = f"RPOP {key}"
        flash_cmd(cmd, val if val is not None else "(nil) 列表已空")
    except Exception as e:
        flash(f"命令失败: {e}", "error")
    return _back("views.list_page", key=key)


@bp.route("/list/del", methods=["POST"])
def list_del():
    key = _key() or "demo:queue"
    try:
        n = _r().delete(key)
        flash_cmd(f"DEL {key}", str(n))
    except Exception as e:
        flash(f"失败: {e}", "error")
    return _back("views.list_page", key=key)


# ----------------------------- 哈希 HASH -----------------------------
@bp.route("/hash")
def hash_page():
    key = (request.args.get("key") or "").strip() or "demo:user"
    r = _r()
    ktype = r.type(key)
    data = r.hgetall(key) if ktype == "hash" else {}
    return render_template("hash.html", key=key, data=data, ktype=ktype)


@bp.route("/hash/set", methods=["POST"])
def hash_set():
    key = _key() or "demo:user"
    field = (request.form.get("field") or "").strip()
    value = (request.form.get("value") or "").strip()
    if not field:
        flash("字段 (field) 不能为空", "error")
        return _back("views.hash_page", key=key)
    try:
        r = _r()
        r.hset(key, field, value)
        flash_cmd(f"HSET {key} {field} {value}", "1")
    except Exception as e:
        flash(f"命令失败 (该键可能不是 hash 类型): {e}", "error")
    return _back("views.hash_page", key=key)


@bp.route("/hash/del", methods=["POST"])
def hash_del():
    key = _key() or "demo:user"
    field = (request.form.get("field") or "").strip()
    try:
        n = _r().hdel(key, field)
        flash_cmd(f"HDEL {key} {field}", str(n))
    except Exception as e:
        flash(f"失败: {e}", "error")
    return _back("views.hash_page", key=key)


# ----------------------------- 集合 SET -----------------------------
@bp.route("/set")
def set_page():
    key = (request.args.get("key") or "").strip() or "demo:tags"
    key2 = (request.args.get("key2") or "").strip()
    r = _r()
    ktype = r.type(key)
    members = sorted(r.smembers(key)) if ktype == "set" else []
    inter = None
    if key2 and ktype == "set" and r.type(key2) == "set":
        inter = sorted(r.sinter(key, key2))
    return render_template(
        "set.html", key=key, key2=key2, members=members, ktype=ktype,
        inter=inter,
    )


@bp.route("/set/add", methods=["POST"])
def set_add():
    key = _key() or "demo:tags"
    raw = (request.form.get("members") or "").strip()
    items = [m.strip() for m in raw.replace("，", ",").split(",") if m.strip()]
    if not items:
        flash("至少输入一个元素 (逗号分隔)", "error")
        return _back("views.set_page", key=key)
    try:
        r = _r()
        added = r.sadd(key, *items)
        flash_cmd(
            f"SADD {key} {' '.join(items)}",
            f"{added} (新增个数; 重复元素不会加, 返回 0)",
        )
    except Exception as e:
        flash(f"命令失败 (该键可能不是 set 类型): {e}", "error")
    return _back("views.set_page", key=key)


@bp.route("/set/del", methods=["POST"])
def set_del():
    key = _key() or "demo:tags"
    member = (request.form.get("member") or "").strip()
    try:
        n = _r().srem(key, member)
        flash_cmd(f"SREM {key} {member}", str(n))
    except Exception as e:
        flash(f"失败: {e}", "error")
    return _back("views.set_page", key=key)


# ----------------------------- 有序集合 ZSET -----------------------------
@bp.route("/zset")
def zset_page():
    key = (request.args.get("key") or "").strip() or "demo:leaderboard"
    r = _r()
    ktype = r.type(key)
    rows = (
        [(m, float(s)) for m, s in
         r.zrange(key, 0, 19, withscores=True, desc=True)]
        if ktype == "zset" else []
    )
    max_score = max((s for _, s in rows), default=1) or 1
    return render_template(
        "zset.html", key=key, rows=rows, max_score=max_score, ktype=ktype,
    )


@bp.route("/zset/add", methods=["POST"])
def zset_add():
    key = _key() or "demo:leaderboard"
    member = (request.form.get("member") or "").strip()
    score = request.form.get("score", type=float)
    if not member or score is None:
        flash("成员和分数都不能为空", "error")
        return _back("views.zset_page", key=key)
    try:
        r = _r()
        r.zadd(key, {member: score})
        flash_cmd(f"ZADD {key} {score} {member}", "1")
    except Exception as e:
        flash(f"命令失败 (该键可能不是 zset 类型): {e}", "error")
    return _back("views.zset_page", key=key)


@bp.route("/zset/seed", methods=["POST"])
def zset_seed():
    key = _key() or "demo:leaderboard"
    data = {
        "前端组": 9600.0, "后端组": 8900.0, "测试组": 7200.0,
        "产品组": 6100.0, "运维组": 5300.0,
    }
    try:
        r = _r()
        r.zadd(key, data)
        flash_cmd(f"ZADD {key} (批量 5 条)", str(len(data)))
        flash("已写入演示排行榜, 按分数从高到低排列", "ok")
    except Exception as e:
        flash(f"失败: {e}", "error")
    return _back("views.zset_page", key=key)


@bp.route("/zset/del", methods=["POST"])
def zset_del():
    key = _key() or "demo:leaderboard"
    member = (request.form.get("member") or "").strip()
    try:
        n = _r().zrem(key, member)
        flash_cmd(f"ZREM {key} {member}", str(n))
    except Exception as e:
        flash(f"失败: {e}", "error")
    return _back("views.zset_page", key=key)


# ----------------------------- 缓存 CACHE -----------------------------
CACHE_KEY = "cache:lesson:answer"
HITS_KEY = "cache:hits"
MISSES_KEY = "cache:misses"


def _expensive_lesson():
    """模拟一次慢查询: 固定 0.8 秒 CPU/IO 等待 + 确定性结果"""
    time.sleep(0.8)
    digest = hashlib.sha256(b"redis-playground-lesson").hexdigest()[:12]
    return f"结课报告编号-{digest}"


@bp.route("/cache")
def cache_page():
    r = _r()
    hits = int(r.get(HITS_KEY) or 0)
    misses = int(r.get(MISSES_KEY) or 0)
    cached = r.get(CACHE_KEY)
    remaining = r.ttl(CACHE_KEY) if cached is not None else -2
    total = hits + misses
    rate = f"{hits / total * 100:.0f}%" if total else "—"
    return render_template(
        "cache.html", hits=hits, misses=misses, rate=rate,
        cached=cached, remaining=remaining,
    )


@bp.route("/cache/run", methods=["POST"])
def cache_run():
    mode = request.form.get("mode", "cached")
    r = _r()
    try:
        if mode == "bypass":
            start = time.perf_counter()
            value = _expensive_lesson()
            ms = (time.perf_counter() - start) * 1000
            flash_cmd(
                "(绕过缓存, 直接执行慢查询)",
                f"{value} · 耗时 {ms:.0f} ms",
            )
        else:
            start = time.perf_counter()
            value = r.get(CACHE_KEY)
            if value is not None:
                r.incr(HITS_KEY)
                ms = (time.perf_counter() - start) * 1000
                flash_cmd(
                    f"GET {CACHE_KEY}",
                    f"{value} · 命中 HIT · 耗时 {ms:.1f} ms",
                )
            else:
                r.incr(MISSES_KEY)
                value = _expensive_lesson()
                r.set(CACHE_KEY, value, ex=30)
                ms = (time.perf_counter() - start) * 1000
                flash_cmd(
                    f"GET {CACHE_KEY} → (nil) 后执行慢查询并 SETEX 30",
                    f"未命中 MISS · 耗时 {ms:.0f} ms",
                )
    except Exception as e:
        flash(f"失败: {e}", "error")
    return _back("views.cache_page")


@bp.route("/cache/reset", methods=["POST"])
def cache_reset():
    try:
        r = _r()
        r.delete(CACHE_KEY, HITS_KEY, MISSES_KEY)
        flash_cmd(f"DEL {CACHE_KEY} {HITS_KEY} {MISSES_KEY}", "3")
        flash("缓存与计数已重置", "ok")
    except Exception as e:
        flash(f"失败: {e}", "error")
    return _back("views.cache_page")

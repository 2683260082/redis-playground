# -*- coding: utf-8 -*-
"""Redis 游乐场 - 启动入口 (业务代码在 playground/ 包内)。

启动方式:
    python app.py                 # 开发模式, http://127.0.0.1:5000

环境变量 (详见 README):
    REDIS_URL          默认 redis://127.0.0.1:6379/0
                       设为 fakeredis:// 可强制使用内存模拟器
"""
import sys

from playground import create_app

app = create_app()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    from playground import redis_client
    print("=" * 52)
    print("Redis 游乐场已启动: http://127.0.0.1:5000")
    print(f"当前模式: {redis_client.get_mode()} Redis")
    if redis_client.get_mode() == "模拟":
        print("提示: 未检测到真实 Redis, 已降级 fakeredis (API 一致)")
    print("=" * 52)
    app.run(debug=True, use_reloader=False, host="127.0.0.1", port=5000)

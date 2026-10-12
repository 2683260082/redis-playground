# -*- coding: utf-8 -*-
"""Redis 游乐场应用包。

包内分工:
    __init__.py      应用工厂、蓝图装配
    redis_client.py  Redis 客户端 (真实优先, 自动降级 fakeredis)
    views.py         七大页面路由: 总览/字符串/列表/哈希/集合/有序集合/缓存
    templates/       页面模板
    static/          样式与脚本
"""
from datetime import datetime

from flask import Flask, render_template

from . import redis_client, views


def create_app(test_config=None):
    """应用工厂: 配置 → 蓝图 → 错误页"""
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os_safe_secret(),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)

    app.register_blueprint(views.bp)

    # 模板全局量: 当前 Redis 模式与页脚年份
    app.context_processor(lambda: {
        "redis_mode": redis_client.get_mode(),
        "now_year": datetime.now().year,
    })

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app


def os_safe_secret():
    import os
    return os.environ.get("PLAYGROUND_SECRET") or "redis-playground-dev-key"

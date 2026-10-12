# -*- coding: utf-8 -*-
"""Redis 游乐场单元测试。

强制使用 fakeredis (API 与真实 Redis 完全一致), 不依赖本机服务,
且每个用例开始前清库, 互不污染。

运行方式 (在 02-项目源码 目录内执行):
    python -m unittest discover -s tests -t . -v
"""
import os
import sys
import unittest

# 导入应用前锁定模拟模式
os.environ["REDIS_URL"] = "fakeredis://"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playground import create_app  # noqa: E402
from playground import redis_client  # noqa: E402


class PlaygroundTestCase(unittest.TestCase):
    """七大页面 + 各数据结构操作的集成测试"""

    @classmethod
    def setUpClass(cls):
        redis_client._client = None  # 重置单例, 确保读到环境变量
        redis_client._mode = None
        cls.app = create_app({"TESTING": True})

    def setUp(self):
        self.client = self.app.test_client()
        redis_client.get_redis().flushdb()

    # ----------------------------- 基础页面 -----------------------------
    def test_mode_is_simulated(self):
        self.assertEqual(redis_client.get_mode(), "模拟")

    def test_all_pages_render(self):
        for path in ("/", "/string", "/list", "/hash", "/set", "/zset", "/cache"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_unknown_page_404(self):
        self.assertEqual(self.client.get("/no-such-page").status_code, 404)

    # ----------------------------- STRING -----------------------------
    def test_string_set_get_roundtrip(self):
        resp = self.client.post(
            "/string/set",
            data={"key": "k1", "value": "hello-redis", "ttl": "0"},
            follow_redirects=True,
        )
        html = resp.get_data(as_text=True)
        self.assertIn("hello-redis", html)
        # 命令回显包含执行的 SET
        self.assertIn("SET k1", html)

    def test_incr_accumulates(self):
        for _ in range(2):
            self.client.post(
                "/string/incr", data={"key": "cnt"}, follow_redirects=True,
            )
        self.assertEqual(redis_client.get_redis().get("cnt"), "2")

    def test_ttl_countdown_api(self):
        redis_client.get_redis().set("tmp", "x", ex=42)
        data = self.client.get("/api/ttl?key=tmp").get_json()
        self.assertTrue(data["exists"])
        self.assertGreater(data["ttl"], 0)
        self.assertLessEqual(data["ttl"], 42)

    # ----------------------------- LIST -----------------------------
    def test_list_push_pop_fifo(self):
        for value in ("a", "b"):
            self.client.post(
                "/list/push",
                data={"key": "q", "value": value, "side": "right"},
                follow_redirects=True,
            )
        r = redis_client.get_redis()
        self.assertEqual(r.lrange("q", 0, -1), ["a", "b"])
        # LPOP 从左弹出 → 先进先出
        self.client.post(
            "/list/pop", data={"key": "q", "side": "left"},
            follow_redirects=True,
        )
        self.assertEqual(r.lrange("q", 0, -1), ["b"])

    # ----------------------------- HASH -----------------------------
    def test_hash_set_and_display(self):
        self.client.post(
            "/hash/set",
            data={"key": "u1", "field": "name", "value": "张三"},
            follow_redirects=True,
        )
        html = self.client.get("/hash?key=u1").get_data(as_text=True)
        self.assertIn("张三", html)
        self.assertEqual(redis_client.get_redis().hget("u1", "name"), "张三")

    # ----------------------------- SET -----------------------------
    def test_set_dedup_and_intersection(self):
        self.client.post(
            "/set/add",
            data={"key": "A", "members": "x, y, z"},
            follow_redirects=True,
        )
        # 重复添加不计数
        self.client.post(
            "/set/add", data={"key": "A", "members": "x"},
            follow_redirects=True,
        )
        self.assertEqual(redis_client.get_redis().scard("A"), 3)

        redis_client.get_redis().sadd("B", "y", "z", "w")
        html = self.client.get("/set?key=A&key2=B").get_data(as_text=True)
        self.assertIn('class="chip inter">y<', html)
        self.assertIn('class="chip inter">z<', html)
        self.assertNotIn('class="chip inter">w<', html)

    # ----------------------------- ZSET -----------------------------
    def test_zset_ranking_desc_by_score(self):
        self.client.post(
            "/zset/add",
            data={"key": "lb", "member": "低分选手", "score": "10"},
            follow_redirects=True,
        )
        self.client.post(
            "/zset/add",
            data={"key": "lb", "member": "高分选手", "score": "99"},
            follow_redirects=True,
        )
        # 展示必须按分数从高到低 (desc=True)
        html = self.client.get("/zset?key=lb").get_data(as_text=True)
        self.assertLess(
            html.find("高分选手"), html.find("低分选手"),
            "排行榜应按分数降序展示",
        )

    # ----------------------------- CACHE -----------------------------
    def test_cache_miss_then_hit(self):
        # 第一次: MISS (执行慢查询并写回)
        self.client.post(
            "/cache/run", data={"mode": "cached"}, follow_redirects=True,
        )
        r = redis_client.get_redis()
        self.assertEqual(int(r.get("cache:misses") or 0), 1)
        self.assertEqual(int(r.get("cache:hits") or 0), 0)
        # 第二次: HIT (直接读缓存)
        self.client.post(
            "/cache/run", data={"mode": "cached"}, follow_redirects=True,
        )
        self.assertEqual(int(r.get("cache:hits") or 0), 1)
        # 绕过缓存: 不计入命中/未命中计数
        self.client.post(
            "/cache/run", data={"mode": "bypass"}, follow_redirects=True,
        )
        self.assertEqual(int(r.get("cache:misses") or 0), 1)

    # ----------------------------- 管理 -----------------------------
    def test_flushdb_clears_everything(self):
        redis_client.get_redis().set("junk", "1")
        self.client.post("/flush", follow_redirects=True)
        self.assertEqual(redis_client.get_redis().dbsize(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

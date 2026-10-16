"""Login: hash functions, Bearer keys, admin phrase, admin endpoints (api/login.py)."""
import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from api.login import hash_phrase, hash_token, new_token, verify_admin_phrase, verify_phrase
from api.models import ApiToken

# The tests use their own phrase, not the real one from .env
TEST_PHRASE = "test-phrase-42"
test_phrase = override_settings(ADMIN_SECRET_PHRASE=TEST_PHRASE, ADMIN_PHRASE_HASH="")


@test_phrase
class HashingTests(TestCase):
    def test_token_hash(self):
        t = new_token("user")
        self.assertTrue(t.startswith("algo_u_"))
        self.assertTrue(new_token("admin").startswith("algo_a_"))
        self.assertEqual(len(hash_token(t)), 64)
        self.assertEqual(hash_token(t), hash_token(t))  # deterministic → can be looked up
        self.assertNotEqual(hash_token(t), hash_token(t + "x"))
        self.assertNotIn(t, hash_token(t))

    def test_phrase_hash(self):
        h = hash_phrase("secret")
        self.assertTrue(h.startswith("pbkdf2_sha256$"))
        self.assertNotEqual(h, hash_phrase("secret"))  # random salt each time
        self.assertTrue(verify_phrase("secret", h))
        self.assertFalse(verify_phrase("Secret", h))
        self.assertFalse(verify_phrase("secret", "garbage"))

    def test_admin_phrase_comes_from_settings(self):
        self.assertTrue(verify_admin_phrase(TEST_PHRASE))
        self.assertTrue(verify_admin_phrase(f"  {TEST_PHRASE} "))
        self.assertFalse(verify_admin_phrase(TEST_PHRASE + "x"))

    def test_admin_phrase_hash_wins(self):
        with self.settings(ADMIN_PHRASE_HASH=hash_phrase("only-the-hash")):
            self.assertTrue(verify_admin_phrase("only-the-hash"))
            self.assertFalse(verify_admin_phrase(TEST_PHRASE))

    def test_no_phrase_set_means_no_admin_login(self):
        with self.settings(ADMIN_SECRET_PHRASE="", ADMIN_PHRASE_HASH=""):
            self.assertFalse(verify_admin_phrase(""))
            self.assertFalse(verify_admin_phrase(TEST_PHRASE))


@test_phrase
class Api(TestCase):
    def setUp(self):
        cache.clear()

    def call(self, method, url, body=None, token=None):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        fn = getattr(self.client, method)
        if method in ("post", "delete"):
            return fn(url, data=json.dumps(body or {}), content_type="application/json", **headers)
        return fn(url, **headers)

    def register(self, username="alice", password="s3cret-pass"):
        r = self.call("post", "/api/auth/register/", {"username": username, "name": username.title(), "password": password})
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def make_admin(self, username="boss", password="b0ss-pass!"):
        User.objects.create_user(username, password=password, is_staff=True, first_name="Boss")
        return username, password

    def admin_key(self, username="boss", password="b0ss-pass!"):
        ch = self.call("post", "/api/auth/admin/login/", {"username": username, "password": password}).json()
        r = self.call("post", "/api/auth/admin/verify/", {"challenge_id": ch["challenge_id"], "answer": TEST_PHRASE})
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()["token"]


class UserTokenTests(Api):
    def test_register_returns_bearer_key(self):
        s = self.register()
        self.assertEqual(s["token_type"], "Bearer")
        self.assertEqual(s["role"], "user")
        self.assertTrue(s["token"].startswith("algo_u_"))
        self.assertEqual(s["expires_in"], 12 * 3600)
        # only the hash is stored
        row = ApiToken.objects.get()
        self.assertEqual(row.key_hash, hash_token(s["token"]))
        self.assertNotIn(s["token"], row.key_hash)
        me = self.call("get", "/api/auth/me/", token=s["token"]).json()
        self.assertEqual(me["user"]["username"], "alice")
        self.assertEqual(me["role"], "user")

    def test_bad_keys(self):
        r = self.call("get", "/api/history/", token="algo_u_nope")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["code"], "token_invalid")
        self.assertEqual(r["WWW-Authenticate"], 'Bearer realm="api"')
        r = self.client.get("/api/history/", HTTP_AUTHORIZATION="Basic abc")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.call("get", "/api/history/").status_code, 401)  # no key

    def test_every_login_gets_a_new_key(self):
        a = self.register()["token"]
        b = self.call("post", "/api/auth/login/", {"username": "alice", "password": "s3cret-pass"}).json()["token"]
        self.assertNotEqual(a, b)
        for t in (a, b):
            self.assertEqual(self.call("get", "/api/history/", token=t).status_code, 200)

    def test_refresh_rotates(self):
        old = self.register()["token"]
        new = self.call("post", "/api/auth/token/refresh/", token=old).json()["token"]
        self.assertNotEqual(old, new)
        self.assertEqual(self.call("get", "/api/history/", token=old).status_code, 401)
        self.assertEqual(self.call("get", "/api/history/", token=new).status_code, 200)

    def test_expired_key(self):
        t = self.register()["token"]
        ApiToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        r = self.call("get", "/api/history/", token=t)
        self.assertEqual(r.status_code, 401)
        self.assertIn("expired", r.json()["error"])

    def test_logout_revokes(self):
        t = self.register()["token"]
        self.call("post", "/api/auth/logout/", token=t)
        self.assertEqual(self.call("get", "/api/history/", token=t).status_code, 401)

    def test_list_and_revoke_own_keys(self):
        t1 = self.register()["token"]
        t2 = self.call("post", "/api/auth/login/", {"username": "alice", "password": "s3cret-pass"}).json()["token"]
        keys = self.call("get", "/api/auth/tokens/", token=t1).json()["tokens"]
        self.assertEqual(len(keys), 2)
        self.assertEqual(sum(k["current"] for k in keys), 1)
        self.assertNotIn("key_hash", keys[0])
        other = next(k for k in keys if not k["current"])
        self.assertEqual(self.call("delete", f"/api/auth/tokens/{other['id']}/", token=t1).status_code, 200)
        self.assertEqual(self.call("get", "/api/history/", token=t2).status_code, 401)
        # can't revoke someone else's key
        bob = self.register("bobby")["token"]
        mine = ApiToken.objects.filter(user__username="alice", revoked_at__isnull=True).first()
        self.assertEqual(self.call("delete", f"/api/auth/tokens/{mine.id}/", token=bob).status_code, 404)

    @override_settings(MAX_ACTIVE_TOKENS_PER_USER=3)
    def test_active_key_limit(self):
        self.register()
        for _ in range(5):
            self.call("post", "/api/auth/login/", {"username": "alice", "password": "s3cret-pass"})
        active = ApiToken.objects.filter(revoked_at__isnull=True).count()
        self.assertEqual(active, 3)

    def test_login_lockout(self):
        self.register()
        for _ in range(10):
            self.assertEqual(self.call("post", "/api/auth/login/", {"username": "alice", "password": "x"}).status_code, 401)
        r = self.call("post", "/api/auth/login/", {"username": "alice", "password": "s3cret-pass"})
        self.assertEqual(r.status_code, 429)

    def test_user_key_is_not_admin(self):
        t = self.register()["token"]
        self.assertEqual(self.call("get", "/api/admin/users/", token=t).status_code, 403)


class AdminLoginTests(Api):
    def test_two_step_admin_login(self):
        self.make_admin()
        r = self.call("post", "/api/auth/admin/login/", {"username": "boss", "password": "b0ss-pass!"})
        self.assertEqual(r.status_code, 200)
        ch = r.json()
        self.assertIn("admin phrase", ch["question"])
        self.assertEqual(ch["attempts_left"], 3)
        ok = self.call("post", "/api/auth/admin/verify/", {"challenge_id": ch["challenge_id"], "answer": TEST_PHRASE}).json()
        self.assertEqual(ok["role"], "admin")
        self.assertTrue(ok["token"].startswith("algo_a_"))
        self.assertEqual(ok["expires_in"], 30 * 60)
        self.assertTrue(ok["user"]["is_admin"])
        # the challenge is single-use
        again = self.call("post", "/api/auth/admin/verify/", {"challenge_id": ch["challenge_id"], "answer": TEST_PHRASE})
        self.assertEqual(again.status_code, 401)

    def test_wrong_phrase_attempts(self):
        self.make_admin()
        ch = self.call("post", "/api/auth/admin/login/", {"username": "boss", "password": "b0ss-pass!"}).json()
        r1 = self.call("post", "/api/auth/admin/verify/", {"challenge_id": ch["challenge_id"], "answer": "ib001"})
        self.assertEqual(r1.status_code, 401)
        self.assertIn("2 attempts left", r1.json()["error"])
        self.call("post", "/api/auth/admin/verify/", {"challenge_id": ch["challenge_id"], "answer": "x"})
        r3 = self.call("post", "/api/auth/admin/verify/", {"challenge_id": ch["challenge_id"], "answer": "y"})
        self.assertIn("No attempts left", r3.json()["error"])
        # even the right phrase no longer works on this challenge
        r4 = self.call("post", "/api/auth/admin/verify/", {"challenge_id": ch["challenge_id"], "answer": TEST_PHRASE})
        self.assertEqual(r4.status_code, 401)

    def test_expired_challenge(self):
        from api.models import AdminChallenge
        self.make_admin()
        ch = self.call("post", "/api/auth/admin/login/", {"username": "boss", "password": "b0ss-pass!"}).json()
        AdminChallenge.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        r = self.call("post", "/api/auth/admin/verify/", {"challenge_id": ch["challenge_id"], "answer": TEST_PHRASE})
        self.assertEqual(r.status_code, 401)

    def test_non_admin_cannot_start(self):
        self.register()
        r = self.call("post", "/api/auth/admin/login/", {"username": "alice", "password": "s3cret-pass"})
        self.assertEqual(r.status_code, 403)
        r = self.call("post", "/api/auth/admin/login/", {"username": "boss", "password": "nope"})
        self.assertEqual(r.status_code, 401)

    def test_staff_with_normal_login_gets_user_key_only(self):
        self.make_admin()
        t = self.call("post", "/api/auth/login/", {"username": "boss", "password": "b0ss-pass!"}).json()["token"]
        self.assertEqual(self.call("get", "/api/admin/users/", token=t).status_code, 403)

    def test_admin_endpoints(self):
        alice = self.register()["token"]
        self.make_admin()
        key = self.admin_key()
        users = self.call("get", "/api/admin/users/", token=key).json()["users"]
        self.assertEqual({u["username"] for u in users}, {"alice", "boss"})
        tokens = self.call("get", "/api/admin/tokens/", token=key).json()["tokens"]
        self.assertEqual(len(tokens), 2)
        alice_id = next(u["id"] for u in users if u["username"] == "alice")
        r = self.call("delete", f"/api/admin/users/{alice_id}/tokens/", token=key).json()
        self.assertEqual(r["revoked"], 1)
        self.assertEqual(self.call("get", "/api/history/", token=alice).status_code, 401)

    def test_admin_key_dies_if_staff_removed(self):
        self.make_admin()
        key = self.admin_key()
        User.objects.filter(username="boss").update(is_staff=False)
        self.assertEqual(self.call("get", "/api/admin/users/", token=key).status_code, 401)

    def test_refresh_keeps_admin_role(self):
        self.make_admin()
        key = self.admin_key()
        new = self.call("post", "/api/auth/token/refresh/", token=key).json()
        self.assertEqual(new["role"], "admin")
        self.assertEqual(self.call("get", "/api/admin/users/", token=new["token"]).status_code, 200)

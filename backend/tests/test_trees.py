"""Trees: the algorithms (algorithms/) and the tree / history API (api/api.py)."""
import json

from django.test import TestCase

from algorithms.algorithms import BSTAlgorithms as BinarySearchTree, build_tree


def values_of(d):
    """Nested dict -> (value, left, right) tuples, ignoring ids."""
    if d is None:
        return None
    return (d["value"], values_of(d["left"]), values_of(d["right"]))


class BuildTests(TestCase):
    def test_structure(self):
        tree, dups = build_tree([5, 3, 8, 1, 4, 9])
        self.assertEqual(
            values_of(tree.snapshot()),
            (5, (3, (1, None, None), (4, None, None)), (8, None, (9, None, None))),
        )
        self.assertEqual(dups, [])
        self.assertEqual(tree.summary()["traversals"]["inorder"], [1, 3, 4, 5, 8, 9])
        self.assertEqual(tree.height(), 3)

    def test_duplicates(self):
        tree, dups = build_tree([2, 2, 1, 1])
        self.assertEqual(tree.size, 2)
        self.assertEqual(dups, [2, 1])

    def test_round_trip(self):
        tree, _ = build_tree([50, 30, 70, 20])
        again = BinarySearchTree.from_dict(tree.snapshot())
        self.assertEqual(again.snapshot(), tree.snapshot())
        self.assertEqual(again.size, 4)


class SearchTests(TestCase):
    def setUp(self):
        self.tree, _ = build_tree([50, 30, 70, 20, 40, 60, 80])

    def test_found(self):
        found, steps = self.tree.search_steps(40)
        self.assertTrue(found)
        self.assertEqual(steps[-1]["status"], "found")
        # start, 50 -> left, 30 -> right, 40 equal
        self.assertEqual(len(steps), 4)

    def test_not_found(self):
        found, steps = self.tree.search_steps(45)
        self.assertFalse(found)
        self.assertEqual(steps[-1]["status"], "not_found")
        self.assertEqual(steps[-1]["highlight"]["missing"]["side"], "right")


class DeleteTests(TestCase):
    def build(self):
        return build_tree([50, 30, 70, 20, 40, 60, 80, 65])[0]

    def test_leaf(self):
        t = self.build()
        ok, steps = t.delete_steps(20)
        self.assertTrue(ok)
        self.assertEqual(t.summary()["traversals"]["inorder"], [30, 40, 50, 60, 65, 70, 80])
        self.assertEqual(steps[-1]["status"], "done")

    def test_one_child(self):
        t = self.build()
        t.delete_steps(60)
        self.assertEqual(values_of(t.snapshot())[2][1], (65, None, None))

    def test_two_children_root(self):
        t = self.build()
        ok, _ = t.delete_steps(50)
        self.assertTrue(ok)
        self.assertEqual(t.root.value, 60)
        self.assertEqual(t.summary()["traversals"]["inorder"], [20, 30, 40, 60, 65, 70, 80])
        self.assertEqual(t.size, 7)

    def test_not_found(self):
        t = self.build()
        ok, steps = t.delete_steps(99)
        self.assertFalse(ok)
        self.assertEqual(t.size, 8)
        self.assertEqual(steps[-1]["status"], "not_found")

    def test_last_node(self):
        t = build_tree([1])[0]
        t.delete_steps(1)
        self.assertIsNone(t.root)


class ApiTestCase(TestCase):
    """Test client that sends the Bearer key it got from register / login."""

    token = None

    def _headers(self):
        return {"HTTP_AUTHORIZATION": f"Bearer {self.token}"} if self.token else {}

    def post(self, url, body):
        r = self.client.post(url, data=json.dumps(body), content_type="application/json", **self._headers())
        if url in ("/api/auth/register/", "/api/auth/login/") and r.status_code == 200:
            self.token = r.json()["token"]
        if url == "/api/auth/logout/":
            self.token = None
        return r

    def get(self, url):
        return self.client.get(url, **self._headers())

    def delete(self, url):
        return self.client.delete(url, **self._headers())


class APITests(TestCase):
    def post(self, url, body):
        return self.client.post(url, data=json.dumps(body), content_type="application/json")

    def test_create(self):
        r = self.post("/api/tree/", {"values": [10, 5, 15, 7.5]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["root"]["left"]["right"]["value"], 7.5)

    def test_bad_input(self):
        self.assertEqual(self.post("/api/tree/", {"values": []}).status_code, 400)
        self.assertEqual(self.post("/api/tree/", {"values": ["a"]}).status_code, 400)
        self.assertEqual(self.post("/api/tree/", {"values": [True]}).status_code, 400)
        self.assertEqual(self.client.get("/api/tree/").status_code, 405)

    def test_search_and_delete(self):
        root = self.post("/api/tree/", {"values": [50, 30, 70]}).json()["root"]
        r = self.post("/api/tree/search/", {"tree": root, "target": 70}).json()
        self.assertTrue(r["found"])
        r = self.post("/api/tree/delete/", {"tree": root, "target": 50}).json()
        self.assertTrue(r["found"])
        self.assertEqual(r["root"]["value"], 70)
        self.assertEqual(r["size"], 2)

    def test_invalid_tree(self):
        bad = {"id": 0, "value": 5, "left": {"id": 1, "value": 9, "left": None, "right": None}, "right": None}
        self.assertEqual(self.post("/api/tree/search/", {"tree": bad, "target": 5}).status_code, 400)


class HistoryTests(ApiTestCase):
    def register(self, name="alice"):
        return self.post("/api/auth/register/", {"username": name, "name": f"{name.title()} Smith", "password": "s3cret-pass"})

    def test_anonymous_has_no_history(self):
        r = self.post("/api/tree/", {"values": [1, 2]}).json()
        self.assertIsNone(r["tree_id"])
        self.assertEqual(self.get("/api/history/").status_code, 401)

    def test_operations_are_recorded(self):
        self.assertEqual(self.register().status_code, 200)
        created = self.post("/api/tree/", {"values": [50, 30, 70]}).json()
        tid = created["tree_id"]
        self.assertIsNotNone(tid)

        self.post("/api/tree/search/", {"tree": created["root"], "target": 99, "tree_id": tid})
        r = self.post("/api/tree/delete/", {"tree": created["root"], "target": 50, "tree_id": tid}).json()
        self.assertEqual(r["size"], 2)

        trees = self.get("/api/history/").json()["trees"]
        self.assertEqual(len(trees), 1)
        ops = trees[0]["operations"]
        self.assertEqual([o["kind"] for o in ops], ["create", "search", "delete"])
        self.assertEqual([o["found"] for o in ops], [None, False, True])
        self.assertEqual(trees[0]["size"], 2)
        self.assertEqual(trees[0]["root"]["value"], 70)

        op = self.get(f"/api/history/{tid}/operations/{ops[2]['id']}/").json()["operation"]
        self.assertEqual(op["steps"][-1]["status"], "done")

    def test_users_are_isolated(self):
        self.register("alice")
        tid = self.post("/api/tree/", {"values": [1]}).json()["tree_id"]
        self.post("/api/auth/logout/", {})
        self.register("bob")
        self.assertEqual(self.get(f"/api/history/{tid}/").status_code, 404)
        self.assertEqual(self.get("/api/history/").json()["trees"], [])

    def test_login_and_errors(self):
        self.register("alice")
        self.post("/api/auth/logout/", {})
        self.assertEqual(self.get("/api/auth/me/").json()["user"], None)
        self.assertEqual(self.register("Alice").status_code, 400)  # taken (case-insensitive)
        self.assertEqual(self.post("/api/auth/login/", {"username": "alice", "password": "nope"}).status_code, 401)
        r = self.post("/api/auth/login/", {"username": "alice", "password": "s3cret-pass"})
        self.assertEqual(r.json()["user"]["username"], "alice")
        self.assertEqual(self.post("/api/auth/register/", {"username": "x", "password": "123"}).status_code, 400)
        no_name = self.post("/api/auth/register/", {"username": "carol", "password": "s3cret-pass"})
        self.assertEqual(no_name.status_code, 400)

    def test_user_json_and_password_hashing(self):
        from django.contrib.auth.models import User
        me = self.register("dave").json()["user"]
        self.assertEqual(me["name"], "Dave Smith")
        self.assertIsInstance(me["id"], int)
        self.assertNotIn("password", me)
        stored = User.objects.get(pk=me["id"]).password
        self.assertNotEqual(stored, "s3cret-pass")  # only the hash is in the database
        self.assertTrue(stored.startswith("pbkdf2_sha256$"))
        self.post("/api/tree/", {"values": [3, 1, 2]})
        data = self.get("/api/history/").json()
        self.assertEqual(data["user"]["id"], me["id"])
        self.assertEqual(data["trees"][0]["user_id"], me["id"])
        self.assertEqual(data["trees"][0]["initial_values"], [3, 1, 2])

    def test_save_false(self):
        self.register()
        r = self.post("/api/tree/", {"values": [1, 2], "save": False}).json()
        self.assertIsNone(r["tree_id"])
        self.assertEqual(self.get("/api/history/").json()["trees"], [])

    def test_delete_from_history(self):
        self.register()
        tid = self.post("/api/tree/", {"values": [1]}).json()["tree_id"]
        self.assertEqual(self.delete(f"/api/history/{tid}/").status_code, 200)
        self.assertEqual(self.get("/api/history/").json()["trees"], [])

    def test_api_ignores_session_cookies(self):
        """Only the Bearer key counts on the API — a Django session cookie does not log you in."""
        from django.contrib.auth.models import User
        User.objects.create_user("eve", password="s3cret-pass")
        self.client.login(username="eve", password="s3cret-pass")  # session cookie
        self.assertEqual(self.client.get("/api/history/").status_code, 401)
        self.assertIsNone(self.client.get("/api/auth/me/").json()["user"])

    def test_save_existing_tree_as_is(self):
        self.register()
        rb = self.post("/api/tree/", {"values": [1, 2, 3, 4, 5, 6], "kind": "rb", "save": False}).json()
        saved = self.post("/api/tree/", {"tree": rb["root"], "kind": "rb"}).json()
        self.assertIsNotNone(saved["tree_id"])
        self.assertEqual(saved["root"], rb["root"])  # same shape and colors


class RedBlackTests(ApiTestCase):
    def test_build_rb_and_ops(self):
        from algorithms.algorithms import RedBlackAlgorithms as RedBlackTree
        r = self.post("/api/tree/", {"values": list(range(1, 16)), "kind": "rb"}).json()
        self.assertEqual(r["kind"], "rb")
        self.assertEqual(r["root"]["color"], "black")
        tree = r["root"]
        # sorted input would make a plain BST a 15-long chain; the RB tree stays short
        self.assertLessEqual(r["height"], 6)

        bd = self.post("/api/tree/op/", {"op": "black_depth", "kind": "rb", "tree": tree}).json()
        self.assertTrue(bd["found"])
        self.assertTrue(bd["outcome"].startswith("BLACK HEIGHT"))
        self.assertIn("def black_depth", bd["code"])

        for v in [8, 1, 15, 4, 12]:
            d = self.post("/api/tree/op/", {"op": "delete", "kind": "rb", "tree": tree, "target": v}).json()
            self.assertTrue(d["found"], v)
            tree = d["root"]
            self.assertIsNone(RedBlackTree.from_dict(tree).violation())
        ins = self.post("/api/tree/op/", {"op": "insert", "kind": "rb", "tree": tree, "target": 100}).json()
        self.assertEqual(ins["outcome"], "INSERTED 100")

    def test_invalid_rb_rejected(self):
        bad = {"id": 0, "value": 5, "color": "red", "left": None, "right": None}
        r = self.post("/api/tree/op/", {"op": "search", "kind": "rb", "tree": bad, "target": 5})
        self.assertEqual(r.status_code, 400)

    def test_op_not_available(self):
        root = self.post("/api/tree/", {"values": [2, 1, 3]}).json()["root"]
        r = self.post("/api/tree/op/", {"op": "black_depth", "kind": "bst", "tree": root})
        self.assertEqual(r.status_code, 400)

    def test_paint(self):
        ok = self.post("/api/tree/", {"values": [50, 30, 70, 20, 40]}).json()["root"]
        r = self.post("/api/tree/op/", {"op": "paint", "kind": "bst", "tree": ok}).json()
        self.assertTrue(r["found"])
        self.assertEqual(r["kind"], "rb")
        self.assertEqual(r["root"]["color"], "black")
        chain = self.post("/api/tree/", {"values": [1, 2, 3, 4]}).json()["root"]
        r = self.post("/api/tree/op/", {"op": "paint", "kind": "bst", "tree": chain}).json()
        self.assertFalse(r["found"])
        self.assertEqual(r["outcome"], "CANNOT BE PAINTED")

    def test_saved_paint_changes_kind(self):
        self.post("/api/auth/register/", {"username": "pat", "name": "Pat", "password": "s3cret-pass"})
        c = self.post("/api/tree/", {"values": [2, 1, 3]}).json()
        r = self.post("/api/tree/op/", {"op": "paint", "tree_id": c["tree_id"], "tree": c["root"]}).json()
        self.assertTrue(r["found"])
        tree = self.get("/api/history/").json()["trees"][0]
        self.assertEqual(tree["kind"], "rb")
        self.assertEqual([o["kind"] for o in tree["operations"]], ["create", "paint"])
        # next op runs on the saved red-black tree
        r = self.post("/api/tree/op/", {"op": "black_depth", "tree_id": c["tree_id"]}).json()
        self.assertTrue(r["found"])

    def test_code_tags_exist_in_snippets(self):
        """Every step's code tag must point to at least one line of the shown code."""
        import random
        import re
        from algorithms.code import tree_code as code_for
        from algorithms.algorithms import RedBlackAlgorithms as RedBlackTree, paint_steps
        from algorithms.algorithms import BSTAlgorithms as BinarySearchTree

        def tags(code):
            out = set()
            for m in re.finditer(r"#@([\w,]+)", code):
                out |= set(m.group(1).split(","))
            return out

        random.seed(5)
        for _ in range(60):
            vals = random.sample(range(60), random.randint(1, 20))
            for kind, cls in (("bst", BinarySearchTree), ("rb", RedBlackTree)):
                t, _ = cls.build(vals)
                for op in ("search", "insert", "delete"):
                    v = random.randint(0, 59)
                    _, steps = getattr(t, f"{op}_steps")(v)
                    missing = {s["code"] for s in steps} - tags(code_for(kind, op))
                    self.assertFalse(missing, (kind, op, missing))
                if kind == "rb":
                    _, steps, _ = t.black_depth_steps()
                    self.assertFalse({s["code"] for s in steps} - tags(code_for("rb", "black_depth")))
            b, _ = BinarySearchTree.build(vals)
            _, steps, _ = paint_steps(b)
            self.assertFalse({s["code"] for s in steps} - tags(code_for("bst", "paint")))


class RedBlackFuzzTests(TestCase):
    """Random inserts / deletes must always keep every red-black rule."""

    def test_random_operations(self):
        import random
        from algorithms.algorithms import RedBlackAlgorithms
        from algorithms.build import RedBlackTree as PlainRedBlackTree

        rng = random.Random(42)
        for _ in range(40):
            vals = rng.sample(range(120), rng.randint(1, 40))
            plain, _ = PlainRedBlackTree.build(vals)  # build.py (no steps)
            self.assertIsNone(plain.violation())
            t, _ = RedBlackAlgorithms.build(vals)
            ref = set(vals)
            for _ in range(40):
                v = rng.randint(0, 119)
                if rng.random() < 0.5:
                    ok, _ = t.insert_steps(v)
                    self.assertEqual(ok, v not in ref)
                    ref.add(v)
                else:
                    ok, _ = t.delete_steps(v)
                    self.assertEqual(ok, v in ref)
                    ref.discard(v)
                self.assertIsNone(t.violation())
                self.assertEqual(t._traverse("in"), sorted(ref))

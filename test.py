import unittest

def extend(*args):
    target = {}
    for source in args:
        if source is None:
            continue
        if isinstance(source, dict):
            target.update(source)
    return target

def mutable_extend(target, *args):
    for source in args:
        if source is None:
            continue
        if isinstance(source, dict):
            target.update(source)
    return target

class TestExtend(unittest.TestCase):
    def test_merge(self):
        a = {"a": "foo"}
        b = {"b": "bar"}
        self.assertEqual(extend(a, b), {"a": "foo", "b": "bar"})

    def test_replace(self):
        a = {"a": "foo"}
        b = {"a": "bar"}
        self.assertEqual(extend(a, b), {"a": "bar"})

    def test_undefined(self):
        a = {"a": None}
        b = {"b": "foo"}
        self.assertEqual(extend(a, b), {"a": None, "b": "foo"})
        self.assertEqual(extend(b, a), {"a": None, "b": "foo"})

    def test_handle_0(self):
        a = {"a": "default"}
        b = {"a": 0}
        self.assertEqual(extend(a, b), {"a": 0})
        self.assertEqual(extend(b, a), {"a": "default"})

    def test_is_immutable(self):
        record = {}
        extend(record, {"foo": "bar"})
        self.assertIsNone(record.get("foo"))

    def test_null_as_argument(self):
        a = {"foo": "bar"}
        b = None
        c = None
        self.assertEqual(extend(b, a, c), {"foo": "bar"})

    def test_mutable(self):
        a = {"foo": "bar"}
        mutable_extend(a, {"bar": "baz"})
        self.assertEqual(a["bar"], "baz")

if __name__ == '__main__':
    unittest.main()

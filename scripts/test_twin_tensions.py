import unittest

from build_twin_profile import _collect_tensions


class TestTwinTensions(unittest.TestCase):
    def test_no_html_comments_in_tensions(self):
        for line in _collect_tensions():
            self.assertNotIn("<!--", line)
            self.assertNotIn("-->", line)


if __name__ == "__main__":
    unittest.main()

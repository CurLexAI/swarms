# SPDX-License-Identifier: MIT
# Licensed under MIT
# mypy: ignore-errors
"""
اختبارات المراجعة السيادية
"""

import sys
import os
import unittest
from pathlib import Path

# إضافة مسار المشروع
sys.path.insert(0, str(Path(__file__).parent.parent / ".agents"))

try:
    from pr_review import SovereignReviewer
except ImportError:
    # Fallback للاستيراد المباشر
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pr_review",
        Path(__file__).parent.parent / ".agents" / "pr_review.py"
    )
    pr_review = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pr_review)
    SovereignReviewer = pr_review.SovereignReviewer


class TestSovereignReviewer(unittest.TestCase):

    def setUp(self):
        """إعداد الاختبارات"""
        self.reviewer = SovereignReviewer(pr_number=42)

    def test_clean_code_approved(self):
        """كود نظيف = APPROVE"""
        clean_code = """
def hello():
    print("Hello World")
    return True
"""
        reviewer = SovereignReviewer(42, clean_code)
        report = reviewer.review()
        self.assertEqual(report["verdict"], "APPROVE")
        self.assertEqual(report["findings_count"], 0)

    def test_api_key_detected(self):
        """اكتشاف API key"""
        code_with_key = "api" + "_key = " + '"sk-' + '1234567890abcdefghij"'
        reviewer = SovereignReviewer(42, code_with_key)
        report = reviewer.review()
        self.assertEqual(report["verdict"], "REQUEST_CHANGES")
        self.assertGreater(report["critical_issues"], 0)

    def test_modal_url_detected(self):
        """اكتشاف Modal URL"""
        code_with_modal = 'url = "https://my-app--function' + '.modal' + '.run"'
        reviewer = SovereignReviewer(42, code_with_modal)
        report = reviewer.review()
        self.assertEqual(report["verdict"], "REQUEST_CHANGES")
        self.assertGreater(report["high_issues"], 0)

    def test_github_format(self):
        """تنسيق GitHub يعمل"""
        reviewer = SovereignReviewer(42, "print('ok')")
        report = reviewer.review()
        comment = reviewer.format_github_comment(report)
        self.assertIn("🛡️ Sovereign PR Review", comment)
        self.assertIn("APPROVE", comment)

    def test_github_token_protection(self):
        """التوكين لا يظهر في المخرجات"""
        fake_token = "ghp_" + "secrettoken1234567890123456789012345"
        os.environ["GITHUB_TOKEN"] = fake_token

        code = "print('hello')"
        reviewer = SovereignReviewer(42, code)
        report = reviewer.review()
        json_output = str(report)

        # التحقق من عدم تسريب التوكين
        self.assertNotIn(fake_token, json_output)


def run_tests():
    """تشغيل الاختبارات"""
    print("=" * 70)
    print("🧪 Sovereign PR Review - Unit Tests")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSovereignReviewer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())

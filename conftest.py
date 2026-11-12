import os
import sys


TESTS_DIR = os.path.join(os.path.dirname(__file__), "tests")
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testapp.settings")

import django

django.setup()


def pytest_collection_modifyitems(config, items):
    # ``rules.rulesets`` exposes a ``test_rule`` helper that pytest otherwise
    # mistakes for a test once it gets imported by the test modules.
    from rules.rulesets import test_rule as library_test_rule

    items[:] = [
        item
        for item in items
        if not (
            item.name == "test_rule"
            and getattr(item, "function", None) is library_test_rule
        )
    ]

"""One public-address guard for every collector that fetches URLs it did not choose (press text, sign-on letters)."""
import ast
import sys
from pathlib import Path

import pytest

FEC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FEC))
from collect import public_fetch_guard as G         # noqa: E402
from collect import collect_signon_letters as C     # noqa: E402


def test_the_letter_collector_uses_the_shared_guard_objects():
    assert C.require_public is G.require_public and C.PublicOnlyRedirects is G.PublicOnlyRedirects


@pytest.mark.parametrize("script", ["fetch_press_text.py", "collect_signon_letters.py"])
def test_neither_collector_carries_its_own_copy_of_the_guard(script):
    tree = ast.parse((FEC / "collect" / script).read_text(encoding="utf-8"))
    defined = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    assert not defined & {"_embedded_ipv4", "_is_public", "_require_public", "_PublicOnlyRedirects", "is_public", "require_public", "PublicOnlyRedirects"}


def test_the_press_fetcher_imports_the_shared_guard():
    assert "public_fetch_guard" in (FEC / "collect" / "fetch_press_text.py").read_text(encoding="utf-8")


@pytest.mark.parametrize("url", ["http://127.0.0.1/x", "http://169.254.169.254/", "file:///etc/passwd", "http://[::1]/", "http://10.0.0.5/"])
def test_the_guard_refuses_non_public_targets(url):
    with pytest.raises(ValueError):
        G.require_public(url)

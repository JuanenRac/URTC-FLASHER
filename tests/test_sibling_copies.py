# =============================================================================
# URTC Flasher - tests/test_sibling_copies.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The modules of the desktop interface that URTC-TESTER and this tool keep as copies of each other must not drift apart.

They are compared by what they do: comments, docstrings and layout are ignored, the syntax tree is not. The check
skips when the other repository is not next to this one. Until the copies become one package, a fix made to one of
them and not to the other fails here."""
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
OTHER = ROOT.parent / "URTC-TESTER"
SHARED = ("hydra_umc_animation.py", "hydra_umc_deck_widgets.py")


def behaviour(path: Path) -> str:
    """The module without comments, docstrings and formatting."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


@pytest.mark.parametrize("name", SHARED)
def test_the_copy_does_not_differ_from_the_one_of_the_other_tool(name):
    if not (OTHER / name).is_file():
        pytest.skip("URTC-TESTER is not next to this repository")
    assert behaviour(ROOT / name) == behaviour(OTHER / name), f"{name} differs from the copy in URTC-TESTER: make the same change in both"


def test_the_comparison_sees_a_real_difference_and_ignores_a_comment(tmp_path):
    base = tmp_path / "a.py"
    base.write_text('"""doc"""\n\ndef f(x):\n    """one"""\n    return x + 1  # note\n', encoding="utf-8")
    same = tmp_path / "b.py"
    same.write_text('"""other doc"""\n\n\ndef f(x):\n    # a comment\n    return x+1\n', encoding="utf-8")
    different = tmp_path / "c.py"
    different.write_text('"""doc"""\n\ndef f(x):\n    return x + 2\n', encoding="utf-8")
    assert behaviour(base) == behaviour(same)
    assert behaviour(base) != behaviour(different)

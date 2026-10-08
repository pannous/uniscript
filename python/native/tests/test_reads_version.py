"""reads_version is part of the package API (AGENTS.md: every implementation has it)"""

import uniscript


def test_reads_any_uniscript_org_version():
    assert "reads_version" in uniscript.__all__
    assert uniscript.reads_version("https://uniscript.org/v1")
    assert uniscript.reads_version("https://uniscript.org/v7")
    assert uniscript.reads_version("")


def test_foreign_version_is_not_read():
    assert not uniscript.reads_version("https://example.org/v1")

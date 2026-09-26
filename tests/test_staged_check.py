"""scripts/check.py's staged-check rule (DECISIONS §59): which check a change needs.

Documentation no code reads and the reports the checks write need no check; any other change is
code (a document a string constant of the Python code names, or DOCS_READ_UNNAMED covers,
included) and needs one --full on its final state before it is merged; what cannot be decided
needs the --full. The decision is made against origin/master (fetched first; master only when
there is no origin/master), counts committed, staged, unstaged, untracked and git-hidden changes,
and accepts the last --full log only for exactly this code.

The fixtures are real git repositories in a temporary directory, isolated from the user's git
configuration. The document names used here are made up, and real ones are assembled from pieces:
the rule reads every string constant of this repository's Python code, this file included, so a
real document named here would become "code".
"""
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("check_script_staged", ROOT / "scripts" / "check.py")
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)

MD = check.DOC_SUFFIX     # globs, name endings and real names are assembled from it: written out, they would name documents


@pytest.fixture
def git_env(monkeypatch, tmp_path):
    """The temporary repositories see no global or system git configuration (a merge.ff=only or a
    failing hook there broke these tests in review) and no repository above tmp_path."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR"):
        monkeypatch.delenv(var, raising=False)


def git(repo: Path, *a: str) -> str:
    p = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "-c", "init.defaultBranch=master", "-c", "commit.gpgsign=false", *a],
                       cwd=repo, check=True, capture_output=True, text=True)
    return p.stdout.strip()


def write(repo: Path, rel: str, text: str = "x\n") -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


READER = 'from pathlib import Path\nGUIDE = Path(__file__).parent.parent / "docs" / "rehber.md"\n'


@pytest.fixture
def repo(tmp_path, git_env):
    """master: code, a document a test reads (docs/rehber.md), one nothing reads (notlar.md),
    reports; then the branch `dal` checked out. No remote: the local master is the base."""
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q")
    write(r, "code.py", "x = 1\n")
    write(r, "docs/rehber.md")
    write(r, "notlar.md")
    write(r, "tests/test_reader.py", READER)
    write(r, "reports/eval_report.md")
    write(r, "reports/check_full.log", "old\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "base")
    git(r, "checkout", "-q", "-b", "dal")
    return r


def commit(repo: Path, msg: str = "c") -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


def full_log(repo: Path, sha: str, *, dirty: int = 0, gates=("a", "b"), failed=(), total_line=True,
             end_sha: str | None = None, end_dirty: int = 0, end_line=True, totals=None) -> None:
    run = " · 2026-09-26 12:00:00 · dal @ {} · commit edilmemiş değişiklik: {} dosya"
    lines = ["check.py --full" + run.format(sha[:7], dirty), "", "== kapılar =="]
    lines += [f"  [OK  ] {g}  1   (hedef: 1)" for g in gates]
    lines += [f"  [FAIL] {g}  0   (hedef: 1)" for g in failed]
    n = len(gates) + len(failed)
    if total_line:
        lines += ["", *(totals or [f"{len(gates)}/{n} kapı geçti"])]
    if end_line:
        lines += ["", "check.py --full sonu" + run.format((end_sha or sha)[:7], end_dirty)]
    write(repo, "reports/check_full.log", "\n".join(lines) + "\n")


def code_files(p: dict) -> set[str]:
    return {f for f, c in p["files"].items() if c == "kod"}


# --------------------------------------------------------------------------- pieces


def test_reports_and_documents():
    assert check.is_report("reports/eval_report.md") and check.is_report("reports/check_full.log")
    assert check.is_report("reports\\lean_report.md")                 # a Windows path
    assert not check.is_report("reports/sub/x.md")                     # only the reports the checks write
    assert not check.is_report("reports/f3_run.log") and not check.is_report("reports/lean_results.json")
    assert check.is_doc("docs/rehber.md") and check.is_doc("NOTLAR.MD") and check.is_doc("docs\\alt\\x.md")
    assert not check.is_doc("reports/eval_report.md") and not check.is_doc("code.py")
    # documentation lives at the root and under docs/; elsewhere a .md file is code by its place
    for elsewhere in ("reports/sub/x.md", "lean/notlar.md", "src/mathverify/paket.md", "scripts/dev/not.md",
                      "docsx/a.md", "tests/data/b.md"):
        assert not check.is_doc(elsewhere), elsewhere


def test_documents_read_without_a_name(monkeypatch):
    assert check.DOCS_READ_UNNAMED == {}                               # none today
    monkeypatch.setattr(check, "DOCS_READ_UNNAMED", {"docs/veri/": "copied", "docs/kabuk.md": "cat"})
    assert check.read_unnamed("docs/veri/a" + MD) == "copied" and check.read_unnamed("docs\\veri\\b" + MD)
    assert check.read_unnamed("docs/kabuk.md") == "cat" and check.read_unnamed("docs/veri" + MD) is None


@pytest.mark.parametrize("token, doc, expected", [
    ("rehber.md", "docs/rehber.md", True),            # the file name alone, as ROOT / "docs" / "x" leaves it
    ("docs/rehber.md", "docs/rehber.md", True),
    ("../docs/rehber.md", "docs/rehber.md", True),
    ("REHBER.MD", "docs/rehber.md", True),             # Windows opens it whatever the case
    ("docs\\rehber.md", "docs/rehber.md", True),
    ("notu.md", "docs/kurulum notu.md", True),         # the end of a name after a space, comma, quote, "="
    ("b.md", "docs/a,b.md", True),
    ("baska.md", "docs/rehber.md", False),
    ("hber.md", "docs/rehber.md", False),              # a letter before it: another name
    ("_rehber.md", "docs/x_rehber.md", False),
    ("rehber.md", "docs/rehber.md.bak", False),
    ("*" + MD, "a/b/c.md", True),                      # a glob over documents
    ("docs/*" + MD, "docs/rehber.md", True),
    ("docs/r?hber" + MD, "docs/rehber.md", True),
    (MD, "docs/rehber.md", False),                     # the bare extension is a type test
])
def test_names_doc(token, doc, expected):
    assert check.names_doc(token, doc) is expected


def test_names_doc_by_ending():
    """Only the ending of a name completed at run time is known: it names every document that
    ends with it, the bare extension every document."""
    assert check.names_doc("_report" + MD, "reports/f3_report.md", suffix=True)
    assert check.names_doc("hber" + MD, "docs/rehber.md", suffix=True)
    assert not check.names_doc("_report" + MD, "docs/rehber.md", suffix=True)
    assert check.names_doc(MD, "docs/rehber.md", suffix=True)


@pytest.mark.parametrize("text, tail, expected", [
    ("see docs/rehber" + MD + " first", False, [("docs/rehber" + MD, False)]),
    ("(rehber" + MD + ")", False, [("rehber" + MD, False)]),
    ("rehber" + MD, True, [("rehber" + MD, True)]),        # f"{x}rehber.md", x + "rehber.md"
    ("{}" + MD, False, [(MD, True)]),                     # "{}.md".format(name)
    ("{name}_x" + MD, False, [("_x" + MD, True)]),
    ("%s" + MD, False, [(MD, True)]),                     # "%s.md" % name: the s is the conversion
    ("%(n)s" + MD, False, [(MD, True)]),
    ("a" + MD + ", b" + MD, False, [("a" + MD, False), ("b" + MD, False)]),
    ("x.mdx and notes.markdown", False, []),
])
def test_doc_tokens(text, tail, expected):
    assert check.doc_tokens(text, tail) == expected


def test_only_code_strings_count_not_prose(tmp_path, git_env):
    write(tmp_path, "m.py", '"""Module docstring: see docs/a.md."""\n'
                            "# a comment: docs/b.md\n"
                            "def f():\n"
                            '    """Function docstring: c.md."""\n'
                            '    "a bare string statement: d.md"\n'
                            '    return open("docs/e.md")\n'
                            "g = lambda tag: f\"{tag}_f.md\"\n"
                            "h = lambda name: name + 'g.md'\n"
                            "i = lambda p: p.with_suffix('.md')\n"
                            "j = lambda p: p.endswith('.md')\n")
    docs = ["docs/a.md", "docs/b.md", "c.md", "d.md", "docs/e.md", "x_f.md", "yg.md", "z.md"]
    named = check.docs_named_by_code(tmp_path, docs)
    # i's with_suffix names every document (z.md included); j's endswith is a type test
    assert named == {"docs/e.md": "m.py:6", "x_f.md": "m.py:7", "yg.md": "m.py:8",
                     "docs/a.md": "m.py:9", "docs/b.md": "m.py:9", "c.md": "m.py:9", "d.md": "m.py:9",
                     "z.md": "m.py:9"}


def test_a_type_test_alone_names_nothing(tmp_path, git_env):
    write(tmp_path, "m.py", "j = lambda p: p.endswith('.md') or p.suffix == '.md'\n")
    assert check.docs_named_by_code(tmp_path, ["docs/a.md"]) == {}


def test_python_that_cannot_be_parsed_is_named(tmp_path, git_env):
    write(tmp_path, "ok.py", "x = 'a.md'\n")
    write(tmp_path, "sub/broken.py", "def (:\n")
    with pytest.raises(check.UnreadableSource, match=r"sub/broken\.py: SyntaxError"):
        check.docs_named_by_code(tmp_path, ["a.md"])
    assert check.docs_named_by_code(tmp_path, []) == {}               # nothing to decide: no scan


def test_python_is_read_as_python_reads_it(tmp_path, git_env):
    """A UTF-8 BOM (PowerShell's Out-File writes one) and a coding cookie are Python, not errors."""
    (tmp_path / "bom.py").write_bytes(b"\xef\xbb\xbfx = 'a" + MD.encode() + b"'\n")
    (tmp_path / "latin.py").write_bytes(b"# -*- coding: latin-1 -*-\ny = '\xe7" + MD.encode() + b"'\n")
    assert check.docs_named_by_code(tmp_path, ["a" + MD, "ç" + MD]) == {
        "a" + MD: "bom.py:1", "ç" + MD: "latin.py:2"}


def test_readers_without_a_name_are_counted(tmp_path, git_env, monkeypatch):
    monkeypatch.setattr(check, "DOCS_READ_UNNAMED", {"docs/kabuk.md": "a shell script cats it", "docs/veri/": "copied"})
    assert check.docs_named_by_code(tmp_path, ["docs/kabuk.md", "docs/diger.md", "docs/veri/a/b.md"]) == {
        "docs/kabuk.md": "adsız okuyucu: a shell script cats it", "docs/veri/a/b.md": "adsız okuyucu: copied"}


def test_without_git_the_walk_skips_environments_and_nested_repositories(tmp_path, git_env):
    write(tmp_path, ".venv/lib/pkg.py", "x = 'a.md'\n")
    write(tmp_path, "src/__pycache__/m.py", "x = 'a.md'\n")
    write(tmp_path, "nested/.git/HEAD", "ref: refs/heads/master\n")
    write(tmp_path, "nested/m.py", "x = 'a.md'\n")
    assert check.docs_named_by_code(tmp_path, ["a.md"]) == {}
    write(tmp_path, "evalset/build/gen.py", "x = 'a.md'\n")           # a directory named build is code
    assert check.docs_named_by_code(tmp_path, ["a.md"]) == {"a.md": "evalset/build/gen.py:1"}


def test_in_a_repository_git_lists_the_sources(repo):
    """Tracked and untracked files count; ignored scratch (even unparsable) and a nested worktree do
    not: a worktree under .claude/worktrees made the repository name its own documents twice."""
    write(repo, ".gitignore", "scratch/\n")
    write(repo, "scratch/eski.py", 'print "py2"\n')
    write(repo, "yeni_test.py", "x = 'notlar.md'\n")
    commit(repo)
    git(repo, "worktree", "add", "-q", ".claude/worktrees/onceki", "HEAD")
    write(repo, ".claude/worktrees/onceki/w.py", "x = 'baska.md'\n")
    named = check.docs_named_by_code(repo, ["notlar.md", "baska.md", "docs/rehber.md"])
    assert named == {"notlar.md": "yeni_test.py:1", "docs/rehber.md": "tests/test_reader.py:2"}


# --------------------------------------------------------------------------- the decision


def test_documentation_nothing_reads_needs_no_check(repo):
    write(repo, "notlar.md", "changed\n")
    commit(repo)
    write(repo, "yeni.md")                                             # untracked, also documentation
    p = check.plan(repo)
    assert p["level"] == "yok" and p["files"] == {"notlar.md": "belge", "yeni.md": "belge"}
    assert p["fetch"] == "origin yok"
    rc, lines = check.plan_report(repo)
    assert rc == 0 and lines[-1].startswith("  karar: YOK")


def test_reports_need_no_check(repo):
    write(repo, "reports/eval_report.md", "new\n")
    write(repo, "reports/check_full.log", "new\n")
    commit(repo)
    assert check.plan(repo)["level"] == "yok"


def test_a_document_a_test_reads_is_code(repo):
    write(repo, "docs/rehber.md", "changed\n")
    commit(repo)
    p = check.plan(repo)
    assert p["level"] == "tam" and p["files"] == {"docs/rehber.md": "kod"}
    assert p["named"] == {"docs/rehber.md": "tests/test_reader.py:2"}
    assert "okuyan: tests/test_reader.py:2" in "\n".join(check.render_plan(p))


def test_deleting_a_document_a_test_reads_is_code(repo):
    (repo / "docs" / "rehber.md").unlink()
    commit(repo)
    assert check.plan(repo)["files"] == {"docs/rehber.md": "kod"}


@pytest.mark.parametrize("change", ["committed", "staged", "unstaged", "untracked", "renamed", "deleted"])
def test_every_kind_of_code_change_is_seen(repo, change):
    if change == "untracked":
        write(repo, "yeni.py")
    elif change == "renamed":
        git(repo, "mv", "code.py", "kod.py")
        commit(repo)
    elif change == "deleted":
        (repo / "code.py").unlink()
    else:
        write(repo, "code.py", "x = 2\n")
        if change == "committed":
            commit(repo)
        elif change == "staged":
            git(repo, "add", "code.py")
    p = check.plan(repo)
    assert p["level"] == "tam", p
    assert code_files(p) == {"untracked": {"yeni.py"}, "renamed": {"code.py", "kod.py"}}.get(change, {"code.py"})


NON_PYTHON_CODE = ["evalset/items/x.json", "lean/PINS", "scripts/x.sh", "requirements.lock", "pyproject.toml",
                   ".env", ".gitignore", "reports/f3_run.log", "reports/lean_results.json", "tests/data/x.txt",
                   "lean/notlar" + MD, "src/mathverify/paket" + MD, "reports/alt/not" + MD, "scripts/dev/not" + MD]


@pytest.mark.parametrize("path", NON_PYTHON_CODE)
def test_whatever_is_not_documentation_is_code(repo, path):
    """Not only Python: data, pins, scripts, settings, other report files, and .md files outside
    the documentation places (lean/ is copied by tests and hashed by the cloud scripts, src/ is
    copied and packaged)."""
    write(repo, path)
    commit(repo)
    p = check.plan(repo)
    assert p["level"] == "tam" and p["files"] == {path: "kod"}, p


def test_no_change_needs_no_check(repo):
    p = check.plan(repo)
    assert p["level"] == "yok" and p["files"] == {}


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_changes_git_hides_decide_nothing(repo, flag):
    git(repo, "update-index", flag, "code.py")
    write(repo, "code.py", "x = 2\n")                                 # an edit no diff shows
    p = check.plan(repo)
    assert p["level"] == "tam" and p["hidden"] == ["code.py"] and "gizliyor" in p["why"]


def test_personal_excludes_hide_no_untracked_file(repo):
    """.git/info/exclude and status.showUntrackedFiles are the user's, not the project's: an
    untracked pytest.ini hidden by them still shapes a test run."""
    write(repo, ".git/info/exclude", "pytest.ini\n")
    git(repo, "config", "status.showUntrackedFiles", "no")
    write(repo, "pytest.ini", "[pytest]\naddopts = -k nothing\n")
    assert code_files(check.plan(repo)) == {"pytest.ini"}


# --------------------------------------------------------------------------- the last --full


def test_the_last_full_run_covers_the_same_code(repo):
    write(repo, "code.py", "x = 2\n")
    sha = commit(repo, "code")
    full_log(repo, sha)                                   # --full ran on this commit, clean, all gates OK
    write(repo, "reports/eval_report.md", "new\n")
    commit(repo, "reports")
    write(repo, "notlar.md", "after\n")                   # later documentation, even uncommitted
    p = check.plan(repo)
    assert p["level"] == "tamam", p
    assert p["full"]["ok"] and p["full"]["gates"] == "2/2" and p["full"]["code_since"] == []
    rc, lines = check.plan_report(repo)
    assert rc == 0 and lines[-1].startswith("  karar: TAMAM")


def test_code_changed_after_the_last_full_run(repo):
    full_log(repo, git(repo, "rev-parse", "HEAD"))
    write(repo, "code.py", "x = 3\n")
    commit(repo)
    p = check.plan(repo)
    assert p["level"] == "tam" and p["full"]["ok"] and p["full"]["code_since"] == ["code.py"]
    assert check.plan_report(repo)[0] == 1


def test_untracked_code_after_the_last_full_run(repo):
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo))
    write(repo, "src/yeni.py")                           # never committed, never measured
    p = check.plan(repo)
    assert p["level"] == "tam" and p["full"]["code_since"] == ["src/yeni.py"]


@pytest.mark.parametrize("path", ["docs/rehber.md", "lean/PINS", "evalset/items/x.json"])
def test_named_documents_and_data_changed_after_the_last_full_run(repo, path):
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo))
    write(repo, path, "changed\n")
    assert check.plan(repo)["full"]["code_since"] == [path]


@pytest.mark.parametrize("log, why", [
    (dict(dirty=1), "commit edilmemiş 1 değişiklikle başlamış"),
    (dict(total_line=False, end_line=False), "koşu bitmemiş"),
    (dict(failed=("c",)), "kapılar geçmedi (2/3)"),
    (dict(gates=()), "kapılar geçmedi (0/0)"),
    (dict(gates=("a",), totals=["2/2 kapı geçti"]), "kapılar geçmedi (2/2)"),       # marks disagree with the total
    (dict(totals=["1/2 kapı geçti", "2/2 kapı geçti"]), "kapılar geçmedi (2/2)"),   # two runs in one log
    (dict(end_line=False), "sonu kaydedilmemiş"),
    (dict(end_dirty=1), "ağaç koşu sırasında değişti"),
    (dict(end_sha="0" * 40), "ağaç koşu sırasında değişti"),
])
def test_a_full_run_that_proves_nothing_is_not_accepted(repo, log, why):
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo), **log)
    p = check.plan(repo)
    assert p["level"] == "tam" and not p["full"]["ok"] and why in p["full"]["why"], p["full"]


def test_a_full_run_log_that_is_not_one(repo):
    write(repo, "code.py", "x = 2\n")
    commit(repo)
    for text in ("", "check.py --full · ? · ? @ ? · x\n"):
        write(repo, "reports/check_full.log", text)
        assert "başlığı okunamadı" in check.plan(repo)["full"]["why"]
    (repo / "reports" / "check_full.log").unlink()
    assert check.plan(repo)["full"]["why"] == "günlük yok"
    full_log(repo, "0123456789abcdef0123456789abcdef01234567")   # a commit this repository lacks
    assert "bu depoda yok" in check.plan(repo)["full"]["why"]


def test_an_extra_ok_or_fail_line_breaks_the_count(repo):
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo))
    log = repo / "reports" / "check_full.log"
    log.write_text(log.read_text(encoding="utf-8").replace("== kapılar ==", "== kapılar ==\n  [FAIL] x"),
                   encoding="utf-8")
    assert not check.plan(repo)["full"]["ok"]


def test_the_full_run_writes_what_the_plan_accepts(repo, monkeypatch):
    """main --full's header and closing line, with the gates stubbed: reports are not counted (the
    run rewrites them, a quick check.py leaves eval_report.md modified), anything else is, and a
    file changed during the run shows in the closing line."""
    write(repo, "code.py", "x = 2\n")
    commit(repo)
    write(repo, "reports/eval_report.md", "left by a quick check.py\n")
    monkeypatch.setattr(check, "ROOT", repo)
    monkeypatch.setattr(check, "_main", lambda args: print("\n  [OK  ] a  1\n\n1/1 kapı geçti") or 0)
    assert check.main(["--full"]) == 0
    assert check.last_full_run(repo)["ok"]
    assert check.plan(repo)["level"] == "tamam"
    monkeypatch.setattr(check, "_main", lambda args: write(repo, "code.py", "x = 3\n") or print("1/1 kapı geçti") or 0)
    assert check.main(["--full"]) == 0
    lines = (repo / "reports" / "check_full.log").read_text(encoding="utf-8").splitlines()
    assert lines[0].endswith("commit edilmemiş değişiklik: 0 dosya")
    assert lines[-1].startswith("check.py --full sonu") and lines[-1].endswith("commit edilmemiş değişiklik: 1 dosya")


# --------------------------------------------------------------------------- the base


def test_code_the_base_received_after_the_branch_left_it(repo):
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo))
    commit(repo, "log")
    git(repo, "checkout", "-q", "master")
    write(repo, "other.py")                              # master gets code the branch never ran with
    commit(repo, "master moves on")
    git(repo, "checkout", "-q", "dal")
    p = check.plan(repo)
    assert p["level"] == "tam" and p["base_ahead"] == ["other.py"] and "birleştirilir" in p["why"]
    git(repo, "merge", "-q", "--no-edit", "master")      # merged: the log no longer covers the code
    p = check.plan(repo)
    assert p["level"] == "tam" and p["base_ahead"] == [] and p["full"]["code_since"] == ["other.py"]


@pytest.mark.parametrize("path", ["lean/PINS", "docs/rehber.md"])
def test_the_base_receiving_data_or_a_read_document_is_code(repo, path):
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo))
    commit(repo, "log")
    git(repo, "checkout", "-q", "master")
    write(repo, path, "master's\n")
    commit(repo)
    git(repo, "checkout", "-q", "dal")
    p = check.plan(repo)
    assert p["level"] == "tam" and p["base_ahead"] == [path]


def test_documentation_the_base_received_does_not_matter(repo):
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo))
    commit(repo, "log")
    git(repo, "checkout", "-q", "master")
    write(repo, "notlar.md", "master's\n")
    commit(repo)
    git(repo, "checkout", "-q", "dal")
    assert check.plan(repo)["level"] == "tamam"


def test_a_documentation_branch_waits_for_code_the_base_received(repo):
    """New code on the base may read a document this branch changed; the scan saw only this
    branch's code. Merged, the scan sees it."""
    write(repo, "notlar.md", "branch\n")
    commit(repo)
    git(repo, "checkout", "-q", "master")
    write(repo, "tests/test_notes.py", "N = 'notlar.md'\n")
    commit(repo)
    git(repo, "checkout", "-q", "dal")
    p = check.plan(repo)
    assert p["level"] == "tam" and p["base_ahead"] == ["tests/test_notes.py"]
    git(repo, "merge", "-q", "--no-edit", "master")
    p = check.plan(repo)
    assert p["level"] == "tam" and p["files"] == {"notlar.md": "kod"}   # now named by the merged test


def test_origin_master_is_the_base_when_there_is_one(repo):
    write(repo, "a.py")
    first = commit(repo, "merged into origin/master")
    git(repo, "update-ref", "refs/remotes/origin/master", first)    # master itself stays behind
    write(repo, "b.py")
    commit(repo)
    p = check.plan(repo)
    assert p["base"] == "origin/master" and p["merge_base"] == first and set(p["files"]) == {"b.py"}
    assert check.choose_base(repo, "master")[0] == "master"          # an explicit base is used as given
    assert set(check.plan(repo, "master")["files"]) == {"a.py", "b.py"}


@pytest.mark.parametrize("where", ["on master", "local merge on master", "branch at local master"])
def test_commits_only_local_master_holds_are_not_checked(repo, where):
    """Local master can hold commits never pushed: code committed on it, a local merge, a branch
    started from it. Its merge base with HEAD is then HEAD and those commits vanished (review)."""
    git(repo, "update-ref", "refs/remotes/origin/master", git(repo, "rev-parse", "master"))
    if where == "local merge on master":
        write(repo, "code.py", "x = 2\n")
        commit(repo)
        git(repo, "checkout", "-q", "master")
        git(repo, "merge", "-q", "--no-edit", "--no-ff", "dal")
    else:
        git(repo, "checkout", "-q", "master")
        write(repo, "code.py", "x = 2\n")
        commit(repo)
        if where == "branch at local master":
            git(repo, "checkout", "-q", "-b", "yeni-dal")
    p = check.plan(repo)
    assert p["level"] == "tam" and p["base"] == "origin/master" and code_files(p) == {"code.py"}, p


def test_on_the_base_branch_itself_nothing_is_decided(repo):
    git(repo, "checkout", "-q", "master")                           # no origin/master: master is the base
    write(repo, "code.py", "x = 2\n")
    commit(repo)
    p = check.plan(repo)
    assert p["level"] == "tam" and "dalının kendisi" in p["why"]


def test_no_base_unrelated_history_or_no_git_means_the_full_check(repo, tmp_path):
    p = check.plan(repo, "yok-boyle-dal")
    assert p["level"] == "tam" and "taban bulunamadı" in p["why"]
    git(repo, "checkout", "-q", "--orphan", "yetim")
    commit(repo, "unrelated")
    git(repo, "update-ref", "refs/remotes/origin/master", git(repo, "rev-parse", "master"))
    assert "ortak atası yok" in check.plan(repo)["why"]
    bare = tmp_path / "not-a-repo"
    bare.mkdir()
    assert check.plan(bare)["level"] == "tam" and check.plan_report(bare)[0] == 1


# --------------------------------------------------------------------------- fetching origin/master


@pytest.fixture
def cloned(tmp_path, git_env):
    """A branch in a clone of a bare `origin`, and a second clone that can push to origin/master."""
    origin, work, other = tmp_path / "origin.git", tmp_path / "work", tmp_path / "other"
    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, "init", "-q")
    write(seed, "code.py", "x = 1\n")
    write(seed, "notlar.md")
    commit(seed, "base")
    git(tmp_path, "clone", "-q", "--bare", str(seed), str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(work))
    git(tmp_path, "clone", "-q", str(origin), str(other))
    git(work, "checkout", "-q", "-b", "dal")
    return types.SimpleNamespace(origin=origin, work=work, other=other)


def test_the_plan_fetches_code_merged_on_the_remote(cloned):
    write(cloned.work, "code.py", "x = 2\n")
    full_log(cloned.work, commit(cloned.work))
    commit(cloned.work, "log")
    write(cloned.other, "remote.py")
    commit(cloned.other, "merged elsewhere")
    git(cloned.other, "push", "-q", "origin", "master")
    p = check.plan(cloned.work)
    assert p["fetch"] == "tamam" and p["level"] == "tam" and p["base_ahead"] == ["remote.py"], p
    assert check.plan(cloned.work, fetch=False)["base_ahead"] == ["remote.py"]    # the ref stays fetched


def test_without_a_fresh_base_only_a_report_change_passes(cloned):
    git(cloned.work, "remote", "set-url", "origin", str(cloned.origin.parent / "gone.git"))
    write(cloned.work, "code.py", "x = 2\n")
    full_log(cloned.work, commit(cloned.work))
    commit(cloned.work, "log")
    p = check.plan(cloned.work)
    assert p["fetch"].startswith("başarısız") and p["level"] == "tam" and "güncelliği bilinmiyor" in p["why"]
    assert check.plan(cloned.work, fetch=False)["level"] == "tam"                 # --no-fetch: same
    git(cloned.work, "checkout", "-q", "-b", "belge-dali", "origin/master")
    write(cloned.work, "notlar.md", "changed\n")
    assert check.plan(cloned.work)["level"] == "tam"                             # documentation: tam too
    git(cloned.work, "checkout", "-q", "notlar.md")
    write(cloned.work, "reports/eval_report.md", "rapor\n")
    assert check.plan(cloned.work)["level"] == "yok"                             # a report alone: no check


# --------------------------------------------------------------------------- reporting and the CLI


def test_a_failure_while_deciding_is_the_full_check(repo, monkeypatch):
    monkeypatch.setattr(check, "plan", lambda *a, **k: 1 / 0)
    rc, lines = check.plan_report(repo)
    assert rc == 1 and "karar verilemedi (ZeroDivisionError" in lines[-1]


def test_a_python_file_that_does_not_parse_makes_the_decision_tam(repo):
    write(repo, "notlar.md", "changed\n")
    write(repo, "tests/broken.py", "def (:\n")
    p = check.plan(repo)
    assert p["level"] == "tam" and "tests/broken.py" in p["why"]
    assert p["files"] == {"notlar.md": "?", "tests/broken.py": "?"}
    assert "değişen: 2 dosya" in "\n".join(check.render_plan(p))


def test_the_plan_command_exit_code(repo, monkeypatch, capsys):
    monkeypatch.setattr(check, "ROOT", repo)
    write(repo, "notlar.md", "changed\n")
    assert check.main(["--plan"]) == 0 and "karar: YOK" in capsys.readouterr().out
    write(repo, "code.py", "x = 2\n")
    assert check.main(["--plan"]) == 1 and "karar: TAM" in capsys.readouterr().out
    assert check.main(["--plan", "--base", "yok-boyle-dal"]) == 1


def test_the_quick_run_reminds_of_the_plan_without_changing_its_exit_code(repo, monkeypatch, capsys):
    monkeypatch.setattr(check, "ROOT", repo)
    monkeypatch.setattr(check, "_main", lambda args: 0)
    write(repo, "code.py", "x = 2\n")
    assert check.main([]) == 0
    out = capsys.readouterr().out
    assert "== kademeli kontrol" in out and "karar: TAM" in out


def test_the_gates_do_not_inherit_what_would_change_them():
    for var in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "MATHVERIFY_SANDBOX"):
        assert var not in check.ENV
    assert check.ENV["PYTHONUTF8"] == "1"


# --------------------------------------------------------------------------- this repository


def _tracked(pattern: str) -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z", pattern], cwd=ROOT, capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def test_the_documents_code_reads_in_this_repository():
    """Today one document is code: tests/test_cloud_scripts.py compares the bootstrap copies in the
    cloud guide with the scripts. A new reader must show up here as a deliberate change, and no
    string in check.py, its tests or the guard may name a document by accident. The .md files
    outside the documentation places (lean/README among them, which the tests copy) are code by
    their place."""
    tracked = _tracked("*" + MD)
    docs = [d for d in tracked if check.is_doc(d)]
    named = check.docs_named_by_code(ROOT, docs)
    guide = "docs/BULUT" + MD
    assert set(named) == {guide}, named
    assert named[guide].startswith("tests/test_cloud_scripts.py:")
    elsewhere = {d for d in tracked if not check.is_doc(d) and not check.is_report(d)}
    assert elsewhere == {"lean/README" + MD, "scripts/dev/README" + MD, "denetim/2026-09-25/README" + MD}


def test_the_scan_covers_every_tracked_python_file():
    scanned = {p.relative_to(ROOT).as_posix() for p in check.python_sources(ROOT)}
    assert set(_tracked("*.py")) <= scanned


def _code_part(line: str) -> str:
    """A shell line without its comment: '#' starts one only outside quotes and after a blank."""
    quote, prev = None, " "
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and prev in " \t":
            return line[:i]
        prev = ch
    return line


# Shell lines that mention a document but read none, by the SHA-1 of their stripped text (the text
# itself would name the documents here). A changed or new such line fails the test below until it
# is looked at and listed, or its document is covered by check.DOCS_READ_UNNAMED.
SHELL_MENTIONS = Counter({
    # `(cd "$REPO" && find lean -type f ! -name README... | ... sha256sum)`: README is left out of the hash
    ("scripts/cloud/session_start.sh", "4108f11f75a0"): 1,
    # `echo "- Önce HANDOFF..., sonra docs/BULUT... okunur."`: printed for the reader
    ("scripts/cloud/session_start.sh", "36afc9979672"): 1,
    # the same `find lean ... ! -name README...` fingerprint
    ("scripts/cloud/setup_env.sh", "4108f11f75a0"): 1,
    # `LOG "... put it in the setup script's text, docs/BULUT...)"`: a message pointing to the guide
    ("scripts/fetch_artifacts.sh", "87eaa2a78010"): 1,
})
_WALK = re.compile(r"(?:\bfind|\bcp\s+-\w*[rRa]\w*|\brsync\b[^|;&]*?|\btar\s+-?\w*c\w*f?)\s+[\"']?([\w./-]+)")


def test_shell_scripts_read_no_document_the_rule_misses():
    """The Python scan cannot see a shell script read a document. On every non-comment line of a
    tracked shell script, a mention of a document is either covered by check.DOCS_READ_UNNAMED (all
    the documents it could name) or one of SHELL_MENTIONS (looked at: not a read); and a directory
    of the repository that a script walks or copies (find, cp -r, rsync, tar c) must be covered."""
    docs = [d for d in _tracked("*" + MD) if check.is_doc(d)]
    mentions, walks = Counter(), set()
    for sh in _tracked("*.sh"):
        for line in (ROOT / sh).read_text(encoding="utf-8").splitlines():
            code = _code_part(line).strip()
            if not code or code.startswith("#"):
                continue
            for token, suffix in check.doc_tokens(code):
                hit = [d for d in docs if check.names_doc(token, d, suffix)]
                if not hit or not all(check.read_unnamed(d) for d in hit if check.is_doc(d)):
                    mentions[(sh, hashlib.sha1(code.encode("utf-8")).hexdigest()[:12])] += 1
                    break
            for d in _WALK.findall(code):
                d = d.strip("/")
                if d and d != "." and (ROOT / d).is_dir():
                    walks.add((sh, d))
    assert mentions == SHELL_MENTIONS, f"a shell line mentions a document: look at it, then list it " \
                                       f"here or cover the document in DOCS_READ_UNNAMED: {mentions - SHELL_MENTIONS}, " \
                                       f"stale: {SHELL_MENTIONS - mentions}"
    uncovered = {w for w in walks if check.is_doc(w[1] + "/x" + MD) and not check.read_unnamed(w[1] + "/x" + MD)}
    assert not uncovered, f"a shell script walks a directory whose documents the rule does not count: {uncovered}"
    assert ("scripts/cloud/setup_env.sh", "lean") in walks                  # the walk test sees the known one


def test_the_plan_runs_on_this_repository(monkeypatch):
    """Offline and without the real --full log: no test may depend on a report (the guard)."""
    monkeypatch.setattr(check, "REPORT_LOG", "reports/bu-testte-yok.log")
    rc, lines = check.plan_report(ROOT, fetch=False)
    assert rc in (0, 1) and lines[0].startswith("== kademeli kontrol") and "karar:" in lines[-1]


# --------------------------------------------------------------------------- the runtime guard


def test_the_guard_counts_unnamed_documents_and_reports(repo):
    write(repo, "reports/check_full.log", "log\n")
    opened = [repo / "docs" / "rehber.md", repo / "notlar.md", repo / "reports" / "eval_report.md",
              repo / "reports" / "check_full.log", repo / ".venv" / "pkg" / "x.md", repo.parent / "outside.md",
              repo / "code.py", repo / "pytest-cache-files-x" / "gone.md"]
    assert check.unexplained_doc_reads(repo, [str(p) for p in opened]) == [
        "notlar.md", "reports/check_full.log", "reports/eval_report.md"]


def test_the_guard_names_the_source_it_cannot_read(repo):
    write(repo, "tests/broken.py", "def (:\n")
    with pytest.raises(check.UnreadableSource, match="tests/broken.py"):
        check.unexplained_doc_reads(repo, [str(repo / "notlar.md")])


def test_the_guard_is_installed_in_this_session(request):
    """Importing the module installs the audit hook; the session only fails on a bad read if
    conftest also hands pytest its hooks."""
    import doc_read_guard
    assert doc_read_guard.installed()
    plugins = request.config.pluginmanager.get_plugins()
    for hook in ("pytest_sessionfinish", "pytest_terminal_summary"):
        assert any(getattr(p, hook, None) is getattr(doc_read_guard, hook) for p in plugins), hook
    guide = ROOT / "docs" / ("BULUT" + MD)
    guide.read_text(encoding="utf-8")
    assert os.path.realpath(guide) in doc_read_guard.OPENED
    assert doc_read_guard.problems() == []


def test_the_guard_sees_a_windows_copy(tmp_path, monkeypatch):
    """On Windows shutil.copy2 (and so copytree) copies with _winapi.CopyFile2 and opens nothing; the
    C function raises its own audit event (CPython 3.12-3.14 Modules/_winapi.c). Simulated here."""
    import doc_read_guard
    src = tmp_path / ("kopya" + MD)
    src.write_text("x\n", encoding="utf-8")
    doc_read_guard.OPENED.discard(os.path.realpath(src))

    class WinApi:
        COPY_FILE_ALLOW_DECRYPTED_DESTINATION, COPY_FILE_COPY_SYMLINK, ERROR_PRIVILEGE_NOT_HELD = 0, 0, 1314

        @staticmethod
        def CopyFile2(existing, new, flags):
            sys.audit("_winapi.CopyFile2", existing, new, flags)

    monkeypatch.setattr(shutil, "_winapi", WinApi)
    shutil.copy2(src, tmp_path / "out.bin")
    assert os.path.realpath(src) in doc_read_guard.OPENED


def test_the_guard_follows_links(tmp_path):
    import doc_read_guard
    target = tmp_path / ("hedef" + MD)
    target.write_text("x\n", encoding="utf-8")
    doc_read_guard.OPENED.discard(os.path.realpath(target))
    link = tmp_path / "bag.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    link.read_text(encoding="utf-8")
    assert os.path.realpath(target) in doc_read_guard.OPENED


def test_the_guard_never_breaks_an_open():
    import doc_read_guard

    class Bad:
        def __fspath__(self):
            raise RuntimeError("no path")

    doc_read_guard.record("open", (Bad(), "r", 0))                   # must not raise
    doc_read_guard.record("open", (7, "r", 0))


def test_the_guard_keeps_a_worse_exit_status(monkeypatch):
    import doc_read_guard
    monkeypatch.setattr(doc_read_guard, "problems", lambda: ["ERROR belge-okuma: x"])
    for before, after in [(pytest.ExitCode.OK, pytest.ExitCode.TESTS_FAILED),
                          (pytest.ExitCode.INTERRUPTED, pytest.ExitCode.INTERRUPTED),
                          (pytest.ExitCode.TESTS_FAILED, pytest.ExitCode.TESTS_FAILED)]:
        session = types.SimpleNamespace(exitstatus=before)
        doc_read_guard.pytest_sessionfinish(session, before)
        assert session.exitstatus == after
    monkeypatch.setattr(doc_read_guard, "problems", lambda: [])
    doc_read_guard.pytest_sessionfinish(types.SimpleNamespace(exitstatus=0), 0)   # leaves nothing to print


def _guarded_session(tmp_path, body: str):
    # A fresh directory each time: two bodies of the same length written within a second reused
    # the first one's cached bytecode.
    t = Path(tempfile.mkdtemp(prefix="suite-", dir=tmp_path))
    (t / "test_reads.py").write_text(body, encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT / "tests"), str(ROOT / "src")]),
               PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTEST_ADDOPTS", None)
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-rfEs", "-p", "no:cacheprovider",
                           "-p", "doc_read_guard", "--rootdir", str(t), str(t / "test_reads.py")],
                          cwd=t, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_a_session_that_reads_an_unnamed_document_fails(tmp_path):
    """End to end: a suite whose passing test opens a document no string constant names (the path
    is built at run time, as a glob would) must fail as a session and say which document, on a line
    of its own that check.py's pytest gate prints."""
    docs = [d for d in _tracked("*" + MD) if check.is_doc(d)]
    unnamed = sorted(set(docs) - set(check.docs_named_by_code(ROOT, docs)))[0]
    target = (ROOT / unnamed).as_posix()
    p = _guarded_session(tmp_path, f"def test_reads():\n    open({target!r}, encoding='utf-8').read()\n")
    assert p.returncode == 1 and "1 passed" in p.stdout, p.stdout + p.stderr
    assert any(f"testler {unnamed} dosyasını açtı" in l for l in check.pytest_problems(p.stdout)), p.stdout
    for report in ("reports/eval_report" + MD, check.REPORT_LOG):
        path = (ROOT / report).as_posix()
        p = _guarded_session(tmp_path, f"from pathlib import Path\ndef test_reads():\n    Path({path!r}).read_bytes()\n")
        assert p.returncode == 1 and f"testler {report} dosyasını açtı" in p.stdout, p.stdout + p.stderr


def test_a_session_that_reads_only_named_documents_passes(tmp_path):
    guide = (ROOT / "docs" / ("BULUT" + MD)).as_posix()
    lean = (ROOT / "lean").as_posix()
    p = _guarded_session(tmp_path, "import shutil\n"
                                   f"def test_reads(tmp_path):\n    open({guide!r}, encoding='utf-8').read()\n"
                                   f"    shutil.copytree({lean!r}, tmp_path / 'lean', ignore=shutil.ignore_patterns('.lake'))\n")
    assert p.returncode == 0 and "belge-okuma" not in p.stdout, p.stdout + p.stderr

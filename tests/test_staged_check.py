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
    """LF on every OS: on Windows write_text would write CRLF, and a test of line endings would hold
    nothing there (review)."""
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


READER = 'from pathlib import Path\nGUIDE = Path(__file__).parent.parent / "docs" / "rehber.md"\n'


@pytest.fixture
def repo(tmp_path, git_env):
    """master: code, a document a test reads (docs/rehber.md), one nothing reads (notlar.md),
    reports, a lock the test environment meets; then the branch `dal` checked out. No remote: the
    local master is the base."""
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q")
    write(r, "code.py", "x = 1\n")
    write(r, "docs/rehber.md")
    write(r, "notlar.md")
    write(r, "tests/test_reader.py", READER)
    write(r, "reports/eval_report.md")
    write(r, "reports/check_full.log", "old\n")
    write(r, "requirements.lock", "sympy==1.14.0\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "base")
    git(r, "checkout", "-q", "-b", "dal")
    return r


def commit(repo: Path, msg: str = "c") -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


def full_log(repo: Path, sha: str, *, dirty: int = 0, gates=("a", "b"), failed=(), total_line=True,
             end_sha: str | None = None, end_dirty: int = 0, end_line=True, totals=None, warmup="0",
             extra=(), reports_line=True, env=("ortam: Python 3",), lock=None) -> None:
    """A --full log as main writes it, for the reports on disk now (the run just wrote them) and the
    lock on disk, met (`lock`: other kilit lines)."""
    run = " · 2026-09-26 12:00:00 · dal @ {} · commit edilmemiş değişiklik: {} dosya"
    if lock is None:
        lock = (f"kilit: requirements.lock {check.lock_digest(repo)} · 1 paket · uyuşmayan: yok",)
    lines = ["check.py --full" + run.format(sha[:7], dirty), *env, *lock, "", "== Lean ısınma =="]
    if warmup is not None:
        lines.append(f"  lean_warmup: 9 s (exit {warmup})")
    lines += ["== testler ==", "  pytest: 1 s (exit 0)", *extra, "", "== kapılar =="]
    lines += [f"  [OK  ] {g}  1   (hedef: 1)" for g in gates]
    lines += [f"  [FAIL] {g}  0   (hedef: 1)" for g in failed]
    n = len(gates) + len(failed)
    if total_line:
        lines += ["", *(totals or [f"{len(gates)}/{n} kapı geçti"])]
    if end_line:
        lines += ["", "check.py --full sonu" + run.format((end_sha or sha)[:7], end_dirty)]
    if reports_line:
        lines.append("check.py --full raporları · " + " · ".join(f"{k} {v}" for k, v in check.report_digests(repo).items()))
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
    # a case-insensitive disk: Docs/ is docs/, Reports/ is reports/
    assert check.is_doc("Docs/x.md") and check.is_report("Reports/eval_report.md") and check.is_report("REPORTS/CHECK_FULL.LOG")
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
    # a glob after a run-time stem: f"docs/{stem}[12].md", "docs/%s?.md" % stem (review)
    assert check.names_doc("[12]" + MD, "docs/notes1.md", suffix=True)
    assert check.names_doc("?" + MD, "docs/notes1.md", suffix=True)
    assert not check.names_doc("[12]" + MD, "docs/notes3.md", suffix=True)


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


def test_bytes_constants_are_names_too(tmp_path, git_env):
    write(tmp_path, "n.py", "k = open(b'docs/h.md')\n")
    assert check.docs_named_by_code(tmp_path, ["docs/h.md", "docs/i.md"]) == {"docs/h.md": "n.py:1"}


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
    assert p["fetch"] == "uzak yok"
    rc, lines = check.plan_report(repo)
    assert rc == 0 and lines[-1].startswith("  karar: YOK")


def test_reports_need_the_full_run_that_wrote_them(repo):
    """A report is a --full's output: a branch that changes only reports needs no check when the
    last --full ran on this code, wrote them and is committed; a report from a direct harness call
    or a hand edit would otherwise enter master unchecked (review, 26 Sep 2026)."""
    write(repo, "reports/eval_report.md", "new\n")
    commit(repo)
    p = check.plan(repo)
    assert p["level"] == "tam" and "geçerli bir --full'a bağlı değil" in p["why"] and p["full"]["why"] == "günlüğün başlığı okunamadı"
    full_log(repo, git(repo, "rev-parse", "HEAD"))                     # the run on this code wrote them
    p = check.plan(repo)
    assert p["level"] == "tam" and p["why"] == "raporlar ya da günlük commit edilmemiş" and p["advice"] == check._ADVICE_COMMIT
    commit(repo, "log")
    assert check.plan(repo)["level"] == "yok"
    write(repo, "reports/eval_report.md", "by hand\n")
    commit(repo, "edited")
    p = check.plan(repo)
    assert p["level"] == "tam" and p["full"]["why"] == check.REPORTS_CHANGED and p["advice"] == check._ADVICE_REPORTS.format(paths="reports/eval_report.md")


def test_reports_of_a_run_on_other_code_are_not_accepted(repo):
    write(repo, "code.py", "x = 2\n")
    sha = commit(repo)
    git(repo, "checkout", "-q", "-b", "rapor-dali", "master")          # the reports, without that code
    write(repo, "reports/eval_report.md", "new\n")
    full_log(repo, sha)
    commit(repo, "reports")
    p = check.plan(repo)
    assert p["level"] == "tam" and "bu kodda değil" in p["why"] and p["full"]["code_since"] == ["code.py"]


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
    assert p["level"] == "tam" and p["hidden"] == ["code.py"] and "göstermiyor" in p["why"]
    assert p["advice"] == check._ADVICE_HIDDEN
    # decided before the files were listed: how many changed is unknown, not zero (26 Sep 2026)
    write(repo, "notlar.md", "changed\n")
    p = check.plan(repo)
    assert p["files"] is None and "  değişen: okunmadı" in check.render_plan(p), check.render_plan(p)


def test_an_untracked_gitignore_that_hides_code_decides_nothing(repo):
    """A tool's untracked .gitignore holding "*" ignores itself and untracked code beside it; a
    --full would measure code the merge lacks (review, 26 Sep 2026). One under a directory the
    tracked rules ignore (.venv/.gitignore) hides nothing of the project."""
    write(repo, ".gitignore", ".venv/\n")
    commit(repo, "ignore .venv")
    write(repo, ".venv/.gitignore", "*\n")
    write(repo, ".venv/lib/x.py")
    assert check.hidden_files(repo) == []
    write(repo, "helpers/.gitignore", "*\n")
    write(repo, "helpers/extra.py")
    assert check.hidden_files(repo) == ["helpers/.gitignore"] and check.dirty_files(repo) == ["helpers/.gitignore"]
    p = check.plan(repo)
    assert p["level"] == "tam" and p["hidden"] == ["helpers/.gitignore"] and p["advice"] == check._ADVICE_HIDDEN


def test_a_clean_filter_that_hides_edits_decides_nothing(repo):
    """A filter from .git/info/attributes rewrites code before git compares it: the edit on disk
    reaches no diff (review)."""
    git(repo, "config", "filter.gizle.clean", "grep -v GIZLI")
    git(repo, "config", "filter.gizle.smudge", "cat")
    (repo / ".git" / "info").mkdir(exist_ok=True)
    (repo / ".git" / "info" / "attributes").write_text("*.py filter=gizle\n", encoding="utf-8")
    write(repo, "code.py", "x = 1\ny = 2  # GIZLI\n")
    assert check.changed_since(repo, "HEAD") == []                    # what the filter hides
    assert "code.py" in check.hidden_files(repo)
    assert check.plan(repo)["level"] == "tam"


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
    write(repo, "reports/eval_report.md", "new\n")       # the run rewrites its reports
    full_log(repo, sha)                                   # --full ran on this commit, clean, all gates OK
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
    (dict(dirty="?"), "koşunun başında git değişiklikleri veremedi"),
    (dict(end_dirty="?"), "ağaç koşu sırasında değişti"),
    (dict(total_line=False, end_line=False), "koşu bitmemiş"),
    (dict(failed=("c",)), "kapılar geçmedi (2/3)"),
    (dict(gates=()), "kapılar geçmedi (0/0)"),
    (dict(gates=("a",), totals=["2/2 kapı geçti"]), "kapılar geçmedi (2/2)"),       # marks disagree with the total
    (dict(totals=["1/2 kapı geçti", "2/2 kapı geçti"]), "kapılar geçmedi (2/2)"),   # two runs in one log
    (dict(end_line=False), "sonu kaydedilmemiş"),
    (dict(end_dirty=1), "ağaç koşu sırasında değişti"),
    (dict(end_sha="0" * 40), "ağaç koşu sırasında değişti"),
    (dict(warmup="1"), "Lean ısınması başarısız"),
    (dict(warmup=None), "Lean ısınması başarısız ya da kayıtsız"),
    (dict(extra=["    SKIPPED [87] tests/test_f5_lean.py:19: Lean/Mathlib toolchain not available"]),
     "Lean testleri atlanmış"),
    (dict(reports_line=False), "raporların özeti kaydedilmemiş"),
])
def test_a_full_run_that_proves_nothing_is_not_accepted(repo, log, why):
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo), **log)
    p = check.plan(repo)
    assert p["level"] == "tam" and not p["full"]["ok"] and why in p["full"]["why"], p["full"]


def test_reports_changed_after_the_run_are_not_its_reports(repo):
    """A report edited by hand, or overwritten by a partial harness run into reports/, after the
    --full no longer rides on it."""
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo))
    commit(repo, "log")
    assert check.plan(repo)["level"] == "tamam"
    write(repo, "reports/eval_report.md", "one item\n")
    p = check.plan(repo)
    assert p["level"] == "tam" and p["full"]["why"] == check.REPORTS_CHANGED and p["advice"] == check._ADVICE_REPORTS.format(paths="reports/eval_report.md")
    git(repo, "restore", "reports/")                                   # what the advice says
    assert check.plan(repo)["level"] == "tamam"
    write(repo, "reports/Yeni_Report.MD", "added\n")                   # a new report, whatever its case
    assert check.plan(repo)["full"]["why"] == check.REPORTS_CHANGED


def test_a_report_changed_before_its_run_was_committed_is_lost(repo):
    """`git restore reports/` would also bring back the old log and throw the new run away (review)."""
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo))                                      # the run's log, not committed yet
    write(repo, "reports/eval_report.md", "a quick check.py after the --full\n")
    p = check.plan(repo)
    assert p["full"]["why"] == check.REPORTS_CHANGED and p["advice"] == check._ADVICE_REPORTS_LOST, p


def test_evidence_that_is_not_committed_is_not_what_gets_merged(repo):
    """The log and the digests are read from disk, but a pull request merges HEAD (review)."""
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo))
    p = check.plan(repo)
    assert p["level"] == "tam" and p["why"] == "raporlar ya da günlük commit edilmemiş" and p["advice"] == check._ADVICE_COMMIT
    git(repo, "add", "reports/check_full.log")                         # staged is not committed either
    assert check.plan(repo)["level"] == "tam"
    commit(repo, "log")
    assert check.plan(repo)["level"] == "tamam"
    log = (repo / "reports" / "check_full.log").read_text(encoding="utf-8")
    write(repo, "reports/check_full.log", "old\n")
    commit(repo, "log lost")
    write(repo, "reports/check_full.log", log)                         # right on disk, wrong in HEAD
    assert check.plan(repo)["level"] == "tam"


def test_the_reports_a_full_run_rewrites_are_the_harnesses_reports():
    written = {f"reports/{name}" for path, name in CODE_DOC_CONSTANTS
               if path.startswith("harness/") and not name.startswith("_")}
    assert check.REWRITTEN == written | {check.REPORT_LOG} and len(written) == 5


def test_a_report_edited_before_the_run_makes_it_dirty(repo):
    """A --full rewrites its own reports but only binds the others (the F3 reports): one edited
    before the run is uncommitted change, not output (review)."""
    write(repo, "reports/f3_report.md", "committed\n")
    commit(repo)
    write(repo, "reports/eval_report.md", "left by a quick check.py\n")
    write(repo, "reports/check_full.log", "being written\n")
    assert check.dirty_files(repo) == []
    write(repo, "reports/f3_report.md", "by hand\n")
    assert check.dirty_files(repo) == ["reports/f3_report.md"]
    if not (repo / "reports" / "EVAL_REPORT.MD").exists():             # a case-sensitive file system
        write(repo, "reports/EVAL_REPORT.MD", "another file\n")
        assert check.dirty_files(repo) == ["reports/EVAL_REPORT.MD", "reports/f3_report.md"]


def test_a_full_run_log_that_is_not_one(repo):
    write(repo, "code.py", "x = 2\n")
    commit(repo)
    for text in ("", "check.py --full · ? · ? @ ? · x\n"):
        write(repo, "reports/check_full.log", text)
        assert "başlığı okunamadı" in check.plan(repo)["full"]["why"]
    (repo / "reports" / "check_full.log").write_bytes(b"\xff\xfe")
    assert check.plan(repo)["full"]["why"] == "günlük okunamadı (UTF-8 değil)"
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


def test_the_full_run_writes_what_the_plan_accepts(repo, monkeypatch, capsys):
    """main --full's header and closing line, with the gates stubbed: reports are not counted (the
    run rewrites them, a quick check.py leaves eval_report.md modified), anything else is, and a
    file changed during the run shows in the closing line."""
    write(repo, "code.py", "x = 2\n")
    commit(repo)
    write(repo, "reports/eval_report.md", "left by a quick check.py\n")
    monkeypatch.setattr(check, "ROOT", repo)
    monkeypatch.setattr(check, "_main", lambda args: print("  lean_warmup: 1 s (exit 0)\n\n  [OK  ] a  1\n\n1/1 kapı geçti") or 0)
    assert check.main(["--full"]) == 0
    assert check.last_full_run(repo)["ok"]
    commit(repo, "the run's reports and log")
    assert check.plan(repo)["level"] == "tamam"
    monkeypatch.setattr(check, "_main", lambda args: write(repo, "code.py", "x = 3\n") or print("1/1 kapı geçti") or 0)
    assert check.main(["--full"]) == 0
    lines = (repo / "reports" / "check_full.log").read_text(encoding="utf-8").splitlines()
    assert lines[0].endswith("commit edilmemiş değişiklik: 0 dosya") and lines[1].startswith("ortam: Python")
    assert re.search(r" · \d{4}-\d\d-\d\d \d\d:\d\d:\d\d UTC · ", lines[0]) and lines[3] == ""
    assert re.fullmatch(r"kilit: requirements\.lock [0-9a-f]{16} · 1 paket · uyuşmayan: yok", lines[2])
    assert lines[-2].startswith("check.py --full sonu") and lines[-2].endswith("commit edilmemiş değişiklik: 1 dosya")
    assert " UTC · " in lines[-2]
    assert lines[-1].startswith("check.py --full raporları · reports/eval_report.md ")
    capsys.readouterr()
    assert check.main(["--full"]) == 0                                 # code.py is still changed: said at once
    lines = (repo / "reports" / "check_full.log").read_text(encoding="utf-8").splitlines()
    assert lines[0].endswith("commit edilmemiş değişiklik: 1 dosya")
    assert lines[3] == "UYARI: ağaç temiz değil, bu koşu --plan için kanıt olmaz: code.py"
    assert "UYARI: ağaç temiz değil" in capsys.readouterr().out


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
    assert p["level"] == "tam" and p["base_ahead"] == ["tests/test_notes.py"] and p["advice"] == check._ADVICE_MERGE
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
    assert "  değişen: okunmadı" in check.plan_report(bare)[1]


# --------------------------------------------------------------------------- fetching origin/master


REAL_LOCAL_ORIGIN = check.local_origin


@pytest.fixture
def cloned(tmp_path, git_env, monkeypatch):
    """A branch in a clone of a bare `origin`, and a second clone that can push to origin/master.
    The bare repository stands in for GitHub: an origin on this machine is otherwise never fresh."""
    monkeypatch.setattr(check, "local_origin", lambda url: False)
    origin, work, other = tmp_path / "origin.git", tmp_path / "work", tmp_path / "other"
    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, "init", "-q")
    write(seed, "code.py", "x = 1\n")
    write(seed, "notlar.md")
    write(seed, "requirements.lock", "sympy==1.14.0\n")
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


def test_without_a_fresh_base_or_a_readable_remote_nothing_passes(cloned):
    git(cloned.work, "remote", "set-url", "origin", str(cloned.origin.parent / "gone.git"))
    write(cloned.work, "code.py", "x = 2\n")
    full_log(cloned.work, commit(cloned.work))
    commit(cloned.work, "log")
    p = check.plan(cloned.work)
    assert p["fetch"].startswith("başarısız") and p["level"] == "tam" and "güncelliği bilinmiyor" in p["why"]
    assert p["advice"] == check._ADVICE_FETCH
    assert check.plan(cloned.work, fetch=False)["level"] == "tam"                 # --no-fetch: same
    git(cloned.work, "checkout", "-q", "-b", "belge-dali", "origin/master")
    write(cloned.work, "notlar.md", "changed\n")
    assert check.plan(cloned.work)["level"] == "tam"                             # documentation: tam too
    git(cloned.work, "checkout", "-q", "notlar.md")
    write(cloned.work, "reports/eval_report.md", "rapor\n")
    full_log(cloned.work, git(cloned.work, "rev-parse", "HEAD"))
    commit(cloned.work, "reports")
    p = check.plan(cloned.work)                                                 # a report bound by its run
    assert p["level"] == "tam" and p["why"] == "origin'deki belge-dali okunamadı" and p["advice"] == check._ADVICE_FETCH


# --------------------------------------------------------------------------- what gets merged


@pytest.mark.parametrize("with_log", [True, False])
def test_committed_code_reverted_only_in_the_working_tree_is_still_code(repo, with_log):
    """A pull request merges HEAD, not the working tree: code committed after the --full and then
    reverted only on disk (`git checkout HEAD~1 -- file`) is still in what gets merged (review)."""
    write(repo, "code.py", "x = 2\n")
    sha = commit(repo)
    if with_log:
        full_log(repo, sha)
        commit(repo, "log")
    write(repo, "code.py", "x = 3\n")
    commit(repo, "after the run")
    git(repo, "checkout", "HEAD~1", "--", "code.py")       # the working tree is back, HEAD is not
    write(repo, "notlar.md", "edited\n")
    p = check.plan(repo)
    assert p["level"] == "tam" and "code.py" in code_files(p), p
    if with_log:
        assert p["full"]["code_since"] == ["code.py"]


def test_a_change_staged_then_undone_on_disk_is_still_seen(repo):
    write(repo, "code.py", "x = 2\n")
    git(repo, "add", "code.py")
    write(repo, "code.py", "x = 1\n")                      # disk equals HEAD, the index does not
    assert code_files(check.plan(repo)) == {"code.py"}


def test_unpushed_commits_of_local_master_count_as_what_the_base_received(repo):
    """A local merge brings local master's unpushed commits in: the plan against origin/master
    must see them too (review)."""
    git(repo, "update-ref", "refs/remotes/origin/master", git(repo, "rev-parse", "master"))
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo))
    commit(repo, "log")
    assert check.plan(repo)["level"] == "tamam"
    git(repo, "checkout", "-q", "master")
    write(repo, "src_yerel.py")
    commit(repo, "merged locally, not pushed")
    git(repo, "checkout", "-q", "dal")
    p = check.plan(repo)
    assert p["level"] == "tam" and p["base_ahead"] == ["src_yerel.py"]
    # origin/master received nothing: merging it is a no-op, so the reason names local master (review)
    assert "yerel master'da push edilmemiş kod var (src_yerel.py)" in p["why"] and p["advice"] == check._ADVICE_LOCAL_MASTER


def test_the_rule_files_never_approve_their_own_change(repo):
    write(repo, "scripts/check.py", "RULE = 1\n")
    full_log(repo, commit(repo))
    commit(repo, "log")
    p = check.plan(repo)
    assert p["level"] == "tam" and "kuralın kendi dosyaları" in p["why"] and p["full"]["ok"]
    assert check.render_plan(p)[-1].endswith(check._ADVICE_RULES)   # not "run the --full" again
    # the decision and its allowlists: a file off this list would judge its own change
    assert set(check.RULE_FILES) == {"scripts/check.py", "tests/doc_read_guard.py", "tests/conftest.py",
                                     "tests/test_staged_check.py"}


def test_submodule_moves_are_seen_whatever_the_config(repo, tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    git(lib, "init", "-q")
    write(lib, "a.py")
    commit(lib, "lib 1")
    git(repo, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(lib), "vendor/lib")
    git(repo, "checkout", "-q", "master")
    commit(repo, "submodule on master")
    git(repo, "checkout", "-q", "dal")
    git(repo, "merge", "-q", "--no-edit", "master")
    git(repo, "-C", "vendor/lib", "config", "user.name", "t")
    write(repo, "vendor/lib/b.py")
    git(repo, "-C", "vendor/lib", "add", "-A")
    git(repo, "-C", "vendor/lib", "commit", "-q", "-m", "lib 2")
    git(repo, "config", "diff.ignoreSubmodules", "all")     # the user's config must not hide the move
    commit(repo, "bump")
    assert "vendor/lib" in code_files(check.plan(repo))


def test_a_nested_worktree_is_not_content(repo):
    """git lists a worktree or clone inside the tree as one untracked directory; it is not the
    project's content and must not make every log dirty (review)."""
    git(repo, "worktree", "add", "-q", ".claude/worktrees/onceki", "HEAD")
    write(repo, "notlar.md", "changed\n")
    p = check.plan(repo)
    assert p["files"] == {"notlar.md": "belge"} and check.dirty_files(repo) == ["notlar.md"]


def test_a_tracked_link_to_a_document_makes_it_read(repo):
    write(repo, "docs/veri.md", "data\n")
    (repo / "evalset").mkdir()
    try:
        os.symlink("../docs/veri.md", repo / "evalset" / "x.json")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    git(repo, "checkout", "-q", "master")
    commit(repo, "a data item that is a link")
    git(repo, "checkout", "-q", "dal")
    git(repo, "merge", "-q", "--no-edit", "master")
    write(repo, "docs/veri.md", "changed\n")
    p = check.plan(repo)
    assert p["files"] == {"docs/veri.md": "kod"} and p["named"]["docs/veri.md"] == "bağlantı: evalset/x.json"


# --------------------------------------------------------------------------- the base must be fresh


def test_a_single_branch_clone_still_fetches_master(cloned):
    """`git fetch origin master` with a refspec that does not map master only writes FETCH_HEAD:
    origin/master stayed stale and TAMAM ignored the code merged on the remote (review)."""
    git(cloned.work, "config", "remote.origin.fetch", "+refs/heads/dal:refs/remotes/origin/dal")
    write(cloned.work, "code.py", "x = 2\n")
    full_log(cloned.work, commit(cloned.work))
    commit(cloned.work, "log")
    write(cloned.other, "remote.py")
    commit(cloned.other, "merged elsewhere")
    git(cloned.other, "push", "-q", "origin", "master")
    p = check.plan(cloned.work)
    assert p["fetch"] == "tamam" and p["base_ahead"] == ["remote.py"] and p["level"] == "tam", p


def test_a_base_other_than_the_fetched_master_is_not_fresh(cloned):
    write(cloned.other, "remote.py")
    commit(cloned.other, "merged elsewhere")
    git(cloned.other, "push", "-q", "origin", "master")
    git(cloned.work, "checkout", "-q", "-b", "belge-dali", "master")     # local master: now stale
    write(cloned.work, "notlar.md", "changed\n")
    p = check.plan(cloned.work, "master")
    assert p["fetch"] == "tamam" and p["level"] == "tam" and "güncelliği bilinmiyor" in p["why"], p
    assert check.plan(cloned.work)["level"] == "tam"                      # origin/master: remote.py is ahead



def test_a_stale_base_still_lists_what_changed(cloned):
    """The stale-base verdict was a copy of the plan taken before the files were read: it rendered
    "değişen: 0 dosya" for a branch that had changed two documents (26 Sep 2026)."""
    write(cloned.work, "notlar.md", "changed\n")
    p = check.plan(cloned.work, fetch=False)
    assert "güncelliği bilinmiyor" in p["why"] and p["files"] == {"notlar.md": "belge"}, p
    write(cloned.work, "code.py", "x = 2\n")
    p = check.plan(cloned.work, fetch=False)
    assert "güncelliği bilinmiyor" in p["why"] and p["files"] == {"notlar.md": "belge", "code.py": "kod"}, p
    git(cloned.work, "remote", "set-url", "origin", str(cloned.origin.parent / "gone.git"))
    rc, lines = check.plan_report(cloned.work)
    assert rc == 1 and "  değişen: 2 dosya (kod 1, belge 1, rapor 0)" in lines, lines
    assert any(line.startswith("  karar: TAM · tabanın güncelliği bilinmiyor (fetch: başarısız") for line in lines)

def test_head_must_be_what_its_upstream_holds(cloned):
    """The pull request merges the pushed head: a decision about an unpushed HEAD says nothing
    about it (review)."""
    write(cloned.work, "notlar.md", "pushed\n")
    commit(cloned.work)
    git(cloned.work, "push", "-q", "-u", "origin", "dal")
    assert check.plan(cloned.work)["level"] == "yok"
    write(cloned.work, "notlar.md", "not pushed\n")
    commit(cloned.work)
    p = check.plan(cloned.work)
    assert p["level"] == "tam" and "push edilmemiş" in p["why"] and p["advice"] == check._ADVICE_SYNC
    git(cloned.work, "push", "-q", "origin", "dal")
    assert check.plan(cloned.work)["level"] == "yok"


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
    assert "  değişen: 2 dosya (kod 0, belge 0, rapor 0, sınıflanmadı 2)" in check.render_plan(p)


def test_the_plan_command_exit_code(repo, monkeypatch, capsys):
    monkeypatch.setattr(check, "ROOT", repo)
    write(repo, "notlar.md", "changed\n")
    assert check.main(["--plan"]) == 0 and "karar: YOK" in capsys.readouterr().out
    write(repo, "code.py", "x = 2\n")
    assert check.main(["--plan"]) == 1 and "karar: TAM" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        check.main(["--plan", "--base", "HEAD"])          # no base to choose: --base HEAD made code vanish (review)


def test_the_quick_run_reminds_of_the_plan_without_changing_its_exit_code(repo, monkeypatch, capsys):
    monkeypatch.setattr(check, "ROOT", repo)
    monkeypatch.setattr(check, "_main", lambda args: 0)
    write(repo, "code.py", "x = 2\n")
    assert check.main([]) == 0
    out = capsys.readouterr().out
    assert "== kademeli kontrol" in out and "karar: TAM" in out


def test_the_gates_do_not_inherit_what_would_change_them(monkeypatch):
    names = ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "MATHVERIFY_SANDBOX",
             "MATHVERIFY_CALIBRATION", "FORCE_COLOR", "PYTHONOPTIMIZE", "PYTHONHASHSEED")
    for var in names:
        monkeypatch.setenv(var, "on")
    monkeypatch.setenv("PY_COLORS", "1")
    monkeypatch.setenv("MATHVERIFY_LEAN_PROJECT", "/lean")
    spec = importlib.util.spec_from_file_location("check_script_env", ROOT / "scripts" / "check.py")
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)                        # ENV is built when the script loads
    assert not set(names) & set(fresh.ENV) and fresh.ENV["PYTHONUTF8"] == "1" and fresh.ENV["PY_COLORS"] == "0"
    assert fresh.ENV["MATHVERIFY_LEAN_PROJECT"] == "/lean"


def test_the_log_names_the_environment_but_no_value(monkeypatch):
    monkeypatch.setitem(check.ENV, "MATHVERIFY_DENEME_ANAHTAR", "gizli-deger-123")
    line, lock = check.environment_lines(ROOT)
    assert line.startswith("ortam: Python ") and "sympy " in line and "z3-solver " in line
    assert "MATHVERIFY_DENEME_ANAHTAR" in line and "gizli-deger-123" not in line + lock
    assert re.fullmatch(r"kilit: requirements\.lock [0-9a-f]{16} · \d+ paket · uyuşmayan: .+", lock)


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
    assert elsewhere == {"lean/README" + MD, "scripts/dev/README" + MD, "denetim/2026-09-25/README" + MD,
                         "denetim/2026-09-26/README" + MD}


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


# Every string or bytes constant that looks like a document name or the documentation directory,
# in the Python code the tests do not guard at run time: the harnesses a --full runs, the scripts,
# the verifier (denetim/ holds audit tools no check runs). Report names are outputs; check.py's
# own constants are the rule's. A new one means code that may handle documents: look at it, then
# list it here (or make it a named read).
CODE_DOC_CONSTANTS = {
    ("harness/adversarial.py", "adversarial_report.md"), ("harness/calibrate.py", "calibration_report.md"),
    ("harness/run_eval.py", "eval_report.md"), ("harness/run_f3.py", "_report.md"),
    ("harness/run_solver.py", "_report.md"),
    ("harness/run_lean.py", "lean_report.md"), ("harness/soundness_fuzz.py", "soundness_report.md"),
    ("scripts/check.py", ".md"), ("scripts/check.py", "docs/"),
}


def test_code_outside_the_tests_handles_no_document_unseen():
    """The static scan misses a name built without a .md constant in it ("".join, an EXT constant
    and a type test after a walk) and the runtime guard sees only the test process: for the code
    that produces the gates, every .md-shaped constant is pinned (review, 26 Sep 2026)."""
    found = set()
    for where, text, _ in check.code_strings(ROOT):
        path = where.rsplit(":", 1)[0]
        if path.startswith(("tests/", "denetim/")):
            continue
        low = text.lower()
        if MD in low or low.strip("/") == "docs" or low.startswith("docs/"):
            found.add((path, text))
    assert found == CODE_DOC_CONSTANTS, f"new: {found - CODE_DOC_CONSTANTS}, gone: {CODE_DOC_CONSTANTS - found}"


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
              repo / "code.py", repo / "pytest-cache-files-x" / "gone.md", repo / "gone.md"]
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
    link = tmp_path / "bag.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    doc_read_guard.OPENED.discard(os.path.realpath(target))          # the write and the link itself were seen
    link.read_text(encoding="utf-8")                                  # a read under a name that hides it
    assert os.path.realpath(target) in doc_read_guard.OPENED


def test_the_guard_sees_a_hard_link(tmp_path):
    import doc_read_guard
    target = tmp_path / ("sert" + MD)
    target.write_text("x\n", encoding="utf-8")
    doc_read_guard.OPENED.discard(os.path.realpath(target))
    try:
        os.link(target, tmp_path / "ikinci-ad.txt")                   # the second name is no link to follow
    except (OSError, NotImplementedError):
        pytest.skip("hard links are not available here")
    assert os.path.realpath(target) in doc_read_guard.OPENED


def test_a_hard_link_s_source_is_read_from_the_working_directory(tmp_path, monkeypatch):
    """Unlike a symlink's target, os.link's source is a path like any other (review)."""
    import doc_read_guard
    write(tmp_path, "sert" + MD)
    (tmp_path / "alt").mkdir()
    doc = os.path.realpath(tmp_path / ("sert" + MD))
    doc_read_guard.OPENED.discard(doc)
    monkeypatch.chdir(tmp_path)
    try:
        os.link("sert" + MD, "alt/ikinci-ad.txt")
    except (OSError, NotImplementedError):
        pytest.skip("hard links are not available here")
    assert doc in doc_read_guard.OPENED


def test_the_guard_sees_a_linked_directory(tmp_path):
    import doc_read_guard
    src = tmp_path / "belgeler"
    write(src, "alt/ic" + MD)
    write(src, "BUYUK" + MD.upper())                                  # Windows reads it as a document too
    docs = {os.path.realpath(src / "alt" / ("ic" + MD)), os.path.realpath(src / ("BUYUK" + MD.upper()))}
    doc_read_guard.OPENED.difference_update(docs)
    try:
        os.symlink(src, tmp_path / "bag", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    assert docs <= doc_read_guard.OPENED


def test_the_guard_reads_a_relative_link_from_the_link_s_directory(tmp_path, monkeypatch):
    """os.symlink("../docs", link): the target is relative to the link's directory; read from the
    working directory it named nothing and a linked directory of documents went unseen (mutation
    check, 26 Sep 2026)."""
    import doc_read_guard
    write(tmp_path, "d/belgeler/ic" + MD)
    write(tmp_path, "d/tek" + MD)
    (tmp_path / "d" / "baglar").mkdir()
    docs = {os.path.realpath(tmp_path / "d" / "belgeler" / ("ic" + MD)), os.path.realpath(tmp_path / "d" / ("tek" + MD))}
    doc_read_guard.OPENED.difference_update(docs)
    monkeypatch.chdir(tmp_path)                                       # not the links' directory
    try:
        os.symlink("../belgeler", tmp_path / "d" / "baglar" / "dizin", target_is_directory=True)
        os.symlink("../tek" + MD, tmp_path / "d" / "baglar" / "dosya")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    assert docs <= doc_read_guard.OPENED


def test_the_guard_resolves_a_path_when_it_is_used(tmp_path, monkeypatch):
    """A relative path, or one through a link, means what it meant at the open: the working
    directory can change and the link can be gone by the end of the session."""
    import doc_read_guard
    write(tmp_path, "gercek/docs/x" + MD)
    write(tmp_path, "gercek/docs/alt/y" + MD)
    docs = {os.path.realpath(tmp_path / "gercek" / "docs" / ("x" + MD)),
            os.path.realpath(tmp_path / "gercek" / "docs" / "alt" / ("y" + MD))}
    doc_read_guard.OPENED.difference_update(docs)
    try:
        os.symlink(tmp_path / "gercek", tmp_path / "gecici", target_is_directory=True)
        monkeypatch.chdir(tmp_path / "gecici")
        with open("docs/x" + MD, encoding="utf-8"):                   # relative, through the link
            pass
        os.symlink(tmp_path / "gecici" / "docs" / "alt", tmp_path / "bag", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "gecici").unlink()
    assert docs <= doc_read_guard.OPENED


def test_the_guard_sees_a_windows_junction(tmp_path):
    """_winapi.CreateJunction links a directory without the privilege a symlink needs on Windows;
    its audit event is simulated here, as CPython raises it (Modules/_winapi.c)."""
    import doc_read_guard
    write(tmp_path, "belgeler/ic" + MD)
    doc = os.path.realpath(tmp_path / "belgeler" / ("ic" + MD))
    doc_read_guard.OPENED.discard(doc)
    sys.audit("_winapi.CreateJunction", str(tmp_path / "belgeler"), str(tmp_path / "bag"))
    assert doc in doc_read_guard.OPENED


def test_the_guard_takes_every_event_it_names(tmp_path):
    """Each audit event the guard lists records its source (shutil.copyfile opens the file too on
    today's Pythons, so only a direct call shows the event itself is handled)."""
    import doc_read_guard
    doc = tmp_path / ("olay" + MD)
    doc.write_text("x\n", encoding="utf-8")
    for event in ("open", "shutil.copyfile", "_winapi.CopyFile2", "os.link", "os.symlink", "_winapi.CreateJunction"):
        doc_read_guard.OPENED.discard(os.path.realpath(doc))
        doc_read_guard.record(event, (str(doc), str(tmp_path / "hedef"), 0))
        assert os.path.realpath(doc) in doc_read_guard.OPENED, event
    doc_read_guard.OPENED.discard(os.path.realpath(doc))
    doc_read_guard.record("os.rename", (str(doc), str(tmp_path / "hedef"), None, None))
    assert os.path.realpath(doc) not in doc_read_guard.OPENED


def test_windows_names_are_read_as_windows_reads_them():
    import doc_read_guard
    for name in ("x" + MD + ".", "x" + MD + " ", "x" + MD + "::$DATA", "x" + MD + ". . "):
        assert doc_read_guard._windows_name("C:\\r\\docs\\" + name) == "C:\\r\\docs\\x" + MD, name
    assert doc_read_guard._windows_name("C:\\r\\notes.txt") == "C:\\r\\notes.txt"
    assert doc_read_guard._windows_name("C:/r/docs/x" + MD + "::$DATA") == "C:/r/docs/x" + MD   # forward slashes
    assert doc_read_guard._windows_name("C:x" + MD + ".") == "C:x" + MD                           # drive-relative


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


# --------------------------------------------------------------------------- round 3 of the review


def test_head_must_be_what_its_branch_on_origin_holds(cloned):
    """The pull request merges the branch as origin holds it, read there: not a local tracking ref,
    which may be stale, missing or origin/master (review, 26 Sep 2026)."""
    write(cloned.work, "notlar.md", "changed\n")
    commit(cloned.work)
    p = check.plan(cloned.work)
    assert p["level"] == "tam" and p["why"] == "origin'de dal dalı yok (push edilmemiş)" and p["advice"] == check._ADVICE_PUSH
    git(cloned.work, "branch", "-q", "-u", "origin/master")          # an upstream that is the base proves nothing
    assert check.plan(cloned.work)["why"] == "origin'de dal dalı yok (push edilmemiş)"
    git(cloned.work, "push", "-q", "origin", "dal")
    assert check.plan(cloned.work)["level"] == "yok"
    assert "güncelliği bilinmiyor" in check.plan(cloned.work, fetch=False)["why"]
    assert check._push_problem(cloned.work, False) == ("origin'deki dal okunmadı (--no-fetch)", check._ADVICE_NO_FETCH)
    git(cloned.other, "fetch", "-q", "origin", "dal")                 # someone else pushes to the branch:
    git(cloned.other, "checkout", "-q", "-b", "dal", "FETCH_HEAD")    # the local tracking ref stays as it was
    write(cloned.other, "their.py")
    commit(cloned.other, "theirs")
    git(cloned.other, "push", "-q", "origin", "dal")
    p = check.plan(cloned.work)
    assert p["level"] == "tam" and "HEAD ile aynı değil" in p["why"] and p["advice"] == check._ADVICE_SYNC, p
    git(cloned.work, "checkout", "-q", "--detach")
    p = check.plan(cloned.work)
    assert p["level"] == "tam" and "bir dala bağlı değil" in p["why"] and p["advice"] == check._ADVICE_SWITCH


def test_nothing_changed_here_but_origin_s_branch_holds_code(cloned):
    """The checkout's branch sits at master; another session pushed code to origin's copy of it.
    The pull request merges origin's copy: nothing changed here is no proof (review, 26 Sep 2026)."""
    git(cloned.work, "push", "-q", "origin", "dal")                   # dal = master, on origin too
    assert check.plan(cloned.work)["level"] == "yok"
    git(cloned.other, "fetch", "-q", "origin", "dal")
    git(cloned.other, "checkout", "-q", "-b", "dal", "FETCH_HEAD")
    write(cloned.other, "their.py", "import os\n")
    commit(cloned.other, "theirs")
    git(cloned.other, "push", "-q", "origin", "dal")
    p = check.plan(cloned.work)
    assert p["level"] == "tam" and "HEAD ile aynı değil" in p["why"] and p["advice"] == check._ADVICE_SYNC, p
    git(cloned.work, "checkout", "-q", "-b", "yeni", "origin/master")  # a branch origin does not have: no PR yet
    assert check.plan(cloned.work)["level"] == "yok"
    git(cloned.work, "checkout", "-q", "--detach")
    p = check.plan(cloned.work)
    assert p["level"] == "tam" and "bir dala bağlı değil" in p["why"] and p["advice"] == check._ADVICE_SWITCH
    assert check.plan(cloned.work, fetch=False)["level"] == "tam"


def test_ls_remote_s_pattern_is_not_the_branch(cloned):
    """`git ls-remote origin refs/heads/dal` also lists a/refs/heads/dal (review)."""
    write(cloned.work, "notlar.md", "changed\n")
    commit(cloned.work)
    git(cloned.work, "push", "-q", "origin", "HEAD:refs/heads/a/refs/heads/dal")
    p = check.plan(cloned.work)
    assert p["level"] == "tam" and p["why"] == "origin'de dal dalı yok (push edilmemiş)", p
    git(cloned.work, "push", "-q", "origin", "HEAD~1:refs/heads/dal")
    assert "HEAD ile aynı değil" in check.plan(cloned.work)["why"]


def test_a_branch_pushed_under_another_name_is_read_there(cloned):
    write(cloned.work, "notlar.md", "changed\n")
    commit(cloned.work)
    git(cloned.work, "push", "-q", "-u", "origin", "dal:claude/ozellik")
    assert check.plan(cloned.work)["level"] == "yok"
    write(cloned.work, "notlar.md", "again\n")
    commit(cloned.work)
    assert "origin'deki claude/ozellik HEAD ile aynı değil" in check.plan(cloned.work)["why"]


def test_what_no_full_run_settles_is_said_before_asking_for_one(cloned):
    """A code branch without a valid log: when the base received code, or origin cannot vouch for
    master, a --full would be thrown away; say that first (review)."""
    write(cloned.work, "code.py", "x = 2\n")
    commit(cloned.work)
    git(cloned.work, "push", "-q", "origin", "dal")
    assert check.plan(cloned.work)["advice"] is None                 # the --full it needs
    write(cloned.other, "remote.py")
    commit(cloned.other, "merged elsewhere")
    git(cloned.other, "push", "-q", "origin", "master")
    p = check.plan(cloned.work)
    assert p["full"] is None and p["advice"] == check._ADVICE_MERGE and "birleştirilir" in p["why"], p
    git(cloned.work, "fetch", "-q", "origin")
    git(cloned.work, "merge", "-q", "--no-edit", "origin/master")
    git(cloned.work, "push", "-q", "origin", "dal")
    git(cloned.work, "remote", "set-url", "origin", str(cloned.origin.parent / "gone.git"))
    p = check.plan(cloned.work)
    assert p["full"] is None and p["advice"] == check._ADVICE_FETCH and "güncelliği bilinmiyor" in p["why"], p


def test_the_full_run_counts_only_for_what_was_pushed(cloned):
    write(cloned.work, "code.py", "x = 2\n")
    full_log(cloned.work, commit(cloned.work))
    commit(cloned.work, "log")
    p = check.plan(cloned.work)
    assert p["level"] == "tam" and p["why"] == "origin'de dal dalı yok (push edilmemiş)" and p["full"]["ok"], p
    git(cloned.work, "push", "-q", "origin", "dal")
    assert check.plan(cloned.work)["level"] == "tamam"


def test_on_local_master_no_push_is_asked(cloned):
    """Merging locally, HEAD is master: there is no pull request to compare with."""
    git(cloned.work, "checkout", "-q", "master")
    write(cloned.work, "notlar.md", "merged locally\n")
    commit(cloned.work)
    p = check.plan(cloned.work)
    assert p["level"] == "yok" and p["base"] == "origin/master", p


def criss_cross(repo: Path) -> None:
    """master and dal each merge the other's first commit: two merge bases."""
    git(repo, "checkout", "-q", "master")
    write(repo, "m.py")
    m1 = commit(repo, "m1")
    git(repo, "checkout", "-q", "dal")
    write(repo, "d.py")
    d1 = commit(repo, "d1")
    git(repo, "checkout", "-q", "master")
    git(repo, "merge", "-q", "--no-edit", "--no-ff", d1)
    git(repo, "checkout", "-q", "dal")
    git(repo, "merge", "-q", "--no-edit", "--no-ff", m1)


def test_a_criss_cross_history_decides_nothing(repo):
    """With two merge bases the branch's changes and the base's depend on which one is taken, and
    git diff HEAD...base takes its own (review)."""
    criss_cross(repo)
    assert len(git(repo, "merge-base", "--all", "master", "dal").split()) == 2
    p = check.plan(repo)
    assert p["level"] == "tam" and "çapraz" in p["why"] and p["advice"] == check._ADVICE_MERGE
    git(repo, "merge", "-q", "--no-edit", "master")
    assert "çapraz" not in check.plan(repo)["why"]


def test_local_master_in_a_criss_cross_decides_nothing(repo):
    git(repo, "update-ref", "refs/remotes/origin/master", git(repo, "rev-parse", "master"))
    criss_cross(repo)
    p = check.plan(repo)
    assert p["level"] == "tam" and "birden çok ortak atası" in p["why"] and p["advice"] == check._ADVICE_LOCAL_MASTER, p


def test_a_base_from_this_machine_or_another_remote_is_not_fresh(cloned, tmp_path, monkeypatch):
    """Only origin on a server can vouch for the real master: a clone of another checkout, a backup
    bundle as origin, or a remote under another name leaves the base's freshness unknown (review)."""
    write(cloned.work, "notlar.md", "changed\n")
    commit(cloned.work)
    git(cloned.work, "push", "-q", "origin", "dal")
    assert check.plan(cloned.work)["level"] == "yok"
    monkeypatch.setattr(check, "local_origin", REAL_LOCAL_ORIGIN)
    p = check.plan(cloned.work)                                        # the bare origin is a directory here
    assert p["fetch"] == "origin bu makinede bir yol: tazeliği bilinmiyor" and p["level"] == "tam", p
    assert p["advice"] == check._ADVICE_ORIGIN
    bundle = tmp_path / "yedek.bundle"
    git(cloned.work, "bundle", "create", str(bundle), "--all")
    no_suffix = str(cloned.origin)[:-len(".git")]                      # git adds .git itself (review)
    for url in (str(bundle), "file://" + bundle.as_posix(), "file://localhost" + bundle.as_posix(),
                os.path.relpath(bundle, cloned.work), no_suffix):
        git(cloned.work, "remote", "set-url", "origin", url)
        p = check.plan(cloned.work)
        assert p["fetch"] == "origin bu makinede bir yol: tazeliği bilinmiyor" and p["level"] == "tam", (url, p)
    for url, local in [("https://github.com/wqedwad/asd", False), ("git@github.com:wqedwad/asd.git", False),
                       ("ssh://git@github.com/wqedwad/asd", False), ("http://proxy@127.0.0.1:9/git/wqedwad/asd", False),
                       ("C:\\Users\\x\\yedek.bundle", True), ("C:/Users/x/yedek", True),
                       ("file:///C:/Users/x/yedek.bundle", True), ("../yedek", True), ("yedek.git", True),
                       ("./a:b", True)]:
        assert check.local_origin(url) is local, url
    git(cloned.work, "remote", "rename", "origin", "yukari")
    p = check.plan(cloned.work)
    assert p["fetch"] == "origin yok (başka uzak var)" and p["level"] == "tam", p


def test_the_base_keeps_its_rule_files(repo):
    """A branch cannot take a file off the rule's list: the base's list counts too (review)."""
    git(repo, "checkout", "-q", "master")
    write(repo, "scripts/check.py", 'RULE_FILES = ("kural.py", "scripts/check.py")\n')
    write(repo, "kural.py", "K = 1\n")
    commit(repo, "the base's rule")
    git(repo, "checkout", "-q", "dal")
    git(repo, "merge", "-q", "--no-edit", "master")
    assert check.base_rule_files(repo, "master") == ("kural.py", "scripts/check.py")
    write(repo, "kural.py", "K = 2\n")
    full_log(repo, commit(repo))
    commit(repo, "log")
    p = check.plan(repo)
    assert p["level"] == "tam" and "(kural.py)" in p["why"] and p["advice"] == check._ADVICE_RULES, p
    assert check.base_rule_files(repo, "yok-boyle-dal") == ()
    git(repo, "checkout", "-q", "master")
    write(repo, "scripts/check.py", 'RULE_FILES: tuple = ("kural.py",)\n')    # annotated
    commit(repo, "annotated")
    assert check.base_rule_files(repo, "master") == ("kural.py",)
    write(repo, "scripts/check.py", 'RULE_FILES = ("a.py",)\nRULE_FILES = ("b.py",)\n')
    commit(repo, "reassigned")
    assert check.base_rule_files(repo, "master") == ("a.py", "b.py")
    for text in ('CORE = ("scripts/check.py",)\nRULE_FILES = CORE + ("kural.py",)\n',
                 'A, RULE_FILES = 1, ("kural.py",)\n', 'RULE_FILES = ("x.py",)\nRULE_FILES += ("kural.py",)\n',
                 "def (:\n"):
        write(repo, "scripts/check.py", text)
        commit(repo, "unreadable")
        assert check.base_rule_files(repo, "master") is None, text
    write(repo, "scripts/check.py", "X = 1\n")                       # a base older than the list
    commit(repo, "no list")
    assert check.base_rule_files(repo, "master") == ()
    write(repo, "scripts/check.py", 'CORE = ("scripts/check.py",)\nRULE_FILES = CORE + ("kural.py",)\n')
    commit(repo, "unreadable again")
    git(repo, "checkout", "-q", "dal")
    git(repo, "merge", "-q", "--no-edit", "master")
    write(repo, "code.py", "x = 9\n")
    full_log(repo, commit(repo))
    commit(repo, "log")
    p = check.plan(repo)
    assert p["level"] == "tam" and "kural listesi (RULE_FILES) okunamadı" in p["why"] and p["advice"] == check._ADVICE_RULES


def test_the_environment_of_the_run_must_be_the_locked_one(repo):
    """A verdict can change with SymPy's or latex2sympy2's version: the log's kilit line must show
    every pin of requirements.lock met, for the lock as it is now (review)."""
    write(repo, "code.py", "x = 2\n")
    sha = commit(repo)
    full_log(repo, sha)
    assert check.last_full_run(repo)["ok"]
    digest = check.lock_digest(repo)
    for lock, why in [((f"kilit: requirements.lock {digest} · 1 paket · uyuşmayan: sympy 1.13.3 ≠ 1.14.0",),
                       "ortam kilitle uyuşmuyor (sympy 1.13.3 ≠ 1.14.0)"),
                      (("kilit: requirements.lock 0123456789abcdef · 1 paket · uyuşmayan: yok",), "kilit koşudan sonra değişti"),
                      (("kilit: yok",), "kilit denetlenemedi (yok)"),
                      ((), "kilit satırı yok ya da birden çok"),
                      ((f"kilit: requirements.lock {digest} · 1 paket · uyuşmayan: yok",) * 2, "kilit satırı yok ya da birden çok")]:
        full_log(repo, sha, lock=lock)
        full = check.last_full_run(repo)
        assert why in full["why"], (lock, full)
        assert full.get("advice") == (check._ADVICE_LOCK if "uyuşmuyor" in why or "denetlenemedi" in why else None)
    for env in [(), ("ortam: Python 3", "ortam: Python 3")]:
        full_log(repo, sha, env=env)
        assert check.last_full_run(repo)["why"] == "ortam satırı yok ya da birden çok"
    (repo / "requirements.lock").unlink()
    full_log(repo, sha, lock=(f"kilit: requirements.lock {digest} · 1 paket · uyuşmayan: yok",))
    assert "kilit koşudan sonra değişti" in check.last_full_run(repo)["why"]


def test_the_kilit_line_is_every_pin_for_this_platform(tmp_path):
    """The gates' interpreter (PY) is asked, not check.py's own; markers are evaluated there."""
    write(tmp_path, "requirements.lock", "sympy==1.14.0\n    # via x\nsympy-yok-boyle==1.0\nmpmath==0.0.1\n"
                                          "colorama==0.4.6 ; sys_platform == 'kimsenin-platformu'\n")
    env, lock = check.environment_lines(tmp_path)
    assert env.startswith("ortam: Python ") and "sympy 1.14.0" in env
    assert lock == (f"kilit: requirements.lock {check.lock_digest(tmp_path)} · 3 paket · uyuşmayan: "
                    f"sympy-yok-boyle yok ≠ 1.0, mpmath 1.3.0 ≠ 0.0.1")
    lf = check.lock_digest(tmp_path)
    (tmp_path / "requirements.lock").write_bytes(b"sympy==1.14.0\r\n    # via x\r\nsympy-yok-boyle==1.0\r\nmpmath==0.0.1\r\n"
                                                 b"colorama==0.4.6 ; sys_platform == 'kimsenin-platformu'\r\n")
    assert check.lock_digest(tmp_path) == lf                           # a Windows checkout's CRLF
    (tmp_path / "requirements.lock").write_bytes("sympy==1.14.0\n".encode("utf-16"))   # PowerShell 5's redirection
    assert check.environment_lines(tmp_path)[1] == "kilit: requirements.lock okunamadı (UTF-8 değil)"
    (tmp_path / "requirements.lock").unlink()
    assert check.environment_lines(tmp_path)[1] == "kilit: yok"


def test_a_utf16_lock_decides_without_raising(repo):
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo))
    commit(repo, "log")
    (repo / "requirements.lock").write_bytes("sympy==1.14.0\n".encode("utf-16"))
    p = check.plan(repo)                                              # the lock changed: TAM, with a reason
    assert p["level"] == "tam" and "kilit koşudan sonra değişti" in p["why"], p


def test_colour_codes_hide_no_skipped_line(repo):
    """FORCE_COLOR or PY_COLORS=1 coloured pytest's summary: the Lean skip vanished from the log
    and the plan accepted a run whose Lean tests did not run (review)."""
    line = "\x1b[33mSKIPPED\x1b[0m [87] tests/test_f5_lean.py:19: Lean/Mathlib toolchain not available"
    assert check.pytest_problems("x\n" + line + "\n") == [check._ANSI.sub("", line)]
    write(repo, "code.py", "x = 2\n")
    full_log(repo, commit(repo), extra=["    " + line])
    assert check.last_full_run(repo)["why"] == "Lean testleri atlanmış (toolchain yok)"


def test_colour_settings_do_not_reach_the_pytest_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("PY_COLORS", "1")
    monkeypatch.setenv("FORCE_COLOR", "1")
    spec = importlib.util.spec_from_file_location("check_script_colour", ROOT / "scripts" / "check.py")
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    write(tmp_path, "test_lean_like.py", "import pytest\n\ndef test_a():\n    pytest.skip('Lean/Mathlib toolchain not available')\n")
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rfEs", "-p", "no:cacheprovider", "test_lean_like.py"],
                       cwd=tmp_path, env=fresh.ENV, capture_output=True, text=True, encoding="utf-8")
    assert "\x1b[" not in p.stdout, p.stdout
    assert any(check._LEAN_SKIPPED in x for x in fresh.pytest_problems(p.stdout)), p.stdout


@pytest.mark.skipif(not hasattr(__import__("ast"), "TemplateStr"), reason="t-strings: Python 3.14+")
def test_template_strings_are_names_completed_at_run_time(tmp_path, git_env):
    write(tmp_path, "a.py", 'stem = "x"\nNAME = t"{stem}' + MD + '"\n')
    assert ("a.py:2", MD, True) in check.code_strings(tmp_path)
    assert check.docs_named_by_code(tmp_path, ["docs/rehber" + MD]) == {"docs/rehber" + MD: "a.py:2"}


def _link(repo: Path, path: str, target: str) -> None:
    """A tracked symbolic link made on git's side (the index entry), whatever the file system."""
    blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=repo, input=target.encode(),
                          capture_output=True, check=True).stdout.decode().strip()
    git(repo, "update-index", "--add", "--cacheinfo", f"120000,{blob},{path}")


def test_a_link_is_read_from_git_not_from_the_disk(repo):
    """On Windows (core.symlinks=false) a tracked link is checked out as a plain file holding its
    target; an absolute target may be any document (review)."""
    git(repo, "config", "core.symlinks", "false")
    doc = "docs/veri" + MD
    write(repo, doc, "data\n")
    _link(repo, "evalset/x.json", "../" + doc)
    git(repo, "add", doc)
    git(repo, "commit", "-q", "-m", "a link")                        # not add -A: the link is not on disk yet
    git(repo, "checkout", "--", "evalset/x.json")
    assert (repo / "evalset" / "x.json").is_file() and not (repo / "evalset" / "x.json").is_symlink()
    assert check.linked_docs(repo, [doc, "notlar" + MD]) == {doc: "bağlantı: evalset/x.json"}
    _link(repo, "evalset/y.json", "/mutlak/yol")
    assert check.linked_docs(repo, [doc, "notlar" + MD]) == {doc: "bağlantı: evalset/x.json",
                                                            "notlar" + MD: "bağlantı: evalset/y.json"}


def test_reports_are_hashed_as_git_stores_them(repo):
    """A Windows checkout (core.autocrlf, text=auto) has CRLF on disk: a --full from the cloud must
    still bind its reports there (review)."""
    write(repo, "code.py", "x = 2\n")
    (repo / "reports" / "eval_report.md").write_bytes(b"a\nb\n")
    full_log(repo, commit(repo))
    commit(repo, "log")
    assert b"\r" not in subprocess.run(["git", "cat-file", "-p", "HEAD:reports/eval_report.md"], cwd=repo,
                                       capture_output=True, check=True).stdout
    lf = check.report_digests(repo)
    git(repo, "config", "core.autocrlf", "true")
    for f in ("reports/eval_report.md", "reports/check_full.log"):
        (repo / f).unlink()
    git(repo, "checkout", "--", "reports/")
    assert b"\r\n" in (repo / "reports" / "eval_report.md").read_bytes()
    assert check.report_digests(repo) == lf and check.plan(repo)["level"] == "tamam"
    (repo / "reports" / ("alt" + MD)).mkdir()                        # not a file: no crash, and no match
    assert check.report_digests(repo)["reports/alt" + MD] == "okunamadı"
    try:
        os.symlink(repo / "reports" / "eval_report.md", repo / "reports" / ("bag" + MD))
    except (OSError, NotImplementedError):
        return
    assert check.report_digests(repo)["reports/bag" + MD] == "okunamadı"     # a link is not a report


def test_remotes_git_cannot_list_are_not_no_remotes(repo, monkeypatch):
    """A failing `git remote` is not a repository without remotes: that would make the base fresh
    and skip the push check."""
    real = check._git_lines
    monkeypatch.setattr(check, "_git_lines", lambda root, *a: None if a == ("remote",) else real(root, *a))
    assert check.fetch_origin(repo) == "başarısız (uzaklar okunamadı)"
    assert check._push_problem(repo, True) == ("uzaklar okunamadı", None)
    write(repo, "notlar.md", "changed\n")
    assert check.plan(repo)["level"] == "tam"


def test_without_remotes_no_fetch_changes_nothing(repo):
    write(repo, "notlar.md", "changed\n")
    p = check.plan(repo, fetch=False)
    assert p["fetch"] == "uzak yok" and p["level"] == "yok"


def test_the_full_run_warns_at_once_when_it_will_prove_nothing(repo, monkeypatch, capsys):
    """An environment off the lock, or a tree git cannot read, is said at the start, not 25 minutes
    later by --plan (review)."""
    monkeypatch.setattr(check, "ROOT", repo)
    monkeypatch.setattr(check, "_main", lambda args: print("1/1 kapı geçti") or 0)
    monkeypatch.setattr(check, "environment_lines", lambda root: ("ortam: Python 3", "kilit: yok"))
    assert check.main(["--full"]) == 0
    log = (repo / "reports" / "check_full.log").read_text(encoding="utf-8")
    assert "UYARI: ortam requirements.lock'la uyuşmuyor ya da denetlenemedi" in log
    monkeypatch.setattr(check, "dirty_files", lambda root: None)
    assert check.main(["--full"]) == 0
    lines = (repo / "reports" / "check_full.log").read_text(encoding="utf-8").splitlines()
    assert lines[0].endswith("commit edilmemiş değişiklik: ? dosya")
    assert "UYARI: git değişiklikleri veremedi, bu koşu --plan için kanıt olmaz" in lines


def test_a_failing_rev_list_is_not_an_empty_one(repo, monkeypatch):
    """Local master's unpushed commits are read with rev-list; a failure there must not read as
    "none" (review)."""
    git(repo, "update-ref", "refs/remotes/origin/master", git(repo, "rev-parse", "master"))
    git(repo, "checkout", "-q", "master")
    write(repo, "src_yerel.py")
    commit(repo, "merged locally, not pushed")
    git(repo, "checkout", "-q", "dal")
    write(repo, "notlar.md", "changed\n")
    real = check._git_run
    monkeypatch.setattr(check, "_git_run", lambda root, *a, **k: types.SimpleNamespace(returncode=128, stdout=b"")
                        if a[:1] == ("rev-list",) else real(root, *a, **k))
    p = check.plan(repo)
    assert p["level"] == "tam" and "yerel master" in p["why"], p


def test_a_shallow_clone_without_the_merge_base_says_so(cloned, tmp_path):
    write(cloned.other, "code.py", "x = 2\n")
    commit(cloned.other, "master moves on")
    git(cloned.other, "push", "-q", "origin", "master")
    git(cloned.other, "push", "-q", "origin", "HEAD~1:refs/heads/yan")   # a branch from the older master
    shallow = tmp_path / "shallow"
    git(tmp_path, "clone", "-q", "--depth", "1", "file://" + cloned.origin.as_posix(), str(shallow))
    git(shallow, "fetch", "-q", "--depth", "1", "origin", "yan:yan")
    git(shallow, "checkout", "-q", "yan")
    p = check.plan(shallow)
    assert p["level"] == "tam" and "ortak atası yok" in p["why"] and p["advice"] == check._ADVICE_SHALLOW, p


def test_a_tag_with_the_branch_s_name_changes_nothing(cloned):
    """`symbolic-ref --short` says "heads/dal" when a tag dal exists too (review)."""
    write(cloned.work, "notlar.md", "changed\n")
    commit(cloned.work)
    git(cloned.work, "push", "-q", "origin", "dal")
    git(cloned.work, "tag", "dal")
    assert check._head_branch(cloned.work) == "dal" and check.plan(cloned.work)["level"] == "yok"


def test_link_targets_are_read_the_same_on_every_os(repo):
    """A link blob is git's text: "..\\x" and "C:x" mean the same in the cloud and on Windows (review)."""
    doc = "docs/veri" + MD
    write(repo, doc, "data\n")
    for target, hit in [("../" + doc, True), ("..\\" + doc.replace("/", "\\"), True), ("C:veri" + MD, True),
                        ("D:\\yedek\\x" + MD, True), ("../docs/baska" + MD, False)]:
        _link(repo, "evalset/x.json", target)
        assert (doc in check.linked_docs(repo, [doc])) is hit, target

"""Mutation check of the staged-check rule, the runtime guard and the split adversarial sweep
(DECISIONS §59). Each mutation breaks one behaviour the tests are meant to hold; the test file that
covers it then runs on the mutated code and must fail ("öldü"). A mutation that survives is a
behaviour no test holds.

    .venv/bin/python denetim/2026-09-26/mutasyon.py [-j N] [--list] [name ...]

The mutations run in throwaway clones of the committed HEAD (uncommitted changes are not
measured; the clone has no remote and is deleted at the end), one clone per job. First the clone's
own tests must pass. The exit code is 0 only when every mutation was applied and killed.

Kept out of pyflakes and pytest like the rest of denetim/. No string here may name a document:
check.py reads every string constant of the repository's Python code.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHECK, GUARD, ADV = "scripts/check.py", "tests/doc_read_guard.py", "harness/adversarial.py"
TS, TA, TH = "tests/test_staged_check.py", "tests/test_adversarial_parallel.py", "tests/test_check_gates_harness.py"

# (name, file, old text, new text, test file[, occurrences]): the old text must occur exactly that
# often (default once), or the mutation is reported as not applied.
MUTATIONS = [
    # --- classification
    ("C01 rapor büyük/küçük harfe duyarlı", CHECK, '    p = _norm(path).lower()\n    head, _, name = p.rpartition("/")',
     '    p = _norm(path)\n    head, _, name = p.rpartition("/")', TS),
    ("C02 belge her dizinde", CHECK, ' and not is_report(p) and ("/" not in p or p.startswith(DOC_DIRS))',
     " and not is_report(p)", TS),
    ("C03 docstring da ad sayılır", CHECK, "            if isinstance(n, ast.Expr):\n                prose.add(id(n.value))",
     "            if isinstance(n, ast.Expr):\n                pass", TS),
    ("C04 bytes sabitleri yok sayılır", CHECK, "and isinstance(n.value, (str, bytes)) and id(n) not in prose",
     "and isinstance(n.value, str) and id(n) not in prose", TS),
    ("C05 f-string kuyruğu yok", CHECK, "            elif isinstance(n, templates):\n", "            elif False:\n", TS),
    ("C06 t-string kuyruğu yok", CHECK,
     '    templates = (ast.JoinedStr, *([ast.TemplateStr] if hasattr(ast, "TemplateStr") else []))',
     "    templates = (ast.JoinedStr,)", TS),
    ("C07 + kuyruğu yok", CHECK,
     "            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):\n                tails.add(id(n.right))",
     "            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):\n                pass", TS),
    ("C08 yer tutucudan sonra tam ad", CHECK, "        suffix = tail if i == 0 else before not in _NAME_START",
     "        suffix = tail", TS),
    ("C09 ad eşleşmesi harfe duyarlı", CHECK, "    t, d = _norm(token).lower(), _norm(doc).lower()",
     "    t, d = _norm(token), _norm(doc)", TS),
    ("C10 çıplak uzantı her belgeyi adlandırır", CHECK, "    if tbase == DOC_SUFFIX:\n        return False",
     "    if tbase == DOC_SUFFIX:\n        return True", TS),
    ("C11 ad sonu eşleşmesi yok", CHECK,
     "    return base == tbase or (base.endswith(tbase) and not _WORD.match(base[-len(tbase) - 1]))",
     "    return base == tbase", TS),
    ("C12 mutlak bağlantı hiçbir belge", CHECK, "            hits = docs                            # unreadable",
     "            hits = []                            # unreadable", TS),
    ("C13 bağlantı diskten okunur", CHECK, '        link = _git_value(root, "cat-file", "blob", meta.split()[1])',
     "        link = os.readlink(root / path) if os.path.islink(root / path) else None", TS),
    ("C14 bağlantılar sayılmaz", CHECK,
     "    found.update({d: why for d, why in linked_docs(root, docs).items() if d not in found})", "    pass", TS),
    ("C15 adsız okuyucu dizin anahtarı yok", CHECK, '        if d == key or (key.endswith("/") and d.startswith(key)):',
     "        if d == key:", TS),
    ("C16 izlenmeyen Python taranmaz", CHECK, '"ls-files", "-z", "--cached", "--others", "--exclude-standard"',
     '"ls-files", "-z", "--cached", "--exclude-standard"', TS),
    # --- what changed
    ("C17 HEAD'in ağacı sayılmaz", CHECK, '_git_lines(root, *diff, rev, "HEAD", "--"),', "[],", TS),
    ("C18 indeks sayılmaz", CHECK, '_git_lines(root, *diff, "--cached", rev, "--")', "[]", TS),
    ("C19 izlenmeyen dosya sayılmaz", CHECK,
     '_git_lines(root, "ls-files", "--others", "--exclude-per-directory=.gitignore", "-z")]', "[]]", TS),
    ("C20 alt modül ayarı gizler", CHECK,
     '    None if git fails."""\n    diff = ("diff", "--name-only", "-z", "--no-renames", "--ignore-submodules=none")',
     '    None if git fails."""\n    diff = ("diff", "--name-only", "-z", "--no-renames")', TS),
    ("C21 yeniden adlandırmanın eski adı yok", CHECK,
     '    None if git fails."""\n    diff = ("diff", "--name-only", "-z", "--no-renames", "--ignore-submodules=none")',
     '    None if git fails."""\n    diff = ("diff", "--name-only", "-z", "--ignore-submodules=none")', TS),
    ("C22 gizlenen dosya yok", CHECK,
     '    out = {r[2:] for r in rows if len(r) > 2 and (r[0].islower() or r[0] == "S")}', "    out = set()", TS),
    ("C23 kirli sayımı bütün raporları dışlar", CHECK, "if _norm(f) not in REWRITTEN})", "if not is_report(f)})", TS),
    ("C24 rapor özeti CRLF'e duyarlı", CHECK, 'out[rel] = hashlib.sha256(p.read_bytes().replace(b"\\r\\n", b"\\n"))',
     "out[rel] = hashlib.sha256(p.read_bytes())", TS),
    ("C86 kilit özeti CRLF'e duyarlı", CHECK, 'hashlib.sha256((root / LOCK_FILE).read_bytes().replace(b"\\r\\n", b"\\n"))',
     "hashlib.sha256((root / LOCK_FILE).read_bytes())", TS),
    ("C25 rapor özeti harfe duyarlı", CHECK, "        if not is_report(rel) or _norm(rel).lower() == REPORT_LOG:",
     "        if not rel.endswith(DOC_SUFFIX):", TS),
    ("C26 dosya olmayan rapor", CHECK, '        if p.is_symlink() or not p.is_file():\n            out[rel] = "okunamadı"\n            continue\n',
     "", TS),
    ("C27 başta kirli ağaç kabul", CHECK, '    if int(head["dirty"]):', "    if False:", TS),
    ("C28 başta ? kirli sayısı", CHECK, '    if head["dirty"] == "?":', "    if False:", TS),
    ("C29 ortam satırı sayılmaz", CHECK, "    if sum(1 for l in lines if _LOG_ENV.fullmatch(l)) != 1:",
     "    if sum(1 for l in lines if _LOG_ENV.fullmatch(l)) < 1:", TS),
    ("C30 kilit denetlenmez", CHECK, '    if lock["bad"] != "yok":', "    if False:", TS),
    ("C31 kilit satırı sayılmaz", CHECK, "    if len(locks) != 1:", "    if not locks:", TS),
    ("C87 kilit özeti denetlenmez", CHECK, '    if lock["file"] != LOCK_FILE or lock["digest"] != lock_digest(root):',
     "    if False:", TS),
    ("C89 kilitte platform işaretleri yok sayılır", CHECK, "            if not Marker(marker).evaluate():", "            if False:", TS),
    ("C91 kilit uyarısı yok", CHECK, '            if not lock.endswith("uyuşmayan: yok"):', "            if False:", TS),
    ("C32 işaret sayısı denetlenmez", CHECK, ' or marks.count("[OK  ]") != n', "", TS),
    ("C33 iki özet satırı kabul", CHECK, " or len(totals) > 1", "", TS),
    ("C34 ısınma denetlenmez", CHECK, '    if len(warmups) != 1 or int(warmups[0]["rc"]):', "    if False:", TS),
    ("C35 atlanan Lean testleri kabul", CHECK, '    if any(l.startswith("SKIPPED") and _LEAN_SKIPPED in l for l in lines):',
     "    if False:", TS),
    ("C36 günlükte renk kodu kalır", CHECK, '    lines = [_ANSI.sub("", l).strip() for l in text.splitlines()]',
     "    lines = [l.strip() for l in text.splitlines()]", TS),
    ("C37 pytest çıktısında renk kodu kalır", CHECK, '    lines = (_ANSI.sub("", l) for l in out.splitlines())',
     "    lines = out.splitlines()", TS),
    ("C38 sonda commit denetlenmez", CHECK, '    if ends[-1]["commit"] != head["commit"] or ends[-1]["dirty"] != "0":',
     '    if ends[-1]["dirty"] != "0":', TS),
    ("C39 sonda kirli ağaç kabul", CHECK, '    if ends[-1]["commit"] != head["commit"] or ends[-1]["dirty"] != "0":',
     '    if ends[-1]["commit"] != head["commit"]:', TS),
    ("C40 raporlar karşılaştırılmaz", CHECK, " or dict(pairs) != now:", ":", TS),
    ("C41 renk ayarı geçer", CHECK, 'ENV["PY_COLORS"] = "0"\n', "\n", TS),
    ("C42 FORCE_COLOR geçer", CHECK, '"FORCE_COLOR", "PYTHONOPTIMIZE"', '"PYTHONOPTIMIZE"', TS),
    ("C92 PYTHONOPTIMIZE geçer", CHECK, '"PYTHONOPTIMIZE", "PYTHONHASHSEED"):', '"PYTHONHASHSEED"):', TS),
    ("C93 PYTHONHASHSEED geçer", CHECK, ', "PYTHONHASHSEED"):', "):", TS),
    ("C43 eklenti kapatma geçer", CHECK, '"PYTEST_PLUGINS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "MATHVERIFY_SANDBOX",',
     '"PYTEST_PLUGINS", "MATHVERIFY_SANDBOX",', TS),
    # --- the base
    ("C44 yerel origin taze", CHECK, "    if local_origin(url):\n", "    if False:\n", TS),
    ("C45 başka uzak = uzak yok", CHECK,
     '        return "origin yok (başka uzak var)" if remotes else "uzak yok"', '        return "uzak yok"', TS),
    ("C79 file: yerel sayılmaz", CHECK, '    if url.startswith("file:"):\n        return True', "    if False:\n        return True", TS),
    ("C80 scp kuralı yok", CHECK, "    return colon < 0 or 0 <= slash < colon or (colon == 1 and url[0].isalpha())",
     "    return colon < 0", TS),
    ("C94 sürücü harfi yerel değil", CHECK, "    return colon < 0 or 0 <= slash < colon or (colon == 1 and url[0].isalpha())",
     "    return colon < 0 or 0 <= slash < colon", TS),
    ("C81 okunamayan uzaklar = uzak yok", CHECK, '    if remotes is None:\n        return "başarısız (uzaklar okunamadı)"\n',
     "", TS),
    ("C82 push: okunamayan uzaklar = uzak yok", CHECK, '    if remotes is None:\n        return "uzaklar okunamadı", None\n', "", TS),
    ("C83 uzaksız depoda --no-fetch TAM", CHECK, 'fetch_origin(root) if fetch or _git_lines(root, "remote") == [] else',
     "fetch_origin(root) if fetch else", TS),
    ("C84 okunamayan kural listesi boş sayılır", CHECK, "                return None\n            found |= set(value)",
     "                continue\n            found |= set(value)", TS),
    ("C95 kural listesi okunamayınca TAM yok", CHECK, "    if base_rules is None:\n", "    if False:\n", TS),
    ("C96 check.py'siz taban okunamaz sayılır", CHECK, "    if text is None:\n        return ()", "    if text is None:\n        return None", TS),
    ("C46 hedefsiz fetch", CHECK, '"origin", "+refs/heads/master:refs/remotes/origin/master", timeout=60',
     '"origin", "master", timeout=60', TS),
    ("C47 çapraz birleşme kabul", CHECK, "        if len(mbs) > 1:\n", "        if False:\n", TS),
    ("C48 taban dalın kendisi", CHECK, "        if _head_branch(root) == b:\n", "        if False:\n", TS),
    ("C49 tazelik uçla karşılaştırılmaz", CHECK,
     'fresh = out["fetch"] == "uzak yok" or (out["fetch"] == "tamam" and out["base_tip"] == origin_tip)',
     'fresh = out["fetch"] in ("uzak yok", "tamam")', TS),
    ("C50 yerel master yok sayılır", CHECK,
     '    if out["base"] != "master" and _git_value(root, "rev-parse", "--verify", "--quiet", "master^{commit}"):', "    if False:", TS),
    ("C97 rev-list hatası yok sayılır", CHECK, "        if unpushed is None or unpushed.returncode:", "        if unpushed is None:", TS),
    ("C51 yerel master çapraz birleşmesi", CHECK, "            if len(mbs) != 1:\n", "            if False:\n", TS),
    ("C113 yerel master kodu tabanınki sayılır", CHECK, "    if remote:\n        received =", "    if True:\n        received =", TS),
    ("C52 ayrık HEAD kabul", CHECK, '        return "HEAD bir dala bağlı değil: birleştirilecek hâl bilinmiyor"',
     "        return None", TS),
    ("C53 master'da da push aranır", CHECK, '    if branch == "master" or not remotes:', "    if not remotes:", TS),
    ("C54 --no-fetch push'u geçer", CHECK, '        return f"origin\'deki {target} okunmadı (--no-fetch)", _ADVICE_NO_FETCH',
     "        return None", TS),
    ("C55 uzakta olmayan dal kabul", CHECK,
     '        return None if absent_ok else (f"origin\'de {target} dalı yok (push edilmemiş)", _ADVICE_PUSH)', "        return None", TS),
    ("C56 uzaktaki uç karşılaştırılmaz", CHECK, '    if shas[0] != _git_value(root, "rev-parse", "HEAD"):', "    if False:", TS),
    ("C98 ls-remote deseni dal sayılır", CHECK, "            if name == ref]", "            if name.endswith(ref)]", TS),
    ("C99 upstream adı okunmaz", CHECK, '            and merge != "refs/heads/master":', "            and False:", TS),
    ("C100 master upstream'i hedef sayılır", CHECK, '            and merge != "refs/heads/master":', "            and True:", TS),
    ("C101 değişiklik yokken push aranmaz", CHECK, "        pushed = _push_problem(root, fetch, absent_ok=True)\n",
     "        pushed = None\n", TS),
    ("C118 eski taban: değişen dosyalar boş", CHECK, 'return {**out, "level": "tam", "why": f"tabanın güncelliği',
     'return {**out, "files": {}, "level": "tam", "why": f"tabanın güncelliği', TS),
    ("C119 okunmamış dosyalar 0 dosya", CHECK, '"files": None, "named": {}', '"files": {}, "named": {}', TS),
    ("C120 okunmamış dosyalar gösterilmez", CHECK, "    if files is None:  ", "    if False:  ", TS),
    ("C121 sınıflanmamış dosyalar sayılmaz", CHECK, 'if counts["?"] else ""     # not zero of each kind',
     'if False else ""     # not zero of each kind', TS),
    ("C102 değişiklik yokken olmayan dal da TAM", CHECK, ", absent_ok=True)", ")", TS),
    ("C57 belge: taban kodu yok sayılır", CHECK, '            if out["base_ahead"]:                  # that code',
     "            if False:                  # that code", TS),
    ("C58 belge: tazelik yok sayılır", CHECK, "            if not fresh:\n", "            if False:\n", TS),
    ("C59 rapor bağlanmaz", CHECK, '        if "rapor" in kinds:\n', "        if False:\n", TS),
    ("C60 rapor başka kodda", CHECK, '            if full["code_since"] != []:', "            if False:", TS),
    ("C61 rapor commit edilmemiş", CHECK, "            if _reports_uncommitted(root) != []:\n", "            if False:\n", TS),
    ("C62 kod yok: push aranmaz", CHECK, "        pushed = _push_problem(root, fetch)\n", "        pushed = None\n", TS),
    ("C63 tamam: sonradan değişen kod", CHECK, '    if full["code_since"]:\n', "    if False:\n", TS),
    ("C64 tamam: kanıt commit edilmemiş", CHECK, "\n    if _reports_uncommitted(root) != []:\n", "\n    if False:\n", TS),
    ("C65 tamam: taban kodu", CHECK, '\n    if out["base_ahead"]:\n', "\n    if False:\n", TS),
    ("C66 tamam: tazelik", CHECK, "\n    if not fresh:\n", "\n    if False:\n", TS),
    ("C67 tamam: push", CHECK, "\n    pushed = _push_problem(root, fetch)\n", "\n    pushed = None\n", TS),
    ("C68 kural dosyaları onaylanır", CHECK, "    if rules:\n", "    if False:\n", TS),
    ("C69 tabanın kural listesi yok", CHECK, "set(RULE_FILES) | set(base_rules)", "set(RULE_FILES)", TS),
    ("C70 tabanın kural listesi okunmaz", CHECK, "                value = ast.literal_eval(node.value) if simple else None",
     "                value = ()", TS),
    ("C71 kural listesinde test dosyası yok", CHECK, '"tests/conftest.py", "tests/test_staged_check.py")',
     '"tests/conftest.py")', TS),
    ("C72 değişen raporlar adlandırılmaz", CHECK, '"changed_reports": changed}', '"changed_reports": []}', TS),
    ("C111 commit edilmemiş koşuda geri alma önerilir", CHECK, "    if uncommitted is None or REPORT_LOG in uncommitted:",
     "    if False:", TS),
    ("C103 koşunun önerisi iletilmez", CHECK, '"advice": _full_advice(root, full)}', '"advice": None}', TS, 2),
    ("C115 dal adı kısa addan okunur", CHECK, "    branch = _head_branch(root)\n",
     '    branch = _git_value(root, "symbolic-ref", "--quiet", "--short", "HEAD")\n', TS),
    ("C116 sürücülü bağlantı hedefi göreli", CHECK,
     '        if link is None or link.startswith("/") or ntpath.splitdrive(link)[0]:',
     '        if link is None or link.startswith("/"):', TS),
    ("C117 bağlantı hedefi düzeltilmez", CHECK, "        link = None if link is None else _norm(link)\n", "", TS),
    ("C106 yerel origin için fetch önerilir", CHECK, "    return _ADVICE_ORIGIN", "    return _ADVICE_FETCH", TS),
    ("C107 süzgeç görülmez", CHECK,
     '        out |= {parts[i] for i in range(0, len(parts) - 2, 3) if parts[i + 2] not in ("unspecified", "unset")}',
     "        pass", TS),
    ("C108 kendini gizleyen .gitignore görülmez", CHECK,
     "        out |= {fields[i + 3] for i in range(0, len(fields) - 3, 4) if fields[i] not in known}", "        pass", TS),
    ("C109 izlenen kural da gizleme sayılır", CHECK, "if fields[i] not in known}", "if True}", TS),
    ("C110 sığ klonda öneri yok", CHECK, "_ADVICE_SHALLOW if shallow else _ADVICE_BASE", "_ADVICE_BASE", TS),
    ("C73 karar verilemeyen: çıkış 0", CHECK, '        return 1, ["== kademeli kontrol (DECISIONS §59) ==",',
     '        return 0, ["== kademeli kontrol (DECISIONS §59) ==",', TS),
    # --- the --full's own lines
    ("C74 kirli ağaç uyarısı yok", CHECK, "            elif dirty:\n", "            elif False:\n", TS),
    ("C104 okunamayan ağaç uyarısı yok", CHECK, "            if dirty is None:\n", "            if False:\n", TS),
    ("C75 başlıkta kirli sayısı 0", CHECK, 'f"commit edilmemiş değişiklik: {_count(dirty)} dosya")',
     'f"commit edilmemiş değişiklik: 0 dosya")', TS),
    ("C76 yerel saat", CHECK, '    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())',
     '    return time.strftime("%Y-%m-%d %H:%M:%S")', TS),
    ("C77 bekçi raporu saymaz", CHECK, "        if rel.lower().endswith(DOC_SUFFIX) or rel == REPORT_LOG:",
     "        if rel.lower().endswith(DOC_SUFFIX):", TS),
    ("C85 adım zaman aşımı yok", CHECK, 'encoding="utf-8", errors="replace", timeout=timeout)',
     'encoding="utf-8", errors="replace")', TH),
    ("C78 bekçi silinmiş yolu sayar", CHECK, '        if rel.split("/")[0] in _SKIP_DIRS or not full.exists():',
     '        if rel.split("/")[0] in _SKIP_DIRS:', TS),
    # --- the runtime guard
    ("G01 kopyalama olayı yok", GUARD, '_EVENTS = frozenset({"open", "shutil.copyfile", "_winapi.CopyFile2",',
     '_EVENTS = frozenset({"open", "_winapi.CopyFile2",', TS),
    ("G02 Windows kopyası yok", GUARD, '"shutil.copyfile", "_winapi.CopyFile2", "os.link"', '"shutil.copyfile", "os.link"', TS),
    ("G03 sabit bağlantı yok", GUARD, '"_winapi.CopyFile2", "os.link", "os.symlink",', '"_winapi.CopyFile2", "os.symlink",', TS),
    ("G04 sembolik bağlantı yok", GUARD, '"os.link", "os.symlink", "_winapi', '"os.link", "_winapi', TS),
    ("G05 bağlantı izlenmez", GUARD, "        if not os.path.islink(p):\n            return\n", "        return\n", TS),
    ("G06 kayıtta çözümleme yok", GUARD, "    OPENED.add(os.path.realpath(p))", "    OPENED.add(p)", TS),
    ("G07 dizin gezmesinde çözümleme yok", GUARD, "OPENED.update(os.path.realpath(os.path.join(d, f)) for f in files",
     "OPENED.update(os.path.join(d, f) for f in files", TS),
    ("G08 dizin gezmesi harfe duyarlı", GUARD, "for f in files if f.lower().endswith(_WATCHED))",
     "for f in files if f.endswith(_WATCHED))", TS),
    ("G09 Windows adı düzeltilmez", GUARD, '    return head + sep + tail.split(":", 1)[0].rstrip(". ")',
     "    return head + sep + tail", TS),
    ("G11 günlük izlenmez", GUARD, ', "check_full.log")', ")", TS),
    ("G12 kötü çıkış üzerine yazılır", GUARD, "    if _PROBLEMS and session.exitstatus == pytest.ExitCode.OK:",
     "    if _PROBLEMS:", TS),
    ("G13 oturum düşmez", GUARD, "        session.exitstatus = pytest.ExitCode.TESTS_FAILED", "        pass", TS),
    ("G15 göreli bağlantı çalışma dizininden", GUARD,
     "            path = os.path.join(os.path.dirname(os.fsdecode(args[1])), path)\n", "            pass\n", TS),
    ("G16 junction olayı yok", GUARD, ', "_winapi.CreateJunction"})', "})", TS),
    ("G17 junction dizini gezilmez", GUARD, '_DIRECTORY_LINKS = ("os.symlink", "_winapi.CreateJunction")',
     '_DIRECTORY_LINKS = ("os.symlink",)', TS),
    ("G18 sürücüye göreli ad", GUARD, '    if not sep and p[1:2] == ":":', "    if False:", TS),
    ("G14 satırlar yazılmaz", GUARD, "        for line in _PROBLEMS:\n            terminalreporter.write_line(line)",
     "        pass", TS),
    # --- the split sweep
    ("A01 tek süreçte de yeniden deneme", ADV,
     'if workers > 1 and (r["sandbox_timeouts"] or r["sandbox_restarts"] or r["sandbox_errors"]):',
     'if (r["sandbox_timeouts"] or r["sandbox_restarts"] or r["sandbox_errors"]):', TA),
    ("A02 yeniden deneme yok", ADV, "        if workers > 1 and (r[\"sandbox_timeouts\"]", "        if False and (r[\"sandbox_timeouts\"]", TA),
    ("A03 yeniden başlatma denemeye girmez", ADV, '(r["sandbox_timeouts"] or r["sandbox_restarts"] or r["sandbox_errors"])',
     '(r["sandbox_timeouts"] or r["sandbox_errors"])', TA),
    ("A04 hata denemeye girmez", ADV, '(r["sandbox_timeouts"] or r["sandbox_restarts"] or r["sandbox_errors"])',
     '(r["sandbox_timeouts"] or r["sandbox_restarts"])', TA),
    ("A05 temel karar karşılaştırılmaz", ADV, 'if (alone["base"], alone["rows"]) != (r["base"], r["rows"]):',
     'if alone["rows"] != r["rows"]:', TA),
    ("A06 toplam zaman aşımı 0", ADV, '"sandbox_timeouts": sum(p["sandbox_timeouts"] for p in per_item),',
     '"sandbox_timeouts": 0,', TA),
    ("A07 toplam hata 0", ADV, '"sandbox_errors": sum(p["sandbox_errors"] for p in per_item), "rechecked": rechecked,',
     '"sandbox_errors": 0, "rechecked": rechecked,', TA),
    ("A08 öğede zaman aşımı yerine hata", ADV, '"seconds": round(r["seconds"], 3), "sandbox_timeouts": r["sandbox_timeouts"],',
     '"seconds": round(r["seconds"], 3), "sandbox_timeouts": r["sandbox_errors"],', TA),
    ("A09 öğede zaman aşımı sayılmaz", ADV, '"sandbox_timeouts": sb.timeouts - timeouts0 + ', '"sandbox_timeouts": 0 + ', TA),
    ("A10 öğede yeniden başlatma sayılmaz", ADV, '"sandbox_restarts": sb.restarts - restarts0,', '"sandbox_restarts": 0,', TA),
    ("A11 kayıp öğe fark edilmez", ADV, "zip(items, results, strict=True)", "zip(items, results)", TA),
    ("A12 forkserver", ADV, 'ctx = mp.get_context("spawn")', 'ctx = mp.get_context("forkserver")', TA),
    ("A13 fork", ADV, 'ctx = mp.get_context("spawn")', 'ctx = mp.get_context("fork")', TA),
    ("A14 ebeveyn ölünce çocuklar kalır", ADV, "        for child in mp.active_children():", "        for child in []:", TA),
    ("A15 parça boyu 8", ADV, "chunksize=1)", "chunksize=8)", TA),
    ("A16 bitiş sırasıyla puanlama", ADV, "        yield from ex.map(attack, items, chunksize=1)",
     "        import concurrent.futures as cf\n        futures = [ex.submit(attack, it) for it in items]\n"
     "        yield from (f.result() for f in cf.as_completed(futures))", TA),
    ("A17 hata sayısı bayrak sayısı", ADV, "errors += bool(flags & _ERROR_FLAGS)", "errors += len(flags & _ERROR_FLAGS)", TA),
    ("A18 yalnız katman bayrakları", ADV, "flags = set(res.flags).union(*(l.flags for l in res.layers))",
     "flags = set().union(*(l.flags for l in res.layers))", TA),
    ("A19 işlemci sayısı yok sayılır", ADV, "    return max(1, min(DEFAULT_WORKERS, cpus))", "    return DEFAULT_WORKERS", TA),
    ("A22 kayıp sandbox sayılmaz", ADV, "                sb.lost_calls += 1\n", "                pass\n", TA),
    ("A23 z3 zaman aşımı sayılmaz", ADV, "                sb.z3_timeouts += 1\n", "                pass\n", TA),
    ("A24 canlı süreçteki hata da kayıp", ADV, "            if not sb._alive():\n", "            if True:\n", TA),
    ("A25 hızlı unknown da zaman aşımı", ADV, "            if time.perf_counter() - t0 >= 0.9 * limit_ms / 1000:\n",
     "            if True:\n", TA),
    ("A26 sandbox izlenmez", ADV, "    _watch_sandbox(sb)\n", "\n", TA),
    ("A27 z3 zaman aşımı öğeye yansımaz", ADV, ' + getattr(sb, "z3_timeouts", 0) - z3_timeouts0,', ",", TA),
    ("A28 kayıp sandbox öğeye yansımaz", ADV, '"sandbox_errors": errors + getattr(sb, "lost_calls", 0) - lost0}',
     '"sandbox_errors": errors}', TA),
    ("A29 sandbox iki kez sarılır", ADV, '    if getattr(sb, "lost_calls", None) is not None or not hasattr(sb, "call"):',
     '    if not hasattr(sb, "call"):', TA),
    ("A20 günlükte zaman aşımı yerine hata", CHECK, "sandbox zaman aşımı {adv['sandbox_timeouts']} · \"",
     "sandbox zaman aşımı {adv['sandbox_errors']} · \"", TA),
    ("A21 günlükte hata yerine zaman aşımı", CHECK, "sandbox/katman hatası {adv['sandbox_errors']} · \"",
     "sandbox/katman hatası {adv['sandbox_timeouts']} · \"", TA),
]


_RUNNING: set[subprocess.Popen] = set()           # the test runs, killed if the runner is stopped
_LOCK = threading.Lock()
_STOPPING = threading.Event()


def _stop(signum, frame):
    """SIGTERM/SIGHUP (a cloud turn's end, `timeout`) end Python without running `finally`: the
    clones, which hold the tracked .env, stayed in the temp directory (review, 26 Sep 2026)."""
    _STOPPING.set()
    with _LOCK:
        for proc in list(_RUNNING):
            proc.kill()
    raise SystemExit(128 + signum)


def clone(dest: Path) -> None:
    subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(REPO), str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "remote", "remove", "origin"], check=True)
    (dest / ".env").unlink(missing_ok=True)       # no test here reads it; its history stays in .git


def run_tests(where: Path, test: str) -> subprocess.CompletedProcess:
    """The test file in the clone, with the clone's own src first: the venv's editable install points
    at the checkout the runner came from, and a child process would import that one (review)."""
    env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
               PYTHONPATH=os.pathsep.join([str(where / "src"), str(where)]))
    cmd = [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "--timeout", "300", test]
    with subprocess.Popen(cmd, cwd=where, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="utf-8", errors="replace") as proc:
        with _LOCK:
            _RUNNING.add(proc)
        try:
            out, _ = proc.communicate()
        finally:
            with _LOCK:
                _RUNNING.discard(proc)
    return subprocess.CompletedProcess(cmd, proc.returncode, out, "")


def _remove(tmp: Path) -> bool:
    """Delete the clones (git's object files are read-only on Windows) and say whether they are gone."""
    def writable(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    shutil.rmtree(tmp, onexc=writable) if sys.version_info >= (3, 12) else shutil.rmtree(tmp, onerror=writable)
    return not tmp.exists()


def mutate(where: Path, m) -> str:
    name, rel, old, new, test, *count = m
    if _STOPPING.is_set():
        return f"UYGULANMADI  {name}: durduruldu"
    f = where / rel
    src = f.read_text(encoding="utf-8")
    if src.count(old) != (count[0] if count else 1):
        return f"UYGULANMADI  {name}: desen {src.count(old)} kez var"
    f.write_text(src.replace(old, new), encoding="utf-8")
    try:
        t0 = time.time()
        p = run_tests(where, test)
    finally:
        f.write_text(src, encoding="utf-8")
    first = next((l for l in p.stdout.splitlines() if l.startswith(("FAILED", "ERROR"))), "")
    verdict = "öldü        " if p.returncode else "YAŞADI      "
    return f"{verdict}{name} ({time.time() - t0:.0f} s) {first[:150]}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-j", "--jobs", type=int, default=1, help="aynı anda koşan klon sayısı")
    ap.add_argument("--list", action="store_true", help="mutasyonları yaz ve çık")
    ap.add_argument("--kayit", metavar="DOSYA",
                    help="her sonucu (HEAD, ad) ile bu JSONL dosyasına hemen ekler; aynı HEAD'de yeniden koşulunca "
                         "kayıtlı mutasyonları atlar (konteyner yeniden başlarsa kaldığı yerden sürer)")
    ap.add_argument("names", nargs="*", help="yalnız adı bu öneklerle başlayan mutasyonlar (ör. C0 G A16)")
    args = ap.parse_args(argv)
    chosen = [m for m in MUTATIONS if not args.names or m[0].startswith(tuple(args.names))]
    unknown = [n for n in args.names if not any(m[0].startswith(n) for m in MUTATIONS)]
    if unknown or not chosen:
        print(f"hiçbir mutasyonla eşleşmeyen ad: {', '.join(unknown) or '(hiç mutasyon seçilmedi)'}")
        return 2
    if args.list:
        print("\n".join(m[0] for m in chosen))
        return 0
    for name in ("SIGTERM", "SIGHUP"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _stop)
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    kayit = Path(args.kayit) if args.kayit else None
    done = {}
    if kayit is not None and kayit.exists():
        for raw in kayit.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(raw)
            except ValueError:
                continue
            if r.get("head") == head and r.get("name") in {m[0] for m in chosen}:
                done[r["name"]] = r["line"]
    if done:
        print(f"kayıttan {len(done)} mutasyon atlandı ({kayit}, HEAD {head})", flush=True)
        for line in done.values():
            print(line, flush=True)
        chosen = [m for m in chosen if m[0] not in done]
        if not chosen:
            lines = list(done.values())
            killed = sum(l.startswith("öldü") for l in lines)
            print(f"toplam: {len(lines)} mutasyon, {killed} öldü, "
                  f"{sum(l.startswith('YAŞADI') for l in lines)} yaşadı, "
                  f"{sum(l.startswith('UYGULANMADI') for l in lines)} uygulanmadı")
            return 0 if killed == len(lines) else 1
    tmp = Path(tempfile.mkdtemp(prefix="mutasyon-"))
    print(f"klonlar: {tmp} (sonunda silinir)", flush=True)
    try:
        jobs = max(1, min(args.jobs, len(chosen)))
        copies = [tmp / f"k{i}" for i in range(jobs)]
        for c in copies:
            clone(c)
        print(f"HEAD {head} · {len(chosen)} mutasyon · {jobs} klon", flush=True)
        for test in sorted({m[4] for m in chosen}):
            p = run_tests(copies[0], test)
            if p.returncode:
                print(f"mutasyonsuz {test} geçmedi: ölçüm yapılamaz\n{p.stdout[-2000:]}", flush=True)
                return 2
        free = list(copies)
        lines = []
        ex = concurrent.futures.ThreadPoolExecutor(jobs)
        try:
            def one(m):
                where = free.pop()
                try:
                    return mutate(where, m)
                finally:
                    free.append(where)
            lines.extend(done.values())
            for m, line in zip(chosen, ex.map(one, chosen)):
                print(line, flush=True)
                lines.append(line)
                if kayit is not None and "durduruldu" not in line:
                    with kayit.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps({"head": head, "name": m[0], "line": line}, ensure_ascii=False) + "\n")
        finally:
            ex.shutdown(wait=True, cancel_futures=True)
        killed = sum(l.startswith("öldü") for l in lines)
        print(f"toplam: {len(lines)} mutasyon, {killed} öldü, "
              f"{sum(l.startswith('YAŞADI') for l in lines)} yaşadı, {sum(l.startswith('UYGULANMADI') for l in lines)} uygulanmadı")
        return 0 if killed == len(lines) else 1
    finally:
        if not _remove(tmp):
            print(f"UYARI: klonlar silinemedi, elle silinmeli (içlerinde .env geçmişi var): {tmp}", flush=True)
            raise SystemExit(3)


if __name__ == "__main__":
    sys.exit(main())

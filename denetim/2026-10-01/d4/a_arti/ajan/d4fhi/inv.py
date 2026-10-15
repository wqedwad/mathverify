"""Builds the d4f/d4h/d4i/kalan inventory JSON and the counts (own data, no repo code)."""
import collections
import json

P = "wf/d4fhi/probe.py"  # own probe (8 runs, 15 Oct 2026)
NA = "zaten UNKNOWN (kapsama kaybı): kural gerekmez, bilinen sınır olarak kaydedilir"

F = []


def add(id, part, klass, introduced, status, realistic, reason, fc, rule, risk, sev, source, evidence, wip=""):
    F.append(dict(id=id, part=part, klass=klass, introduced=introduced, status=status, realistic=realistic,
                  realistic_reason=reason, failclosed_coverable=fc, failclosed_rule=rule, rule_risk=risk,
                  severity=sev, source=source, wip_ref=wip, evidence=evidence))


# ---------------- d4f original (6) ----------------
E_D4F1 = ("Düzeltme 7d29714 (edison atası); kosular.txt:69 'sonda 151/225->0, test 111'; DECISIONS.md:436; "
          "testler edison tests/test_d4_d4f_tanimlilik.py")
add("CAP-F1", "d4f", "false_accept", "preexisting", "closed_in_branch", "unclear",
    "Negatif tam sayının faktöriyeli çözücü adımında (C(n,k) formülü, k>n) yazılabilir; problem metninde beklenmez.",
    False, "", "n/a", "high", "original-60",
    E_D4F1 + ":81-204 (test_cap_f1_*). dogrulama.json A/B doğruladı. ℂ söylemindeki kardeşi açık: D4F2A-YO-3.")
add("TAN-10", "d4f", "false_accept", "preexisting", "closed_in_branch", "no",
    "Tam sayı olmayan Σ sınırı (1/2..5/2) müfredatta yok; yapay.", False, "", "n/a", "low", "original-60",
    E_D4F1 + ":216-240 (test_tan10_*). dogrulama.json'da A/B yok (yöntem değişikliği: düzeltici yeniden üretti, duzeltme_d4f.txt).")
add("C1", "d4f", "false_accept", "preexisting", "closed_in_branch", "no",
    "TAN-10 ile aynı: kesirli kaydırmalı Σ sınırı yapay.", False, "", "n/a", "low", "original-60",
    E_D4F1 + " (TAN-10/C1 tek karar, kararlar_fhi.txt:6-8; test_tan10_* kapsar). A/B yok.")
add("B1", "d4f", "false_accept", "preexisting", "closed_in_branch", "no",
    "\\alpha indisli, \\sqrt{1} sınırlı ters aralıklı LaTeX toplam floor içinde: yapay.", False, "", "n/a", "medium",
    "original-60", E_D4F1 + ":261-268 (test_b1_*). A/B yok.")
add("TAN-12", "d4f", "coverage_loss", "preexisting", "closed_in_branch", "unclear",
    "İç içe Π_{k=1}^{n} Σ_{j=1}^{k} 1 üniversite alıştırmasında görülebilir.", False, "", "n/a", "low", "original-60",
    E_D4F1 + ":278-286 (test_tan12_*). #14 getirmişti (d4 öncesi). A/B yok.")
add("G14", "d4f", "coverage_loss", "preexisting", "closed_in_branch", "unclear",
    "Faktöriyelli dizi limiti ((n−2)!/n^n) birinci sınıf analizde görülebilir.", False, "", "n/a", "low",
    "original-60", E_D4F1 + ":301-308 (test_g14_*). Yük altında süre bütçesiyle UNKNOWN kalıntısı ayrı: V20-G14-YUK. A/B yok.")

# ---------------- d4f attack round 1 (11), closed in e0983d0 ----------------
E_D4F2 = ("Düzeltme e0983d0 (edison atası); kosular.txt:89 '11 bulgu kapandı; sonda L-R 135 vakada 72 -> 0'; "
          "DECISIONS.md:436; kararlar d4/saldiri/d4f/kararlar_tur2.txt")
add("D4F-YO-1", "d4f", "false_accept", "preexisting", "closed_in_branch", "unclear",
    "Örnek yapay (x²/x + Σ_{k=√1}^{3}), ama okunamayan yazılı metni 'koşul yok' sayan mekanizma her girdide geçerliydi.",
    False, "", "n/a", "high", "d4f", E_D4F2 + ":3; d4/saldiri/d4f/bulgular.json d4f-YO-1.")
add("D4F-YO-2", "d4f", "false_accept", "preexisting", "closed_in_branch", "no",
    "√x girişli matrisin determinant denklemi yapay.", False, "", "n/a", "high", "d4f",
    E_D4F2 + ":8. Kardeşi D4F2A-YO-1 (bu düzeltmenin yeni yolu) açık.")
add("D4F-YO-3", "d4f", "false_accept", "by_d4_fix", "closed_in_branch", "no",
    "Gerçel n'li Σ_{k=n}^{n+2} ve sin(πn) eklenmiş iddia yapay.", False, "", "n/a", "medium", "d4f",
    E_D4F2 + ":10 (d4f 1. tur getirdi). Doğrusal olmayan sınır kardeşi D4F2A-RK-1 açık.")
add("D4F-YO-4", "d4f", "false_accept", "preexisting", "closed_in_branch", "no",
    "Payında cos(πx/2)/cos(πx/2) gibi özdeş kesir olan dizi yapay.", False, "", "n/a", "medium", "d4f",
    E_D4F2 + ":13. Saldırgan 'parça getirdi' dedi, doğrulayıcı 'önceden var' (faktöriyelsiz akrabaları tabanda da CORRECT). "
    "Kuyruk kapısı D4F2B-RK-2 kapsama kaybını getirdi.")
add("D4F-YO-5", "d4f", "false_accept", "preexisting", "closed_in_branch", "no",
    "1/factorial(−a) gibi değersiz iddia gerçek çözücüden beklenmez.", False, "", "n/a", "medium", "d4f",
    E_D4F2 + ":15.")
add("D4F-YO-6", "d4f", "false_accept", "preexisting", "closed_in_branch", "no",
    "Nokta, merkez ya da başlangıç değerinde 1/(−1)! yapay.", False, "", "n/a", "medium", "d4f",
    E_D4F2 + ":17. Bu düzeltmenin yan etkisi D4F2B-RK-1 (yalın ad etiketleri) açık.")
add("D4F-YO-7", "d4f", "false_accept", "preexisting", "closed_in_branch", "no",
    "∞⁰ yazımı gerçek soruda nadir.", False, "", "n/a", "low", "d4f",
    E_D4F2 + ":19. Özdeş sıfır üslü kardeşi D4F2A-YO-2 açık (kapalı oo**0 kapandı; edison sondası: oo**(x−x) hâlâ CORRECT).")
add("D4F-RK-F1", "d4f", "unjust_reject", "by_d4_fix", "closed_in_branch", "no",
    "Gerçel x'li Σ_{k=x}^{x+2} k = 10 denklemi yapay.", False, "", "n/a", "medium", "d4f",
    E_D4F2 + ":21 (Convention('integer_bound')).")
add("D4F-RK-F2", "d4f", "coverage_loss", "by_d4_fix", "closed_in_branch", "unclear",
    "Γ fonksiyonlu limit/integral üniversite düzeyinde nadir de olsa görülebilir.", False, "", "n/a", "medium", "d4f",
    E_D4F2 + ":24 (limits.membership_holds_on).")
add("D4F-RK-F3", "d4f", "coverage_loss", "by_d4_fix", "closed_in_branch", "yes",
    "ℂ söyleminde √−4 = 2i AYT karmaşık sayılar konusunda standart.", False, "", "n/a", "low", "d4f",
    E_D4F2 + ":26. Problem tarafı (NO_VALUE ℂ'de düşüyor) D4F2A-YO-3 açık.")
add("D4F-RK-F4", "d4f", "coverage_loss", "by_d4_fix", "closed_in_branch", "no",
    "\\frac{1}{0} içeren denklem yapay.", False, "", "n/a", "low", "d4f", E_D4F2 + ":28.")

# ---------------- d4f attack round 2 (13): d4f round 3 NOT started ----------------
K3 = "d4/saldiri/d4f2/kararlar_tur3.txt"
B2 = "d4/saldiri/d4f2/bulgular.json"
OPEN3 = "d4f 3. tur başlamadı (DECISIONS.md:457; HANDOFF.md §3 adım 2 (v)); karar yazılı, kod yok. "
add("D4F2A-YO-1", "d4f", "false_accept", "by_d4_fix", "open", "no",
    "0⁰ girişli matrisin izi/determinantı yapay.", True,
    "normalize.parse._held_matrix_op: girdide sıfır üslü Pow (taban değerlenince 0 olabilir) ya da kendi tanımlılık/gelenek "
    "koşulu olan alt ifade varsa matris işlemi hesaplanmaz (tutulur → yazılı okuma kararsız → UNKNOWN); küçük kesin düzeltme",
    "none", "medium", "d4f2",
    OPEN3 + K3 + ":7; " + B2 + ". d4f 2. turun (YO-2 düzeltmesi) getirdiği. Sonda (" + P + "): edison, wip/d4e-tur4, "
    "wip/d4b-tur9, wip/d4h'de trace([[0**0,0],[0,0]]) = 1 CORRECT.")
add("D4F2A-YO-2", "d4f", "false_accept", "preexisting", "open", "no",
    "oo**(x−x), 0**(x−x) gibi özdeş sıfır üs yapay.", True,
    "domain._node_conditions Pow: tabanı 0 ya da ±oo olan ve üssü sabit olmayan (ya da sadeleşince 0 olan) her kuvvet "
    "Convention zero_power (değer geleneği) → karar UNKNOWN",
    "low", "low", "d4f2",
    OPEN3 + K3 + ":10; " + B2 + ". Sonda: dört dalda oo**(x − x) → 1 ve 0**(x − x) → 1 CORRECT.")
add("D4F2A-YO-3", "d4f", "false_accept", "preexisting", "open", "no",
    "ℂ söyleminde 1/(−1)!, 0⁰, ∞⁰, Mod(7,−5) yapay.", True,
    "Ctx.written_undefined/written_undecided: domain_of_discourse ℂ iken yalnız gerçele özgü koşullar (√ ve log negatif) "
    "düşer; NO_VALUE ve Convention koşulları kalır → UNKNOWN",
    "none", "medium", "d4f2",
    OPEN3 + K3 + ":12; " + B2 + " (saldırgan high, doğrulayıcı medium). Sonda: dört dalda ℂ'de 1/factorial(-1) → 0 CORRECT.")
add("D4F2A-YO-4", "d4f", "false_accept", "preexisting", "closed_in_branch", "no",
    "Kısıtta sqrt(−1)**2, log(−1)·0 ya da x/x yapay.", False, "", "n/a", "medium", "d4f2",
    K3 + ":15; " + B2 + ". Saldırı e0983d0'da koştu; edison (d342778) d4e 3. turu içeriyor (fcd9f82 'YO-5', d3e805c). Sonda (" + P +
    ", edison): kısıt x > sqrt(-1)**2 ve x > log(-1)*0 ile {1} UNKNOWN, x/x > 0 ile {-1,0,1} INCORRECT / {-1,1} CORRECT, "
    "limit verileni UNKNOWN (5/5 beklenen; yalnız 5 temsilci vaka). Kararsız yazılı kısıt kalıntısı = D4E3-YO-3 (d4e grubu, wip/d4e-tur4).")
add("D4F2A-YO-5", "d4f", "false_accept", "preexisting", "open", "no",
    "0·sin(∞) yapay; e^{−∞} = 0 alt grubu gelenek tutarlılığı, yanlış onay değil.", True,
    "domain._node_conditions: SymPy değeri AccumBounds olan ya da kapalı argümanı ±oo olan toplam fonksiyon "
    "(sin, cos, frac, floor, sign) düğümü NO_VALUE → UNKNOWN; lim görevleri hariç",
    "none", "low", "d4f2",
    OPEN3 + K3 + ":20; " + B2 + " (saldırgan medium, doğrulayıcı low). Sonda: dört dalda 0*sin(oo) → 0 CORRECT. "
    "e^{−∞}/2^{−∞} tutarlılık alt grubu ayrıca UNKNOWN'a çekilirse çözücünün 'e^{−∞} = 0' adımı unknown olur (ceza yok).")
add("D4F2A-RK-1", "d4f", "unjust_reject", "by_d4_fix", "open", "no",
    "Doğrusal olmayan gerçel sınırlı Σ (k = n²..n²+2) ve sin(πn²) eklenmiş iddia yapay.", True,
    "certify.domain.convention_split integer_bound: sınır doğrusal değilse ya da tam sayılığı kanıtlanamıyorsa bölge kurulamaz → "
    "karar UNKNOWN (algebra._beyond_value_conventions ok False dalında da çürütme yok)",
    "none", "low", "d4f2",
    OPEN3 + K3 + ":23; " + B2 + ". Sonda: dört dalda Sum(k,(k,n**2,n**2+2)) için 3n²+3+sin(πn²) INCORRECT.")
add("D4F2B-RK-1", "d4f", "coverage_loss", "by_d4_fix", "open", "yes",
    "Nokta adı P, S ve renk baş harfli öğeler (S = sarı) Türkçe geometri/olasılık sorularında çok yaygın.", True, NA,
    "n/a", "medium", "d4f2",
    OPEN3 + K3 + ":30; " + B2 + " (11 vaka gerileme). Sonda: dört dalda PQR üçgeni PR = 10 UNKNOWN "
    "(problem_definedness_undecided). Küçük kesin düzeltme: _unread yalın adı (işlev/sınıf nesnesi okuması) metin saymaz; "
    "doğru cevap UNKNOWN, yanlış cevap (11) da UNKNOWN.")
add("D4F2B-RK-2", "d4f", "coverage_loss", "by_d4_fix", "open", "yes",
    "ln n/(n − ln n), n²/(n² − 2ⁿ), 1/⌊n/2⌋ gibi ders kitabı dizi limitleri gerçekçi.", True, NA, "n/a", "medium",
    "d4f2", OPEN3 + K3 + ":33; " + B2 + " (20 vaka). Sonda: dört dalda lim 1/(2^x − 1000) = 0 UNKNOWN "
    "(sequence_undefined_on_the_tail; bayrak adı yanıltıcı: dizi kuyrukta tanımlı).")
add("D4F2B-YO-1", "d4f", "false_accept", "by_d4_fix", "closed_in_wip_only", "no",
    "Çözücünün adımda üst sınırı \\log_3 27 yazılmış Σ kullanması beklenmez.", True,
    "steps.deterministic._convention_as_written: okunamayan yazılı metin gelenek sayılmaz; çürütme yalnız değer okumasında "
    "gelenek düğümü varsa geri çekilir",
    "low", "medium", "d4f2",
    K3 + ":25; " + B2 + ". Sonda (" + P + "): edison ve wip/d4h'de yanlış adım 'unknown', çözüm CORRECT (açık); "
    "wip/d4b-tur9 (9d60d17)'da adım refuted, INCORRECT, doğru adım verified: d4b 9–10. tur (büyük olasılıkla _sympy_guards evalf "
    "tavanı RecursionError'u gideriyor) bunu yan etkiyle kapatıyor; hiçbir belgede kayıtlı değil.", "wip/d4b-tur9 (9d60d17)")
add("D4F2B-RK-3", "d4f", "coverage_loss", "by_d4_fix", "closed_in_wip_only", "unclear",
    "Logaritma ve Σ birleşen sorular YKS'de görülür, ama sınırın \\log_b a yazılması nadir.", True, NA, "n/a", "low",
    "d4f2", K3 + ":25; " + B2 + ". Sonda: edison/wip/d4h'de Σ_{k=1}^{log_3 27} k = 6 UNKNOWN; wip/d4b-tur9'da 6 CORRECT, 7 INCORRECT.",
    "wip/d4b-tur9 (9d60d17)")
add("D4F2B-RK-4", "d4f", "coverage_loss", "by_d4_fix", "open", "unclear",
    "Üçgensel sayı sınırlı Σ (Σ_{k=1}^{n(n+1)/2} 1) nadir ama olası.", True, NA, "n/a", "low", "d4f2",
    OPEN3 + K3 + ":36; " + B2 + ". Sonda: dört dalda UNKNOWN.")
add("D4F2B-RK-5", "d4f", "coverage_loss", "by_d4_fix", "open", "unclear",
    "1/det(A) doğrusal cebirde olası; √ girişli kapalı matris nadir.", True, NA, "n/a", "low", "d4f2",
    OPEN3 + K3 + ":39; " + B2 + ". Sonda: dört dalda 1/det([[√2,1],[1,√2]]) = 1 UNKNOWN.")
add("D4F2B-ONCEKI-1", "d4f", "unjust_reject", "preexisting", "open", "yes",
    "YKS şıkları ondalık virgüllü ('1,5') ve 'x > −2' biçiminde olabilir; doğru cevap INCORRECT oluyor.", True,
    "mc.consistency yalnız şık metni cevap biçiminin türünde (aralık/küme/sayı) okunduğunda veto eder; FiniteSet(ilişki), "
    "Tuple ya da ondalık virgül şüphesinde çekimser → UNKNOWN",
    "none", "medium", "d4f2",
    OPEN3 + K3 + ":42; " + B2 + ". Sonda: edison, wip/d4b-tur9 ve wip/d4h'de 'x > -2' şıkkı ve '1,5' şıkkı INCORRECT "
    "(d4h 2. turun PRE-RK-5 iddia gösterimi şık yolunu kapsamıyor).")

# ---------------- d4h original (7): round 1 a2f5603 only in wip/d4h ----------------
WH = "wip/d4h (a2f5603; 1aa422f ara)"
E_H1 = ("Düzeltme a2f5603 (edison'da yok: git merge-base); kosular.txt:109,120 (sonda 301/0; ec62a68'de 186 beklenmeyen); "
        "DECISIONS.md:456; notlar/duzeltme_d4h.txt")
add("F1", "d4h", "false_accept", "preexisting", "closed_in_wip_only", "no",
    "Problem metninde simplify(Limit(...)) sarmalaması gerçek IR'da beklenmez.", True,
    "problem/adım metninde biçim sarmalayıcısı (simplify, expand, factor, ...) içinde kapalı Limit/Integral/Sum varsa UNKNOWN",
    "low", "high", "original-60",
    E_H1 + ". Kardeşleri D4H-YO-1 (işleç/kurucu yolları) ve D4H-YO-3 (anahtar kelime) 2. turda. A/B yok. "
    "Edison'da ölçmedim (35–130 s); kod yolu edison'da değişmedi.", WH)
add("H1", "d4h", "false_accept", "preexisting", "closed_in_wip_only", "no",
    "Limit girişli matris yapay.", True, "Matrix girdisinde kapalı Limit/Integral/Sum varsa UNKNOWN", "none", "medium",
    "original-60", E_H1 + ". A/B yok.", WH)
add("D1", "d4h", "false_accept", "preexisting", "closed_in_wip_only", "yes",
    "Fonksiyon tanım kümesinin LaTeX 'x ∉ [0,3]' ile verilmesi gerçekçi.", True,
    "fonksiyon alanı/verilen metni değişken adını anıp sabit True/False'a çöküyorsa okunmaz → UNKNOWN (d4d not_collapsed "
    "kuralının alan okuyucusuna genişletilmesi)",
    "low", "high", "original-60",
    E_H1 + ". Sonda (" + P + "): edison'da f(x)=5, alan '$x \\notin [0,3]$', {-2,2} CORRECT (açık); wip/d4h'de UNKNOWN. A/B yok.", WH)
add("D2", "d4h", "false_accept", "preexisting", "closed_in_wip_only", "unclear",
    "Tanım kümesinin virgüllü aralık listesiyle yazılması IR yazarından gelebilir.", True,
    "alan metni en az bir aralık/küme parçası içeren çok parçalı liste ise ve parçalar özdeş değilse UNKNOWN "
    "('x > 0, x ≠ 1' gibi ilişki listeleri kesişim kalır)",
    "low", "medium", "original-60",
    E_H1 + ". #14 getirmişti. Sonda: edison '(-oo,-1), (1,oo)' ile {} CORRECT (açık); wip/d4h UNKNOWN. A/B yok.", WH)
add("I2", "d4h", "false_accept", "preexisting", "closed_in_wip_only", "no",
    "d ve dn adlı değişken bildirimi yapay.", True,
    "bildirilmiş sembollerden biri d ya da d+değişken adıysa LaTeX'te d ile başlayan pay/paydalı \\frac → UNKNOWN",
    "low", "low", "original-60",
    E_H1 + ". Sonda: edison 0 CORRECT (açık); wip/d4h UNKNOWN. Kardeşi D4H-YO-2 2. turda. A/B yok.", WH)
add("CAP-G1", "d4h", "other", "preexisting", "closed_in_wip_only", "no",
    "Değer doğru; yanlış cevap onayı doğurmuyor, yalnız ilke 2 (doğrulayıcı hesaplamaz) tutarlılığı.", True,
    "iddia ağacında kapalı sayı argümanlı gcd/lcm düğümü varsa claim_is_not_a_value", "none", "low", "original-60",
    E_H1 + ". dogrulama.json A/B doğruladı. Sonda: edison \\mathit{gcd}(120,84) CORRECT; wip/d4h UNKNOWN (claim_is_not_a_value).", WH)
add("G11", "d4h", "unjust_reject", "preexisting", "closed_in_wip_only", "unclear",
    "İki aile parametreli genel çözüm ({nπ + kπ}) çözücüden nadir gelir.", True,
    "iddiada iki ya da daha çok aile parametresi varsa UNKNOWN (tohumdan bağımsız)", "low", "low", "original-60",
    E_H1 + "; G11 tohumları PYTHONHASHSEED 0..7: ec62a68'de 14 beklenmeyen, a2f5603'te 0 (kosular.txt:120). dogrulama.json A/B "
    "doğruladı; A ayrıca 5 yanlış onay buldu (cos x = 1 için {2nπ + 3kπ} bazı tohumlarda CORRECT). Kafes indirgemesi D4H-YO-5'i getirdi.", WH)

# ---------------- d4h attack round 1 (13): round 2 interim 1aa422f ----------------
K2 = "d4/saldiri/d4h/kararlar_tur2.txt"
BH = "d4/saldiri/d4h/bulgular.json"
R2 = ("2. tur ara commit 1aa422f (wip/d4h; mesajı: sonda d4h 600 durumda 88d68df'te 167 → 1, test_d4_*/parca* 24 düşen düzeltildi; "
      "tam ölçüm, mutasyon ve saldırı yok; scr/d4/duzeltme/d4h/NOTLAR.md:108-189). ")
WR2 = "wip/d4h (1aa422f, ara)"
add("D4H-YO-1", "d4h", "false_accept", "preexisting", "fix_in_progress", "no",
    "1000e^{−10⁶(x−1/3)²} gibi sivri integralin tam kısmı yapay.", True,
    "ayrıştırma sırasında kapalı Integral/Sum/Product/Limit'in evalf'i alınmaz; kapalı form karar veren düğümün (floor, ceiling, //, %, "
    "karşılaştırma, Interval, Piecewise, Max/Min, subs) argümanıysa UNKNOWN",
    "low", "medium", "d4h", R2 + K2 + ":6; " + BH + ". Doğru değerin (SPK//1 = 1) haksız reddi de aynı kök.", WR2)
add("D4H-YO-2", "d4h", "false_accept", "preexisting", "fix_in_progress", "unclear",
    "d'nin ortak fark ya da uzaklık adı olduğu soruda \\frac{d}{d\\,x} yazımı olası ama nadir.", True,
    "normalleştirilmiş LaTeX'te (boşluk komutları, \\mathrm{d}, süslü/parantez, \\dfrac) d^k/(d v)^k kesri ve d ya da dv adı "
    "bildirilmişse UNKNOWN",
    "low", "medium", "d4h", R2 + K2 + ":11; " + BH + ". Türev okumasıyla doğru iddianın (2x) haksız reddi de var.", WR2)
add("D4H-YO-3", "d4h", "false_accept", "preexisting", "fix_in_progress", "no",
    "simplify(expr=...) anahtar kelimeli yazım çözücü adımında beklenmez.", True,
    "anahtar kelimeli argümanlı çağrı (f(name=...)) içeren iddia/adım metni okunmaz → UNKNOWN/unknown", "none", "medium",
    "d4h", R2 + K2 + ":15; " + BH + ". Doğru adımın (= 4 sin 1) reddi de aynı kök.", WR2)
add("D4H-YO-4", "d4h", "false_accept", "preexisting", "fix_in_progress", "no",
    "İki argümanlı fonksiyonun alanının boş kesişimli listeyle yazılması yapay.", True,
    "çok argümanlı fonksiyonun alan metni çok parçalı listeyse UNKNOWN", "low", "low", "d4h",
    R2 + K2 + ":17; " + BH + ". Doğrulayıcı: yalnız iki argümanlı alan kısmı gerçek; verilen kısmı (x = 4) yanlış onay değil.", WR2)
add("D4H-YO-5", "d4h", "false_accept", "by_d4_fix", "fix_in_progress", "no",
    "m = 1/2 verilmişken iddiada m'nin aile indisi kullanılması yapay.", True,
    "iddiadaki aile indisi adı bir verilende ya da kısıtta geçiyorsa UNKNOWN (trig _problem_names)", "low", "low", "d4h",
    R2 + K2 + ":19 (ana oturum: 'bu parça getirdi'); " + BH + " (doğrulayıcı: tek aileli {mπ} tabanda da CORRECT, kök önceden var; "
    "iki aileli biçim G11 kafes indirgemesiyle UNKNOWN→CORRECT oldu).", WR2)
add("D4H-RK-1", "d4h", "coverage_loss", "by_d4_fix", "fix_in_progress", "yes",
    "'x ∈ ℝ' verileni IR'da çok olası.", True, NA, "n/a", "medium", "d4h",
    R2 + K2 + ":22; " + BH + ". d4h 1. tur (a2f5603) getirdi; 1. tur 2. tursuz birleşirse gerçekçi gerileme dalda olur.", WR2)
add("D4H-RK-2", "d4h", "coverage_loss", "by_d4_fix", "fix_in_progress", "unclear",
    "Örtüşen aralık listesiyle verilen tanım kümesi nadir.", True, NA, "n/a", "low", "d4h",
    R2 + K2 + ":26; " + BH + " (19 vaka).", WR2)
add("D4H-RK-3", "d4h", "other", "by_d4_fix", "fix_in_progress", "no",
    "Sonda beklenti hatası (SPK ≠ √π); kod hatası değil.", False, "", "n/a", "low", "d4h",
    R2 + K2 + ":30; " + BH + ". 1aa422f sonda C güncellendi.", WR2)
add("PRE-RK-4", "d4h", "unjust_reject", "preexisting", "fix_in_progress", "yes",
    "SOLVER_FORMAT denklemi params.equation'a koymaya izin veriyor; adımlı doğru çözümler INCORRECT oluyor.", True,
    "solve_equation/solve_inequality'de denklem params'ta ise ve adım öncül havuzunda yoksa çürütme geri çekilir (unknown); "
    "küçük kesin düzeltme (params.equation öncül havuzuna, 1aa422f steps _task_relations) tercih edilir",
    "none", "high", "d4h",
    R2 + K2 + ":32; " + BH + ". Sonda (" + P + "): edison x²−x−2=0 params, {-1,2} + adım 'x + 2 = x**2' INCORRECT (s1 refuted); "
    "wip/d4h CORRECT (s1 verified). evalset'in 14 solve_equation öğesi givens biçiminde olduğu için fark.py görmüyor.", WR2)
add("PRE-RK-5", "d4h", "unjust_reject", "preexisting", "fix_in_progress", "yes",
    "Çözücüler cevabı sık sık 'x ∈ {−2, 2}' ya da 'x = ±2' biçiminde yazar.", True,
    "intake 'bilinmeyeni içeriyor / değer değil' dediği iddiada sertifikanın sert reddi UNKNOWN'a iner", "none", "medium",
    "d4h", R2 + K2 + ":36; " + BH + ". Sonda: edison '$x \\in \\{-2, 2\\}$' INCORRECT; wip/d4h CORRECT.", WR2)
add("PRE-RK-6", "d4h", "crash_or_timeout", "preexisting", "closed_in_branch", "yes",
    "'S = {−2, 2}' Türkçe çözüm kümesi gösterimi yaygın.", False, "", "n/a", "medium", "d4h",
    K2 + ":41; " + BH + " (a2f5603/62a40e9'da SympifyError). Sonda (" + P + "): edison'da 'S = {-2, 2}' UNKNOWN (parse_error), "
    "istisna sızmıyor: d4f 2. turun _claim_without_value try'ı kapatmış (scr/d4/duzeltme/d4h/NOTLAR.md:156 'PRE-RK-6 sızıntısı d4f'nin try'ı ile "
    "kapanmış'). HANDOFF V20 bunu hâlâ açık sayıyor. 1aa422f _SingletonNames ekliyor (S değer değil).")
add("PRE-RK-7", "d4h", "crash_or_timeout", "preexisting", "fix_in_progress", "no",
    "İntegral girişli matrisin determinantı yapay.", True,
    "parse_structural/parse_as_written çağrılarına süre bütçesi; aşılırsa UNKNOWN (karar bugün doğru, yalnız 132–191 s)",
    "low", "low", "d4h", R2 + K2 + ":43; " + BH + " (birleşik ağaçta 191.9 s, NOTLAR).", WR2)
add("PRE-RK-8", "d4h", "coverage_loss", "preexisting", "fix_in_progress", "unclear",
    "Matrisin en büyük özdeğeri sorusu üniversite birinci sınıfta olası.", True, NA, "n/a", "low", "d4h",
    R2 + K2 + ":45; " + BH + ".", WR2)

# ---------------- fixer-found extras (not independently verified) ----------------
add("D4H-EK-SPIKE", "d4h", "false_accept", "preexisting", "closed_in_wip_only", "no",
    "floor(∫ 1000e^{−10⁶(x−1/3)²}) yapay.", True, "D4H-YO-1 ile aynı kural", "low", "medium", "fixer-d4h",
    "d4h 1. tur düzelticisi buldu (notlar/duzeltme_d4h.txt 'Yeni kardeş bulgu ... floor(∫...) = 1 ... claim 0 CORRECT'); a2f5603'te "
    "UNKNOWN (sonda/x_spike.py). Bağımsız doğrulanmadı; saldırgan D4H-YO-1 aynı ailede kalan yolları buldu.", WH)
add("D4H2-EK-ASSET", "d4h", "other", "preexisting", "fix_in_progress", "unclear",
    "Çözücünün cevabı soruyu tekrarlayan eşitsizlik (x² < 4) olarak yazması nadir ama olası.", True,
    "görev değişkeni dışında ifade içeren ilişki biçimli iddia as_set ile çözülmez → UNKNOWN", "low", "low", "fixer-d4h",
    "d4h 2. tur düzelticisi buldu (scr/d4/duzeltme/d4h/NOTLAR.md:175: eski `[<>]` + as_set dalı x**2 < 4'ü çözüp soruyu CORRECT "
    "yapıyordu; önceden var); 1aa422f'te kaldırıldı. Bağımsız doğrulanmadı.", WR2)
add("D4F-EK-INTERVAL", "d4f", "false_accept", "preexisting", "closed_in_branch", "no",
    "Interval(1/factorial(−1), 2) yapay.", False, "", "n/a", "", "fixer-d4f",
    "d4f 1. tur düzelticisi buldu (notlar/duzeltme_d4f.txt: Interval kurucusu ucu kutup → parse_set_as_written); 2bff664 (edison atası).")
add("D4F2-EK-LATEXDET", "d4f", "false_accept", "preexisting", "closed_in_branch", "no",
    "LaTeX \\det girişli tanımlılık yapay.", False, "", "n/a", "", "fixer-d4f",
    "d4f 2. tur düzelticisi buldu (notlar/duzeltme_d4f.txt: LaTeX \\det/\\operatorname{tr|rank} yazılı okumada hesaplanıyordu, "
    "eedd182'de {-3} CORRECT); f305d8c/fbc1a3a (edison atası).")

# ---------------- d4i ----------------
add("CAP-K1", "d4i", "other", "preexisting", "unverified", "no",
    "Bugünkü Lean şablonları Σ/∫/lim basmıyor, başka birincil katman yok; ölçüm: 89 Lean koşusunda 3 UNKNOWN→CORRECT, üçü de doğru.",
    True,
    "fuse: birincil olmayan katmanın her çekimserlik bayrağı varsayılan olarak engelleyici; yalnız yazılı listedeki 'kanıtlanamadı' "
    "türü (üyelik kararsız, sertifika yok) engellemez; listede olmayan yeni bayrak bir testte yakalanır (kararlar_fhi.txt:36)",
    "low", "low", "original-60",
    "dogrulama.json CAP-K1: A/B yok (bağımsız doğrulanmadı); d4i başlamadı (DECISIONS.md:439; HANDOFF §3 adım 2 (vi)); kod yok. "
    "Kapsamı büyüdü: d4e/d4f/d4h'nin yeni bayrakları (problem_definedness_undecided — d4f bunu engelleyici yaptı, kosular.txt:69 "
    "'d4i sınıflandırsın' —, sequence_undefined_on_the_tail, domain_list_ambiguous, integer_bound ...) sınıflanmadı. "
    "Kural ölçülmüş 3 Lean kurtarmasını kaybettirebilir.")

# ---------------- unassigned original ----------------
add("D4-ADIM-I", "kalan (atanmamış)", "unjust_reject", "preexisting", "closed_in_branch", "yes",
    "Vaka ayrımlı (case) çözüm adımları gerçek çözümlerde yaygın.", False, "", "n/a", "low", "original-60",
    "60 adaydan hiçbir parçaya atanmamış tek bulgu (DECISIONS.md:415,424 parça listeleri; known=True, §84 (11) bilinen sınır). "
    "d4g 2. tur (195e183/0120211, edison atası) 'vaka varsayımı compute öncülü' ile kapattı (notlar/duzeltme_d4g.txt:74,81; "
    "DECISIONS §85 d4g tur 2). Sonda (" + P + ", edison): case x = 2 altında compute 'x**3 = 8' verified (eskiden refuted). A/B yok.")

# ---------------- small gaps (HANDOFF V20, DECISIONS §85 'Açık') ----------------
add("V20-G14-YUK", "kalan (V20)", "coverage_loss", "by_d4_fix", "open", "unclear",
    "Faktöriyelli dizi limiti gerçekçi olabilir; karar makine yüküne bağlı.", True, NA, "n/a", "low", "HANDOFF V20",
    "kosular.txt:73: test_g14_a_sequence_limit_reads_the_tail [(x-2)!/x!, C(x,3)/x^3] yük altında UNKNOWN, tek başına 2.3 s'de geçiyor; "
    "DECISIONS §86 (tur 8 satırı) 'güvenli yön, açık'; HANDOFF.md:138-146. Deterministik olmayan karar (--full yükünde test düşebilir).")
add("V20-GAUSS", "kalan (V20)", "coverage_loss", "by_d4_fix", "closed_in_wip_only", "yes",
    "Gauss integrali ∫_ℝ e^{−x²} = √π birinci sınıf klasiği.", True, NA, "n/a", "", "HANDOFF V20",
    "d4c 2. tur (db7fb6d) getirdi (DECISIONS §86 d4c tur 2 'Kapsama'); HANDOFF.md:138-146 'd4c RK-A, tur 3'te ele alındı'; "
    "wip/d4c-tur3 697a025 'erf ailesi (RK-A)'. Ölçmedim. = D4C2-RK-A (d4c grubu raporlar; çift sayılmasın).", "wip/d4c-tur3 (697a025)")
add("GAP-NE", "kalan (§85)", "other", "unknown", "unverified", "unclear",
    "Tolerans altı farkla eşit sayılan iki değer ancak ondalık (Float) girdide olası.", True,
    "domain._num_relation_holds: Eq/Ne yalnız sym_equal ya da kesin eşitlikle karar verir; num_equal'in toleranslı True'su "
    "(Float işlenen) None döner",
    "low", "", "DECISIONS §85",
    "DECISIONS.md:424 'relation_holds_at(Ne) sayısal eşitliği kanıt sayıyor'; repro kaydı yok, bağımsız doğrulanmadı. Edison "
    "certify/domain.py:1584-1595 Eq/Ne hâlâ num_equal ile karar veriyor; ama equiv/numeric.py:546-557 iki kesin sabiti toleranssız "
    "kesin karşılaştırıyor, kalan yol yalnız Float işlenen. Hiçbir wip dalı bu satırları değiştirmiyor.")
add("GAP-WORDPROBLEM", "kalan (§85)", "coverage_loss", "unknown", "unverified", "unclear",
    "Sözel problemde 'x ∈ (0,3)' ya da 'veya' içeren verilen olası.", True, NA, "n/a", "", "DECISIONS §85",
    "DECISIONS.md:424 'wordproblem katmanı ctx.givens() bileşik metin verilenleri okuyamıyor'; DECISIONS §85 d4d satırı bunu "
    "'Kapsama' altında sayıyor (UNKNOWN yönü). Repro yok, bağımsız doğrulanmadı.")
add("GAP-XA", "kalan (§85)", "coverage_loss", "unknown", "open", "unclear",
    "'a = 2 için x^a = 4' biçimli parametreli soru olası; IR yazarı çoğunlukla x² = 4 yazar.", True, NA, "n/a", "",
    "DECISIONS §85", "DECISIONS.md:424; HANDOFF.md:138-146. Sonda (" + P + ", edison): solve x**a = 4, verilen a = 2, {-2, 2} "
    "UNKNOWN (z3_unsupported).")
add("GAP-D4G-BUTCE", "kalan (§85)", "crash_or_timeout", "preexisting", "unverified", "unclear",
    "Ağır SymPy çağrısı gerçek girdide de olabilir; kesilemeyen çağrı takılma demek.", True,
    "her verify çağrısı sandbox'ta sert duvar saatiyle; aşımda UNKNOWN", "low", "", "DECISIONS §85",
    "DECISIONS.md:424 'd4g'nin süre bütçesi işbirlikçi (tek süreç içi çağrı yalnız sandbox'ta kesilebiliyor)'; notlar/saldiri_d4g.txt:13 "
    "(S8 >400 s). d4g 2. tur sert sınır ekledi (answers_equivalent sandbox 40 s, çözüm 300 s); wip/d4b-tur9 _sympy_guards evalf "
    "tavanı bir kök nedeni kapatıyor. HANDOFF V20 listesinde yok (sessiz düşmüş).")
add("GAP-LIMABS", "kalan (V20)", "coverage_loss", "unknown", "open", "unclear",
    "Sağ limiti kısıtla (x > 0) ve evaluate Limit ile kodlamak alışılmadık ama olası.", True, NA, "n/a", "",
    "HANDOFF V20", "HANDOFF.md:138-146; kosular.txt:62 (d4e açıkları). Sonda (" + P + ", edison): evaluate Limit(Abs(x)/x, x, 0) "
    "x positive_real ile 1 CORRECT, kısıt x > 0 ile UNKNOWN (parse_error). Yalnız UNKNOWN yönü.")
add("GAP-LFLOOR", "kalan (V20)", "other", "preexisting", "unverified", "no",
    "Değer doğru; yalnız soruyu yeniden yazma kuralı (§28, ilke 2).", True,
    "iddianın yapısal ağacı hedefin işlemini (floor) içeriyorsa claim_is_not_a_value", "none", "", "HANDOFF V20",
    "notlar/duzeltme_d4h.txt:76 '\\lfloor\\frac{17}{5}\\rfloor yeniden yazımı açık bırakıldı'; HANDOFF.md:138-146. 1aa422f "
    "_structure/AST değişikliği etkilemiş olabilir (ölçülmedi).")
add("GAP-RANK", "kalan (V20)", "crash_or_timeout", "preexisting", "unverified", "unclear",
    "Matris rankı sorusu birinci sınıfta olası; sonuç layer_exception → UNKNOWN (güvenli).", True, NA, "n/a", "",
    "HANDOFF V20", "notlar/duzeltme_d4h.txt:75 'rank Python int döndürür -> layer_exception, ec62a68'de de'; HANDOFF.md:138-146. "
    "1aa422f matris işlemlerini eylemsiz yaptı (etkisi ölçülmedi).")
add("A05", "kalan (§85)", "other", "unknown", "closed_in_branch", "no",
    "Mutasyon düzeneği sorusu; davranış bulgusu değil.", False, "", "n/a", "", "DECISIONS §85",
    "DECISIONS.md:424 (Açık), DECISIONS.md:429: koruma gerekli, (x−8)(x^(2/3)−x^(1/3)+1)=0 öldürücü testi, A05 öldü (9c6fbdb).")
add("TEST-REVIEW", "kalan (§85)", "coverage_loss", "by_d4_fix", "closed_in_branch", "unclear",
    "a = log(8)/log(2) gibi verilen nadir.", False, "", "n/a", "", "DECISIONS §85",
    "DECISIONS.md:424 (birleşimde düşen test_review_constraint_and_given_write_one_value_twice); DECISIONS.md:428 kök neden "
    "Poly log(8) vs Intersection TypeError, certify.base.exact_intersection (9c6fbdb, edison atası).")

ids = [f["id"] for f in F]
assert len(ids) == len(set(ids)), [i for i, c in collections.Counter(ids).items() if c > 1]
c = collections.Counter((f["status"], f["klass"], f["realistic"]) for f in F)
by_status = collections.Counter(f["status"] for f in F)
by_klass = collections.Counter(f["klass"] for f in F)
by_real = collections.Counter(f["realistic"] for f in F)
lines = [f"toplam {len(F)}; durum: " + ", ".join(f"{k} {v}" for k, v in sorted(by_status.items())),
         "sınıf: " + ", ".join(f"{k} {v}" for k, v in sorted(by_klass.items())),
         "gerçekçi: " + ", ".join(f"{k} {v}" for k, v in sorted(by_real.items())),
         "durum x sınıf x gerçekçi: " + "; ".join(f"{s}/{k}/{r} {v}" for (s, k, r), v in sorted(c.items()))]
out = {"findings": F, "counts": " | ".join(lines)}
json.dump(out, open(__file__.rsplit("/", 1)[0] + "/inventory.json", "w"), ensure_ascii=False, indent=1)
print(out["counts"])
print(len(F))

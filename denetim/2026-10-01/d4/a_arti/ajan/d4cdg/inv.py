import json
from collections import Counter

D = "d4/"  # = ed/denetim/2026-10-01/d4/
F = []


def add(id, part, klass, introduced, status, realistic, reason, evidence, severity, source,
        wip_ref="", fc=False, rule="", risk="n/a"):
    F.append({"id": id, "part": part, "klass": klass, "introduced": introduced, "status": status,
              "realistic": realistic, "realistic_reason": reason, "evidence": evidence,
              "severity": severity, "source": source, "wip_ref": wip_ref,
              "failclosed_coverable": fc, "failclosed_rule": rule, "rule_risk": risk})


# ---------------- d4c original ----------------
add("S1", "d4c", "false_accept", "preexisting", "closed_in_branch", "no",
    "cos(50x) gibi değeri 1e-79 olan Bessel integrali ya da |cos x|/10^80 eklentisi yapay; YKS/ilk yıl sorusu değil.",
    "d4/dogrulama.json S1 (fixer yeniden üretti); d4/notlar/duzeltme_d4c.txt:5 (sıfır yalnız sembolik sertifikayla); düzeltme 86361fe/7e2f08d, birleşme ad50fbc -> edison'da (git merge-base: 86361fe edison'un atası).",
    "high", "original-60")
add("S2", "d4c", "false_accept", "preexisting", "closed_in_branch", "no",
    "10^8 genişlikli dar tepe ve 2 + 10^-40 iddiası kod yolunu vurmak için kurgulanmış.",
    "d4/dogrulama.json S2; d4/notlar/duzeltme_d4c.txt:11 (kesin değer yoksa kareleme kabul etmez); 86361fe edison'da. Yakın sınıf (SymPy'nin yanlış kapalı biçimi + kareleme/tolerans) D4C2-YO-2 olarak ayrı kayıtta.",
    "high", "original-60")
add("S3", "d4c", "unjust_reject", "preexisting", "closed_in_branch", "yes",
    "Dirichlet ∫₀^∞ sin x/x = π/2 ve Fresnel/Laplace integralleri ilk yıl üniversite analizinin klasik adımları.",
    "d4/dogrulama.json S3; d4/notlar/duzeltme_d4c.txt:17 (anlamlı basamaksız evalf değer değil -> unknown); 86361fe edison'da.",
    "high", "original-60")
add("S4", "d4c", "crash_or_timeout", "preexisting", "closed_in_branch", "no",
    "3000 terimli Σ x^k/k! = e^x iddiası yapay uzunlukta.",
    "d4/dogrulama.json S4; d4/notlar/duzeltme_d4c.txt:21 (süre sınırlı değerlendirme); random_point _terms_at + 20 s bütçe, 86361fe edison'da.",
    "medium", "original-60")
add("S5", "d4c", "false_accept", "preexisting", "closed_in_branch", "no",
    "Σ_{k=0}^{5000} a^k ve (10,20)'de tanh(100x)=1 kurgulanmış; gerçek soruda 1e-165 altı fark yok.",
    "d4/dogrulama.json S5; d4/notlar/duzeltme_d4c.txt:23 (evalf'in '0.e-168'i sıfır kanıtı değil); 86361fe/7e2f08d edison'da.",
    "high", "original-60")
add("S6", "d4c", "coverage_loss", "preexisting", "closed_in_branch", "unclear",
    "Tek ve içte integrallenebilir tekillikli ∫₋₁¹ x^(-1/3)-türü integral ilk yıl örneklerinde geçebilir.",
    "d4/dogrulama.json S6 (coverage_regression, #14 getirdi); d4/notlar/duzeltme_d4c.txt:27 (simetri + mutlak integrallenebilirlik sertifikası -> CORRECT); 86361fe edison'da.",
    "low", "original-60")
add("D4-ADIM-C", "d4c", "unjust_reject", "preexisting", "closed_in_branch", "yes",
    "Dirichlet/Fresnel adımları gerçek bir çözücünün yazacağı ders kitabı eşitlikleri.",
    "d4/dogrulama.json D4-ADIM-C; d4/notlar/duzeltme_d4c.txt:17 (S3 ile aynı karar); 86361fe edison'da.",
    "high", "original-60")

# ---------------- d4c attack round 1 ----------------
add("D4C1-BULGU-1", "d4c", "unjust_reject", "preexisting", "closed_in_branch", "no",
    "sech²(10^6(x-√2/2)) gibi dar tepe yapay.",
    "d4/notlar/saldiri_d4c.txt:3; kararı kesin aralık zarfı (DECISIONS §85 d4c satırı); d4c tur 2 db7fb6d -> eedd182 edison'da. Zarfın kendi kusurları sonradan D4C3R-RET-1 olarak bulundu.",
    "high", "d4c")
add("D4C1-BULGU-2", "d4c", "unjust_reject", "by_d4_fix", "closed_in_branch", "unclear",
    "Kaydırılmış Gauss/normal dağılım momentleri (∫ x² e^{-(x-60)²/2}) olasılık derslerinde geçebilir; tepe varyantları yapay.",
    "d4/notlar/saldiri_d4c.txt:9 (sonsuz aralıkta zarf tepeyi kaçırıyor, d4c getirdi; ∫_R e^{-(x-100)²} adımı önceden var); d4c tur 2 db7fb6d edison'da (sonsuz aralıkta sayısal ret yok).",
    "medium", "d4c")
add("D4C1-BULGU-3", "d4c", "unjust_reject", "by_d4_fix", "closed_in_branch", "unclear",
    "Bildirilen toleranslı yaklaşık integral cevabı (0.4306, rel_tol 1e-3) sayısal soruda olası ama YKS'de nadir.",
    "d4/notlar/saldiri_d4c.txt:14 (rel_tol yok sayılıyor, eski CORRECT -> yeni INCORRECT); d4c tur 2 rel_tol okur (tolerance_window, e2f2c0b) edison'da; o pencere D4C2-YO-4/RK-E/RK-F'yi doğurdu.",
    "medium", "d4c")
add("D4C1-KAPSAMA", "d4c", "coverage_loss", "by_d4_fix", "closed_in_branch", "unclear",
    "Gudermann tipi ve log(e^x+e^-x) özdeşlikleri üniversite düzeyinde geçebilir.",
    "d4/notlar/saldiri_d4c.txt:16 (5 doğru özdeşlik CORRECT -> UNKNOWN); düzeltme e2579c3 (sertifika önceliği, Gudermann) edison'da.",
    "low", "d4c")

# ---------------- d4c2 (round-2 attack) ----------------
W3 = "wip/d4c-tur3 (tur 3 d9a7bb3; tur 4 c32cdad); wip/birlesik 443e078"
add("D4C2-YO-1", "d4c", "false_accept", "preexisting", "closed_in_wip_only", "no",
    "max(1 + x/10^50) ve tanh(100) gibi 40 basamak altı farklar kurgulanmış.",
    "d4/saldiri/d4c2/bulgular.json YO-1; kararlar_tur3.txt:3; düzeltme 8427b14 (edison'da yok). Benim koşum: max(1+x/10**50,[0,1]) iddia 1 -> edison CORRECT, c32cdad INCORRECT.",
    "high", "d4c2", W3)
add("D4C2-YO-2", "d4c", "false_accept", "preexisting", "closed_in_wip_only", "unclear",
    "SymPy'nin yanlış kapalı biçimi + bildirilen toleransla yanlış yaklaşık cevap; atan(tan x)+174 varyantı gerçek bir toleranslı integral sorusunda olabilir, tepe varyantı yapay.",
    "d4/saldiri/d4c2/bulgular.json YO-2; kararlar_tur3.txt:7; tur 3 düzeltmesi 8427b14 eksik kaldı (kabul yolunu zarfa taşıdı -> D4C3R-YO-1), tur 4 728226f/c32cdad ile kapandı (d4/../scr NOTLAR d4c:241). Edison'da açık.",
    "high", "d4c2", "wip/d4c-tur3 c32cdad (tur 3 tek başına yetmedi)")
add("D4C2-YO-3", "d4c", "false_accept", "preexisting", "closed_in_wip_only", "no",
    "sin(3·10^6·πx) terimi ızgarayı vurmak için kurgulanmış.",
    "d4/saldiri/d4c2/bulgular.json YO-3; kararlar_tur3.txt:13; tur 3 697a025 mekanizmayı kapatmadı (D4C3-YO-B), tur 4 728226f (bütün örnek noktalarında kesin fark) c32cdad'de kapattı.",
    "medium", "d4c2", "wip/d4c-tur3 c32cdad")
add("D4C2-YO-4", "d4c", "false_accept", "by_d4_fix", "closed_in_wip_only", "yes",
    "IR'yi yazan model '%5' için rel_tol: 5 ya da 1 yazabilir; o zaman her iddia (ters işaretli bile) CORRECT oluyor.",
    "d4/saldiri/d4c2/bulgular.json YO-4 (d4c tur 2 tolerance_window getirdi); kararlar_tur3.txt:17 (rel_tol >= 1 biçimce bozuk -> UNKNOWN); düzeltme 8427b14. Benim koşum: ∫₀¹e^{cos x}, rel_tol 1 iddia 100 ve rel_tol 5 iddia 10 -> edison CORRECT, c32cdad UNKNOWN.",
    "medium", "d4c2", W3)
add("D4C2-YO-5", "d4c", "other", "by_d4_fix", "closed_in_wip_only", "no",
    "1 ulp içe yuvarlama; karara etkisi bulunamadı.",
    "d4/saldiri/d4c2/bulgular.json YO-5; kararlar_tur3.txt:20; düzeltme 697a025 (_neg kesin, dışa yuvarlama).",
    "low", "d4c2", W3)
add("D4C2-RK-A", "d4c", "coverage_loss", "by_d4_fix", "closed_in_wip_only", "yes",
    "∫_R e^{-x²} = √π ve normal yoğunluğun integrali klasik ders kitabı sonuçları; edison'da UNKNOWN.",
    "d4/saldiri/d4c2/bulgular.json RK-A; kararlar_tur3.txt:23; düzeltme 697a025 (erf ailesi TTK). HANDOFF V20 'tur 3'te ele alındı'.",
    "medium", "d4c2", W3)
add("D4C2-RK-B", "d4c", "coverage_loss", "by_d4_fix", "closed_in_wip_only", "unclear",
    "∫₀¹ sin x/x gibi uçta kaldırılabilir tekillikli integrallerde yanlış değerin reddi; iddialar (-100) yapay ama sınıf gerçek.",
    "d4/saldiri/d4c2/bulgular.json RK-B; kararlar_tur3.txt:26; 697a025 (uç Taylor kuralı), tur 4 728226f bu kuralı analitiklik kanıtına bağladı (kararlar_tur4.txt:6).",
    "medium", "d4c2", "wip/d4c-tur3 c32cdad")
add("D4C2-RK-F", "d4c", "unjust_reject", "by_d4_fix", "closed_in_wip_only", "no",
    "Negatif rel_tol biçimce bozuk girdi; gerçek IR'de beklenmez.",
    "d4/saldiri/d4c2/bulgular.json RK-F; kararlar_tur3.txt:17; düzeltme 8427b14 (rel_tol <= 0 -> UNKNOWN).",
    "low", "d4c2", W3)
add("D4C2-RK-D", "d4c", "crash_or_timeout", "by_d4_fix", "not_real", "no",
    "Doğrulayıcı gerçek değil dedi: kilitli D3 kararı süre sınırı koymuyor.",
    "d4/saldiri/d4c2/bulgular.json RK-D verdict.real=false; kararlar_tur3.txt:1 ('RK-D gerçek değil: D3 süre sınırı yok').",
    "low", "d4c2")
add("D4C2-RK-C", "d4c", "other", "by_d4_fix", "closed_in_wip_only", "unclear",
    "Kapalı biçimsiz her ağır integralde karar makine yüküne bağlıydı (güvenli yönde UNKNOWN).",
    "d4/saldiri/d4c2/bulgular.json RK-C (nondeterminism); kararlar_tur3.txt:29; düzeltme 697a025 (4000 hücre bütçesi, 120 s yalnız güvenlik durdurucusu).",
    "low", "d4c2", W3)
add("D4C2-RK-E", "d4c", "unjust_reject", "by_d4_fix", "closed_in_wip_only", "unclear",
    "Tolerans sınırındaki yuvarlanmış doğru cevap (göreli hata 9.995e-4, t=1e-3) gerçek sayısal soruda olabilir.",
    "d4/saldiri/d4c2/bulgular.json RK-E (doğrulayıcı 782431c'ye göre 'önceden var' dedi; pencere d4c tur 2'nin e2f2c0b'si, d4c öncesi CORRECT'ti: saldiri_d4c.txt:14) ; kararlar_tur3.txt:17; düzeltme 8427b14 (|c-v|/|v| tek tanım).",
    "low", "d4c2", W3)

# ---------------- d4c3 (round-3 attack) ----------------
W4 = "wip/d4c-tur3 c32cdad (tur 4: 728226f, b99f0ca, c32cdad; tur ölçümü yarım)"
add("D4C3-YO-A", "d4c", "false_accept", "by_d4_fix", "closed_in_wip_only", "unclear",
    "∫₀² arctan(tan x) dx bilinen bir tuzak alıştırması; saf cevap (2) bildirilen toleransla CORRECT oluyordu; YKS'de yok.",
    "d4/saldiri/d4c3/bulgular.json D4C3-YO-A (tur 3 getirdi); kararlar_tur4.txt:6; düzeltme 728226f (Taylor hücresi yalnız yazılı biçimden kanıtlı analitiklikte); scr NOTLAR d4c:241 rep A. Benim koşum: atan(tan x) [0,2] rel_tol 1e-3 iddia 2 -> c32cdad INCORRECT (edison'da da INCORRECT: açık yalnız 443e078/d9a7bb3 hâlinde).",
    "high", "d4c3", W4)
add("D4C3-YO-B", "d4c", "false_accept", "by_d4_fix", "closed_in_wip_only", "no",
    "ε·sin(πNx), N = 8 asalın çarpımı: örnekleyiciye karşı kurgulanmış.",
    "d4/saldiri/d4c3/bulgular.json D4C3-YO-B (tur 3'ün YO-3 düzeltmesi kör noktayı taşıdı); kararlar_tur4.txt:15; düzeltme 728226f (kesin fark bütün noktalarda, nonzero_sign_points).",
    "medium", "d4c3", W4)
add("D4C3-YO-C", "d4c", "false_accept", "preexisting", "closed_in_wip_only", "no",
    "Genişliği 1e-7 olan kısıt aralığı yapay.",
    "d4/saldiri/d4c3/bulgular.json D4C3-YO-C; kararlar_tur4.txt:23; düzeltme 728226f (_inside: nokta kesin olarak alanın içinde). Edison'da açık (önceden var).",
    "low", "d4c3", W4)
add("D4C3R-YO-1", "d4c", "false_accept", "by_d4_fix", "closed_in_wip_only", "unclear",
    "D4C3-YO-A ile aynı kök (arctan(tan x) tuzağı, toleranslı saf cevap).",
    "d4/saldiri/d4c3/bulgular.json D4C3R-YO-1; kararlar_tur4.txt:6 'YO-A = R-YO-1 = R-RET-1'; 728226f.",
    "high", "d4c3", W4)
add("D4C3R-RET-1", "d4c", "unjust_reject", "by_d4_fix", "closed_in_wip_only", "unclear",
    "arctan(tan x) içeren integralin doğru değeri/adımı reddediliyordu; tuzak alıştırmasında doğru çözüm INCORRECT olabilirdi.",
    "d4/saldiri/d4c3/bulgular.json D4C3R-RET-1 (zarf hücresi d4c tur 2 e2f2c0b'den; e03ea1f'te de var -> edison'da açık); kararlar_tur4.txt:6; 728226f sonrası doğru kesin değer UNKNOWN, adım unknown (scr NOTLAR d4c:241).",
    "high", "d4c3", W4)
add("D4C3R-KK-1", "d4c", "coverage_loss", "by_d4_fix", "closed_in_wip_only", "yes",
    "∫_{-2}^{-1} dx/x = -ln 2, ∫ sec x gibi temel ders kitabı integralleri UNKNOWN'a düşmüştü (yalnız tur 3 hâlinde).",
    "d4/saldiri/d4c3/bulgular.json D4C3R-KK-1 (tur 3 getirdi; edison'da CORRECT); kararlar_tur4.txt:26; 728226f (_real_primitive log(-u), polylog); sonda T 0 beklenmeyen (b99f0ca).",
    "medium", "d4c3", W4)
add("D4C3R-SG-1", "d4c", "other", "by_d4_fix", "closed_in_wip_only", "no",
    "Skaler toleranslı görevde küme/aralık ya da karmaşık iddia yazılması gerçekçi değil.",
    "d4/saldiri/d4c3/bulgular.json D4C3R-SG-1 (layer_exception TypeError, ilke 13); kararlar_tur4.txt:31; 728226f + c32cdad (∞ iddia sertifikalı sonlu değere karşı INCORRECT).",
    "low", "d4c3", W4)
add("D4C3R-KK-2", "d4c", "coverage_loss", "by_d4_fix", "closed_in_wip_only", "unclear",
    "Ters sınırlı (∫₁⁰) integral seyrek ama gerçek sorularda geçer.",
    "d4/saldiri/d4c3/bulgular.json D4C3R-KK-2 (zarf kusuru e2f2c0b'den); kararlar_tur4.txt:34; 728226f (clo/chi); rep R ikisi CORRECT.",
    "low", "d4c3", W4)
add("BIRLESIK-1", "d4c", "coverage_loss", "by_d4_fix", "closed_in_wip_only", "unclear",
    "∫₀^∞ e^{-t^(1/3)} dt = 6 (Gamma) üniversite alıştırması olabilir; yalnız d4a + d4c tur 3 birleşiminde UNKNOWN.",
    "d4/kosular.txt 13:29 satırı; DECISIONS.md:450; kararlar_tur4.txt:36; düzeltme 728226f (_exact_conditions odd_root); rep U: 6 CORRECT, 5 INCORRECT.",
    "low", "birlesik 443e078", W4)

# ---------------- d4c fixer-found ----------------
add("D4C-T2-SERI", "d4c", "unjust_reject", "preexisting", "closed_in_branch", "no",
    "e^{-(k-1000)^2} tümseği olan seri yapay.",
    "d4/notlar/duzeltme_d4c.txt:91-92 (kardeş yol taraması: numeric_only seri reddi); düzeltme d03ad51 edison'da.",
    "medium", "duzeltme_d4c (tur 2)")
add("D4C-T2-GEXP", "d4c", "coverage_loss", "by_d4_fix", "closed_in_branch", "yes",
    "∫₀^∞ e^{-x} dx = 1 temel uygunsuz integral.",
    "d4/notlar/duzeltme_d4c.txt:111-112 (CORRECT -> UNKNOWN); düzeltme b2c9182 edison'da.",
    "low", "duzeltme_d4c (tur 2)")
add("D4C-T3-CS", "d4c", "unjust_reject", "preexisting", "closed_in_wip_only", "no",
    "asin(tanh x) = atan(sinh x) görevin örnek listesinde yapay sayılan kurgulanmış özdeşlik.",
    "d4/notlar/duzeltme_d4c.txt:167 (certified_sign sertifikalı değildi, doğru özdeşlik INCORRECT); düzeltme cb3f1d8 (edison'da yok); genel düzeltme d4b tur 10 kararlar_tur10.txt:4.",
    "medium", "duzeltme_d4c (tur 3)", W3)
add("D4C-T3-EQ", "d4c", "other", "by_d4_fix", "closed_in_wip_only", "unclear",
    "atan(x) - atan(x/2) = atan(x/(x²+2)) türü ters trig özdeşliklerinde karar koşudan koşuya değişiyordu (yalnız tur 3 ara hâlinde).",
    "d4/notlar/duzeltme_d4c.txt:179 (SymPy equals rastgele; tur 3'ün çatışma kuralı getirdi); düzeltme ef6b0cd (üç tohum). Edison'da bu kural yok.",
    "low", "duzeltme_d4c (tur 3)", W3)
add("D4C-T4-CS8", "d4c", "unjust_reject", "preexisting", "fix_in_progress", "no",
    "Tetikleyen örnek asin(tanh x) = atan(sinh x) gibi kurgulanmış özdeşlik.",
    "scr/d4/duzeltme/d4c/NOTLAR.md:256 'KAPSAM DIŞI: aynı certified_sign zaafı ilk 8 rasyonel noktadaki yolda sürüyor, düzeltilmedi'; bağımsız doğrulanmadı; d4b9-YO-1 ile aynı kök, kararı d4b tur 10 (kararlar_tur10.txt:4-12, wip/d4b-tur9 9d60d17) bütün certified_sign kullanıcılarına uyguluyor.",
    "low", "duzeltme_d4c (tur 4)", "wip/d4b-tur9 9d60d17 (d4b tur 10, yarım)",
    True, "random_point'in kesin karşı örnek onayında evalf_table dışı fonksiyon (asin, sinh, tanh, erf, atan2, ...) içeren farkın strict-evalf işareti karşı örnek sayılmaz; yalnız aralık aritmetiği ya da kesin sıfır testi, yoksa UNKNOWN", "low")
add("D4C-T4-PI", "d4c", "false_accept", "preexisting", "open", "no",
    "Bütün örnek noktalarda (sabit tohum, irrasyonel kaymalar dahil) sıfır olan fark yalnız örnekleyiciyi bilen saldırganca kurulur.",
    "scr/d4/duzeltme/d4c/NOTLAR.md:216 ('Bilinen sınır (rapor): bütün örnek noktalarda tam sıfır olan özel kurgulanmış fark (Π(x − p_i) gibi) nokta örneklemenin genel sınırıdır'); bulgu değil, bilinen sınır; doğrulanmadı.",
    "low", "duzeltme_d4c (tur 4)", "",
    False, "rastgele nokta uyumu hiçbir yolda kanıt sayılmaz (yalnız sembolik özdeşlik)", "high")

# ---------------- d4d original ----------------
DD = "d4d tur 1 ecb392c -> d540add, tur 2 76d0c87 -> 782431c (edison'un atası)"
add("G1", "d4d", "false_accept", "preexisting", "closed_in_branch", "yes",
    "'0 < x < 3 olmak üzere' gibi zincir/bileşik verilenler YKS'de çok yaygın.",
    "d4/dogrulama.json G1 (A+B doğruladı); d4/notlar/duzeltme_d4d.txt:5; " + DD + "; sonda 340/0.",
    "high", "original-60")
add("G7", "d4d", "false_accept", "preexisting", "closed_in_branch", "unclear",
    "Çelişen verilen/bildirim ancak IR yazım hatasıyla oluşur; log(-1), 0**0 bağlamaları yapay.",
    "d4/dogrulama.json G7 (A+B); d4/notlar/duzeltme_d4d.txt:10 (ir_inconsistent / tanımsız bağlama UNKNOWN); " + DD + ".",
    "medium", "original-60")
add("G8", "d4d", "false_accept", "preexisting", "closed_in_branch", "unclear",
    "Bağlamayla boşalan bölge (x>0, x<a, a=0) yalnız tutarsız IR'de olur; IR yazarı hatası olası.",
    "d4/dogrulama.json G8 (A+B); d4/notlar/duzeltme_d4d.txt:14; " + DD + ".",
    "medium", "original-60")
add("G9", "d4d", "false_accept", "preexisting", "closed_in_branch", "no",
    "x + log(a) - log(a) gibi yalnız parametreyi anan iptal eden terim yapay.",
    "d4/dogrulama.json G9 (A+B, gelenek); d4/notlar/duzeltme_d4d.txt:16; " + DD + ".",
    "medium", "original-60")
add("G10", "d4d", "false_accept", "preexisting", "closed_in_branch", "no",
    "atan1+atan2+atan3 = π ile x > π kurgulanmış kararsızlık.",
    "d4/dogrulama.json G10 (A+B); d4/notlar/duzeltme_d4d.txt:19 (kararsız üyelik ne tutulur ne düşer); " + DD + ".",
    "low", "original-60")
add("TAN-01", "d4d", "false_accept", "preexisting", "closed_in_branch", "no",
    "Σ_{k=1}^{n} ile n = -3 bağlaması yapay; müfredatta ters aralık yok.",
    "d4/dogrulama.json TAN-01 (A+B); d4/notlar/duzeltme_d4d.txt:23; " + DD + ".",
    "high", "original-60")
add("TAN-03", "d4d", "false_accept", "preexisting", "closed_in_branch", "no",
    "G9 ile aynı yapay iptal eden parametre terimi.",
    "d4/dogrulama.json TAN-03 (fixer yeniden üretti); d4/notlar/duzeltme_d4d.txt:16; " + DD + ".",
    "medium", "original-60")
add("TAN-04", "d4d", "false_accept", "preexisting", "closed_in_branch", "unclear",
    "a = 0 ve a > 1 gibi çelişen verilenler yalnız IR yazım hatasıyla oluşur.",
    "d4/dogrulama.json TAN-04; d4/notlar/duzeltme_d4d.txt:10; " + DD + ".",
    "medium", "original-60")
add("TAN-09", "d4d", "false_accept", "preexisting", "closed_in_branch", "unclear",
    "Önceki şıkta bulunan a = 2'yi verilen olarak taşıyan x^a < 4 IR'si çok parçalı soruda olası.",
    "d4/dogrulama.json TAN-09; d4/notlar/duzeltme_d4d.txt:26; " + DD + ". Kalan kapsama (x**a = 4 UNKNOWN) D4D-XA'da.",
    "medium", "original-60")
add("P1", "d4d", "false_accept", "preexisting", "closed_in_branch", "yes",
    "'F(x) = ∫₀ˣ t² dt ise F'(2)' klasik AYT sorusu; IR yazarı x = 2'yi verilen yazabilir.",
    "d4/dogrulama.json P1; d4/notlar/duzeltme_d4d.txt:28 (bağlı/görev değişkeni yerine konmaz, PinnedBoundVariable); " + DD + "; saldiri_d4d.txt:11 pin sızıntısı sağlam.",
    "high", "original-60")

# ---------------- d4d attack ----------------
DD2 = "d4d tur 2 76d0c87 -> 782431c edison'da (duzeltme_d4d.txt:47-52)"
add("D4D-B1", "d4d", "false_accept", "by_d4_fix", "closed_in_branch", "unclear",
    "'x ≠ 6, x < 1 veya x > 5' gibi virgül/veya karışık verilen gerçek soruda yazılabilir.",
    "d4/notlar/saldiri_d4d.txt:3 (d4d kısmen getirdi); karar: aynı düzeyde and/or okunmaz (UNKNOWN); " + DD2 + ".",
    "medium", "d4d")
add("D4D-B2", "d4d", "false_accept", "preexisting", "closed_in_branch", "yes",
    "LaTeX 'x \\notin (-1,1)' verileni gerçekçi.",
    "d4/notlar/saldiri_d4d.txt:5; karar: sabite inen metin okunmaz; " + DD2 + ".",
    "medium", "d4d")
add("D4D-B3", "d4d", "false_accept", "by_d4_fix", "closed_in_branch", "no",
    "'x in {(2, 3)}' gibi demet üyeliği yapay.",
    "d4/notlar/saldiri_d4d.txt:9; karar: gerçel olmayan elemanlı kümeye üyelik okunmaz; " + DD2 + ".",
    "low", "d4d")
add("D4D-B4", "d4d", "false_accept", "preexisting", "closed_in_branch", "no",
    "a < 0 ile x + log(a) - log(a) = 2 yapay iptal eden terim.",
    "d4/notlar/saldiri_d4d.txt:10; karar: parametre koşulu parametrenin bölgesinde (parameter_condition_not_proved); " + DD2 + ".",
    "low", "d4d")
add("D4D-6a", "d4d", "false_accept", "preexisting", "closed_in_branch", "no",
    "Serbest a ile a/a, log(a)-log(a) iptalleri yapay.",
    "d4/notlar/saldiri_d4d.txt:6 (d4d tur 1'in açık maddesi 6a ölçüldü: {2} CORRECT); " + DD2 + ".",
    "medium", "d4d")
add("D4D-6b", "d4d", "false_accept", "preexisting", "closed_in_branch", "unclear",
    "x > 1 ve x < 0 gibi boş ortak bölge yalnız tutarsız IR'de olur.",
    "d4/notlar/saldiri_d4d.txt:6-7 ({} / 0 / {} CORRECT); karar: boş ortak bölge ir_inconsistent; " + DD2 + ".",
    "low", "d4d")
add("D4D-KAPSAMA-ESIT", "d4d", "coverage_loss", "by_d4_fix", "closed_in_branch", "unclear",
    "Aynı değerin iki yazımı (a = 3, a = log(8)/log(2)) seyrek ama olası.",
    "d4/notlar/saldiri_d4d.txt:8,16 (given_binding_undecided); d4d tur 2 same_value; birleşimdeki test düşüşü d4b tur 6 9c6fbdb exact_intersection ile kapandı (DECISIONS.md:428).",
    "low", "d4d")
add("D4D-GCD00", "d4d", "other", "preexisting", "closed_in_branch", "no",
    "gcd(0,0) + 1 bağlaması yapay.",
    "d4/notlar/saldiri_d4d.txt:15; d4d tur 2 (duzeltme_d4d.txt:48 'gcd(0,0)'; DECISIONS §85: gcd(0, 0) geleneği çekimser).",
    "low", "d4d")

# ---------------- d4d residual / small items ----------------
add("D4D-KAPSAMA-KALAN", "d4d", "coverage_loss", "by_d4_fix", "open", "unclear",
    "Serbest parametreli yazılı koşul (x/a = 3, a bildirilmemiş) gerçek parametrik sorularda olabilir; sonuç güvenli yönde UNKNOWN.",
    "d4/notlar/duzeltme_d4d.txt:52 (saldırganın 556 vakası 72 -> 9: 3 beklenti hatası, 5 kapsama, 1 doğru karar); DECISIONS.md:421 'Kapsama: serbest parametreli yazılı koşul, B1 belirsiz metinler, wordproblem in/or'. Bilinen sınır, düzeltme yok.",
    "low", "d4d")
add("D4D-NE", "d4d", "other", "unknown", "unverified", "unclear",
    "Kaynağı ve hâlâ geçerli olup olmadığı belgelenmemiş; edison'da kesin sabitler exact_equal ile karşılaştırılıyor, yalnız Float'lı dal toleranslı.",
    "DECISIONS.md:424 ('relation_holds_at(Ne) sayısal eşitliği kanıt sayıyor'), HANDOFF.md:143 V20; edison src/mathverify/certify/domain.py:1591-1596 (Ne: sym_equal, sonra num_equal) ve equiv/numeric.py:551-561 (kesin sabitlerde exact_equal). Hiç bağımsız doğrulanmadı.",
    "low", "DECISIONS §85 Açık (d4d raporu, G10 bağlamı; kesin değil)", "",
    True, "relation_holds_at'te Eq/Ne kararı yalnız kesin yoldan (sym_equal/exact_equal); Float işlenenli toleranslı eşitlik Ne'yi False, Eq'yi True yapmaz -> None", "low")
add("D4D-WP", "d4d", "other", "preexisting", "unverified", "unclear",
    "Bileşik metin verilenler gerçekçi; wordproblem'in bunları atlayıp pass verip vermediği ölçülmedi.",
    "DECISIONS.md:424 ('wordproblem katmanı ctx.givens() bileşik metin verilenleri okuyamıyor'); HANDOFF.md:143 V20; scr/d4/v/gorev-G7-A/NOTLAR.md:10 (wordproblem._equation_givens). Hiç bağımsız doğrulanmadı.",
    "low", "DECISIONS §85 Açık (d4d raporu)", "",
    True, "wordproblem katmanı ctx.givens()'ten okuyamadığı ya da bileşik (zincir/And/Or/in) bir verilen varsa pass vermez (çekimser)", "low")
add("D4D-XA", "d4d", "coverage_loss", "preexisting", "open", "unclear",
    "a = 2 verilmişken x**a = 4 gibi parametrik IR olası; sonuç güvenli yönde UNKNOWN (eskiden haksız INCORRECT'ti).",
    "DECISIONS.md:424 ('x**a = 4 (a = 2 verilen) ana denklem bağlamayla yeniden yazılmıyor (UNKNOWN)'); HANDOFF.md:143 V20; TAN-09'un kalan kapsaması.",
    "low", "DECISIONS §85 Açık (d4d raporu)")

# ---------------- d4g original ----------------
DG = "d4g tur 1 07deafd..c30e134 (84673a3) edison'da"
add("D4-ADIM-A", "d4g", "false_accept", "preexisting", "closed_in_branch", "unclear",
    "log(x²) = 2 log x klasik çözücü hatası, ama yanlışlığın görüldüğü öncül bölgesi (x > -1/1000) kurgulanmış.",
    "d4/dogrulama.json D4-ADIM-A (fixer yeniden üretti 4/4); d4/notlar/duzeltme_d4g.txt:11 (beyaz liste kapısı); " + DG + ".",
    "medium", "original-60")
add("D4-ADIM-B", "d4g", "false_accept", "preexisting", "closed_in_branch", "no",
    "İddiaya Sum(0, (k, 1, n-5)) eklemek ret geri çekmesini atlatmak için kurgulanmış.",
    "d4/dogrulama.json D4-ADIM-B (A yeniden üretti, B yarım); d4/notlar/duzeltme_d4g.txt:20; " + DG + "; iç içe atlatma D4G-B'de.",
    "high", "original-60")
add("D4-ADIM-D", "d4g", "false_accept", "preexisting", "closed_in_branch", "unclear",
    "0 ≤ n ≤ 11 iken n!/(n-1)! = n adımı (n = 0'da tanımsız) kombinatorik çözümde yazılabilir.",
    "d4/dogrulama.json D4-ADIM-D; d4/notlar/duzeltme_d4g.txt:29; " + DG + ".",
    "low", "original-60")
add("D4-ADIM-E", "d4g", "unjust_reject", "preexisting", "closed_in_branch", "yes",
    "[1,3]'te |x| + x² ekstremumunda d/dx = 1 + 2x adımı tipik doğru çözüm.",
    "d4/dogrulama.json D4-ADIM-E; d4/notlar/duzeltme_d4g.txt:36 (görev aralığı compute öncülü); " + DG + ".",
    "medium", "original-60")
add("D4-ADIM-F", "d4g", "crash_or_timeout", "preexisting", "closed_in_branch", "yes",
    "'x³ - 3x + 1 = 0 ise x³ - 3x kaçtır' tipi soru YKS'ye çok benzer; tek adım 166-390 s sürüyordu.",
    "d4/dogrulama.json D4-ADIM-F; d4/notlar/duzeltme_d4g.txt:40 (adım bütçesi 60 s, kapalı olmayan bölge örneklenmez); " + DG + ".",
    "medium", "original-60")
add("D4-ADIM-H", "d4g", "false_accept", "preexisting", "closed_in_branch", "no",
    "n < 0, n > -4 altında Σ_{k=1}^{n} k Karr geleneğine dayanır; müfredatta yok.",
    "d4/dogrulama.json D4-ADIM-H; d4/notlar/duzeltme_d4g.txt:43; " + DG + ".",
    "low", "original-60")
add("D4-ADIM-J", "d4g", "unjust_reject", "preexisting", "closed_in_branch", "unclear",
    "x² = 4 altında sqrt(x³) = x·sqrt(x) adımı bir çözücünün yazabileceği bir adım.",
    "d4/dogrulama.json D4-ADIM-J; d4/notlar/duzeltme_d4g.txt:48 (yazıldığı biçimde tanımsız nokta karşı örnek değil); " + DG + ".",
    "low", "original-60")
add("TAN-11", "d4g", "false_accept", "preexisting", "closed_in_branch", "no",
    "x/x + sqrt(y) - sqrt(y) = 1 kurgulanmış.",
    "d4/dogrulama.json TAN-11; d4/notlar/duzeltme_d4g.txt:29; " + DG + ".",
    "low", "original-60")

# ---------------- d4g attack ----------------
DG2 = "d4g tur 2 39c3683..0120211 -> 195e183 edison'da; saldırgan vakaları 20/144 -> 0 (duzeltme_d4g.txt:91)"
add("D4G-Z", "d4g", "unjust_reject", "preexisting", "closed_in_branch", "yes",
    "'x < 0 durumunda |x| = -x' vaka ayrımı YKS çözümlerinde çok yaygın.",
    "d4/notlar/saldiri_d4g.txt:16 (Z1/Z2/Z4 REFUTED -> INCORRECT); karar 1 duzeltme_d4g.txt:74; " + DG2 + ".",
    "medium", "d4g")
add("D4G-S", "d4g", "false_accept", "preexisting", "closed_in_branch", "no",
    "1 + log(1 + exp(-exp(10x))) = 1 kurgulanmış.",
    "d4/notlar/saldiri_d4g.txt:7 (S1/S3/S4/S6 VERIFIED); karar 2 duzeltme_d4g.txt:74; d4c ile ad50fbc'de zaten kapalıydı; " + DG2 + ".",
    "medium", "d4g")
add("D4G-U", "d4g", "false_accept", "preexisting", "closed_in_branch", "no",
    "(1+t)² = 1+2t, t ~ 1e-104 kurgulanmış.",
    "d4/notlar/saldiri_d4g.txt:10 (U1/U3/U4/V VERIFIED); karar 3 (noktalarda kesin uyum); " + DG2 + ".",
    "medium", "d4g")
add("D4G-B", "d4g", "false_accept", "preexisting", "closed_in_branch", "no",
    "İç içe Sum(Sum(0)) ve üç aralık sembollü dolgu kurgulanmış.",
    "d4/notlar/saldiri_d4g.txt:5,14 (B1/B5/B14-16 ret geri çekiliyor); karar 4 (_neutralized, _claim_reading_free); " + DG2 + ".",
    "medium", "d4g")
add("D4G-S8", "d4g", "crash_or_timeout", "preexisting", "closed_in_branch", "no",
    "t = e^{-e^{e^x}} kurgulanmış.",
    "d4/notlar/saldiri_d4g.txt:9,12 (>400 s, bütçe kooperatif); karar 5 (sandbox 40 s, çözüm başına 300 s; deterministic.py:42,62 edison'da); " + DG2 + ". Kalan kooperatiflik D4G-BUTCE'de.",
    "medium", "d4g")
add("D4G-Q", "d4g", "false_accept", "preexisting", "closed_in_branch", "unclear",
    "'x² + y² = 0 ise' klasik öncül, ama o öncül altında x/x = 1 adımı tuhaf.",
    "d4/notlar/saldiri_d4g.txt:18 (Q4/Q6-8/Q10 VERIFIED); karar 6 (_proved_on_system); " + DG2 + ".",
    "low", "d4g")

# ---------------- d4g residual ----------------
add("D4G-BUTCE", "d4g", "crash_or_timeout", "preexisting", "unverified", "unclear",
    "Süreç içi tek SymPy çağrısı bütçeyi aşabilir; gerçek girdide görülüp görülmediği ölçülmedi.",
    "DECISIONS.md:424 ('d4g'nin süre bütçesi işbirlikçi (tek süreç içi çağrı yalnız sandbox'ta kesilebiliyor)'); HANDOFF V20'de artık yok (sessizce düşmüş); d4b tur 9 _sympy_guards (evalf <= 2**16 bit) ana asılma kökünü hafifletti (DECISIONS.md:454). Bağımsız yeniden ölçülmedi.",
    "low", "DECISIONS §85 Açık (d4g raporu)", "",
    True, "verify çağrısının tamamı süreç düzeyinde sert süre sınırıyla (alt süreç, aşımda UNKNOWN); kilitli D3 'süre sınırı yok' ile çelişir, kişi kararı gerekir", "low")

assert len({f["id"] for f in F}) == len(F)
c = Counter((f["status"], f["klass"], f["realistic"]) for f in F)
st = Counter(f["status"] for f in F)
lines = [f"toplam {len(F)}; durum: " + ", ".join(f"{k} {v}" for k, v in sorted(st.items()))]
for s in sorted(st):
    parts = [f"{k}/{r} {v}" for (ss, k, r), v in sorted(c.items()) if ss == s]
    lines.append(f"{s}: " + ", ".join(parts))
counts = " | ".join(lines)
print(counts)
json.dump({"findings": F, "counts": counts}, open(__file__.replace("inv.py", "inv.json"), "w"), ensure_ascii=False, indent=1)

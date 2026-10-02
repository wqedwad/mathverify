# d4/sifir NOTLAR
- başlangıç: kopyalar hazır (yeni=eb3bccc, eski=aa67b20)
- sonda altyapısı: sonda/ortak.py (ir/sol/main_run), sonda/kos.sh yeni|eski script
- BULGU F1 (adayı, doğrulandı uçtan uca): definite_integral ∫_0^{2π} e^{cos x} cos(50x) dx, iddia 0 → yeni CORRECT, eski INCORRECT.
  Gerçek değer 2π I_50(1) ≈ 1.8e-79 ≠ 0. Kök: definite_integral_is_zero yalnız sayısal (80 basamakta 1e-70·S sınırı), SymPy kesin değer yoksa okN=zero=True → CORRECT.
  Ayrıca definite_integral_is_zero: 1e60·sin x + 1e-12 → True (S büyük, değer 2e-12) — görevde converged değil, ama checked_forms'ta?
- p1_int (47 durum, iki ağaç) bitti. Yeni CORRECT/eski INCORRECT: A1 (e^cos cos50x [0,2π]), A1b ([0,π]), A1g (iddia "0.0"), A3/A3b (tek+1e-80/1e-75). Gerçek: 2π I_50(1)=1.8439e-79 (mpmath 80 bsm).
  A1i: yanlış adım "∫...=0" eski refuted, yeni unknown; çözüm CORRECT.
- BULGU F2 (önceden var): kesin değeri SymPy'de yok → okN=num_equal(claimed,val,rel_tol=rel_err≥1e-25) gevşek: ∫_{-1}^{1}(sin(x^5)e^{cos x}+1)dx için iddia 2+10^-40 eski ve yeni CORRECT.
- kapsama: B5 ∫_{-1}^{1} sign(x)/sqrt|x| = 0: eski CORRECT, yeni UNKNOWN (§84'te yok?) — incelenecek.
- iyileşme: B6 (sin50x, cos7x cos3x, sin x 100π...) eski UNKNOWN yeni CORRECT; B9 eski INCORRECT yeni UNKNOWN.
- p2_num (20 doğrudan) + p3_spike (17 durum, iki ağaç). BULGU F3 (önceden var): SymPy kesin değer bulamayınca tanh-sinh tek başına karar; dar tepe (e^{-1e8(x-1/3)^2}) kaçırılıyor, err=0, converged:
  ∫_0^1 (1 + e^{-1e8(x-1/3)^2} e^{cos x}) dx iddia 1 → eski ve yeni CORRECT (gerçek ≈1.00046). ∫_{-1}^{1}(tek+tepe) iddia 0 iki ağaçta CORRECT. 2+1e-40 (F2) de aynı kök: birleştir.
  S9b (log|x|/sqrt|x| + tek + 8 = 0): eski INCORRECT (haksız) → yeni UNKNOWN (iyileşme).
- p4_fam (25, iki ağaç): F1 ailesi yeni CORRECT: e^cos cos{50,55,60}x, e^sin cos60x, cos(cos x) cos60x [0,2π] iddia 0 (eski hepsi INCORRECT).
  F1 checked_forms varyantı (SymPy |cos| yanlış 0 + küçük gerçek değer): evaluate Integral(x + Abs(cos(x))/10**80,(x,-1,1)) iddia 0 yeni CORRECT (eski UNKNOWN); adım "...=0" yeni verified (eski refuted); definite_integral iddia 0 yeni CORRECT (eski UNKNOWN).
  Doğru değer 2*sin(1)/10**80 iddiası iki ağaçta INCORRECT (haksız red; yeni kodda nedeni sıfır sınamasının SymPy'nin yanlış 0'ını onaylaması).
- p5_sum (45, iki ağaç): N4/N6 iyi. Yanlış onay yok. Uzun toplamda yanlış iddia UNKNOWN (P9b/P11/P12; bütçe 2 nokta büyük n'de tükeniyor) - güvenli, bulgu değil. E3 >2000 terimli sıfır toplam UNKNOWN (bilinen §76 i).
- p0d: zero_test_battery Held formları hesaplamıyor (20 durum) - F9 baypası yok.
- p6_f9 başlatıldı (45 durum).
- Fikir: adımda tepe (spike) → _integrals_refute sayısal değerle doğru adımı çürütür (haksız red, önceden var?) → p7.
- p6_f9 (45, iki ağaç): F9'da yeni yanlış onay bulunmadı. H (karmaşık değerli kapalı integral) çökme yok. I7 (limit, a=2 sabit) eski UNKNOWN → yeni CORRECT doğru.
- p7_step (22): K6c yanlış adım "∫(x+|cos|/1e80) = 0" yeni verified (eski refuted) → F1 varyantı. K6b doğru adım iki ağaçta refuted (haksız; F1 kökü yeni kodda).
- p0e/p0f: forms._numeric sonsuz aralıkta evalf'in anlamsız "0.e+107", "1.6" değerlerini 40 basamak sayıp tol 1e-15 veriyor. → _integrals_refute doğru adımı çürütebilir (Dirichlet π/2). p8_inf başlatıldı.
- p8_inf (22, iki ağaç): BULGU F4 (önceden var, haksız red): sonsuz aralıklı doğru integral adımları refuted → doğru çözüm INCORRECT, iki ağaçta aynı:
  ∫_0^∞ sin x/x = π/2 (compute ve eq), 2∫=π, ∫ sin³x/x = π/4, Fresnel sin(x²)=√(2π)/4, ∫cos x/(1+x²)=π/(2e), ∫sin²x/x²=π/2, ∫e^{-x/100}cos x=100/10001, ∫ sin x sin3x/x²=π/2, ∫cos x/√x=√(π/2); definite_integral görevinde de (L17).
  Kök: forms._numeric sonsuz aralıkta sp.N(Integral,40) çıktısını ('0.e+107', '1.6', '0.58') 40 basamaklı değer sayıyor, tol 1e-15; _integrals_refute bununla çürütüyor.
- DİKKAT: pkill -f kendi kabuğumu öldürdü (çıkış 144) — PID ile durdur.
- p9_trunc: T1 (simp Sum x^k/k! 0..3000, iddia exp(x)) iki ağaçta >6 dk takılma. faulthandler: random_point._definite_nonzero_difference → sp.N(dp,30) ana süreçte → Sum.euler_maclaurin. BULGU F5 adayı (crash/takılma, önceden var).
  sonda/toplu.sh + tek.py ile tek tek (150 s sınır, 4 paralel) koşuluyor → p9b.log
- F1 repro (repro/F1.py) yeni: CORRECT×3, evaluate CORRECT, yanlış adım verified, doğru adım refuted; eski: INCORRECT×3, UNKNOWN, refuted, refuted.
- BULGU F6 (önceden var, YANLIŞ ONAY): simplify Sum(a**k,(k,0,5000)), a∈(-1/2,1/2) kısıtıyla, iddia 1/(1-a) → iki ağaçta CORRECT (gerçek (1-a^5001)/(1-a)). Kök: >2000 terimli toplam yazılmıyor, random_point sayısal uyum + _definite_nonzero_difference evalf anlamlı bit bulamıyor → True.
- p9b/p10: F6 varyantları iki ağaçta CORRECT: T2, T9 (Σ k a^k 0..2500 → a/(1-a)^2), V2 (a∈(0,1/2)), V3 (Σ_{1}^{2001} a^k → a/(1-a)), V4, V5 (evaluate). Adım "Sum(...)=1/(1-a)" unknown (verified değil).
  T2c (1500 terim): eski CORRECT → yeni UNKNOWN (yeni kod ≤2000'de kapattı). Mekanizma (p0k): sp.N(Sum(a**k,(k,0,5000)) - 1/(1-a)) = 0.e-168 (_prec 1) → "anlamlı bit yok = özdeşlik" varsayımı.
  F5: T1 iki ağaçta >150 s.
- repro/F1,F2,F4,F5,F6.py yazıldı. p12_cancel (genelleme: tanh(100x)=1 vb., x kısıtlı) çalışıyor. p11_dos yazıldı (henüz koşmadı).
- p12_cancel (14, iki ağaç): BULGU F7 (önceden var, YANLIŞ ONAY, F6'yı kapsar): random_point_equal sayısal uyum + _definite_nonzero_difference'ta evalf'in "0.e-N" (anlamlı bitsiz) sonucu özdeşlik sayılıyor; iptal gerektiren fark evalf'in erişiminin altındaysa CORRECT:
  tanh(100x)=1 (x∈(10,20)), sqrt(1+x²/10^600)=1, cos(x/10^300)=1, exp(x/10^600)=1, atan(10^600x)=π/2, (1+10^-300)^x=1, log(1+x/10^600)=0, 1/(1-e^{-1000x})=1, sqrt(x²+e^{-1000})=x — hepsi iki ağaçta CORRECT.
  docs/ARCHITECTURE.md:108 "gerçek bir fark ~100 bit taşır" varsayımı yanlış.
- p13 (F7 görev varyantları, iki ağaç aynı): türev tanh(100x) iddia 0 CORRECT; compute adımı "tanh(100*x) = 1" verified; evaluate CORRECT; simp x*tanh(100x)=x CORRECT.
- p11: D1/D3 eski CORRECT → yeni UNKNOWN (F9 bilinen kapsama §84(9)); D2 yanlış iddia eski UNKNOWN → yeni INCORRECT.
- p13 kalan: nokta görevleri (teğet, türev-noktada, limit) kesin → doğru karar. F7 yalnız ifade özdeşliği yolunda.
- p14_lim (18 limit, eq adımı _limits_refute) toplu.sh ile başlatıldı → p14.log
- SIRADAKİ: bulgular.json taslağı; repro'ları iki ağaçta koş; kapsama/not_covered yaz.
- p15 (19, iki ağaç): KAPSAMA GERİLEMESİ (§84'te yok): içte integrallenebilir tekillikli tek fonksiyonun sıfır integrali eski CORRECT → yeni UNKNOWN: ∫_{-1}^{1} sign(x)/sqrt|x| (definite_integral ve evaluate), sign(x)|x|^{-2/3}. Neden: sıfır merdiveninde 30 basamak hata tahmini 2e-17 > 1e-20·S.
  İyileşme: R11 log x+1, R14 sin(1000x) yeni CORRECT.
- repro koşuları: F2, F4, F6, F7 iki ağaçta beklenen; F4'te e^{-x/100}cos x örneği yük altında belirsiz (zaman aşımı) → repro'dan çıkarıldı, yerine sin³x/x.
- p16 (8): erf/besseli iddiada okunmuyor (skipped/UNKNOWN). N3b (1+tepe·e^cos iddia 1) iki ağaçta CORRECT (F2).
- p17 (20, F9 ek): yeni yanlış onay yok; O8 eski kodda yanlış adım verified idi, yeni unknown (iyileşme).
- p18 (süre, 5 durum) koşuyor → p18.log
- SONUÇ TASLAĞI: S1=F1 (yeni, yüksek), S2=F2 tepe+tolerans (önceden), S3=F4 sonsuz aralık haksız red (önceden), S4=F5 takılma (önceden), S5=F6+F7 evalf anlamlı bitsiz sıfır (önceden, yüksek), S6 kapsama gerilemesi (sign/sqrt|x|).
- p10 kalan: V7, V9, V10, V11 (1/(1-a)+a^6000), V12 iki ağaçta CORRECT (S5). V14 (kısıtsız a) INCORRECT (doğru).
- p11: D6 (Σ x^k/k!, 0..2001, iddia exp(x)) iki ağaçta >120 s; T1 ile aynı satır (random_point.py:734 sp.N(dp,30), ana süreçte). S4.
- p18 (5): süre artışı ~1.4x, takılma yok.
- repro/S5.py yeni: beklenen (CORRECT×4, adım verified).
- bulgular.json yazıldı (S1–S6)
- SON: StructuredOutput gönderiliyor (S1–S6, ~912 sonda)

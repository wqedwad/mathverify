# NOTLAR adim denetimi (d4)
- başlangıç: kopyalar hazır (yeni=eb3bccc, eski=aa67b20)

## p1 (33 durum, sonda/p1_region.py)
- BULGU A (false_accept, #14): bölge yolu (_on_premises region) rastgele noktayla verified veriyor; analitik olmayan
  ama _NONSMOOTH'ta olmayan fonksiyonlar (asin(sin x), acos(cos x), binomial(n,200) tam sayı) dar bölgede yanlış.
  R1 0<x<1.58 asin(sin(x))=x verified (eski refuted); R7 cevap 4 ile CORRECT (eski INCORRECT); R11 kısıtla CORRECT;
  R5 n>5 binomial(n,200)=0 verified (eski refuted); R17 asin(sin(x/64))=x/64, 0<x<101 verified.
- Sonlu yol: transandantal öncülde solveset ConditionSet -> unknown (güvenli). F1-F16 doğru.
## p2+p3 (31+20 durum)
- BULGU B (false_accept/kaçırma, #14 parça 11): _refuted_where_backwards, ret noktası okunamazsa (pt None) ya da nokta
  n'yi içermezse (doit Sum'ı n'ye katlayıp karşılaştırmadan n'yi düşürünce) reddi geri çeker. Herhangi bir yanlış compute
  adımına "+ Sum(1, (k, 1, n)) - n" (n integer) eklemek adımı unknown, doğru cevaplı çözümü CORRECT yapar (eski INCORRECT).
  C3 "2 + 2 + Sum(1,(k,1,n)) - n = 5" CORRECT; C18/C19 n >= 0 verilmiş/kısıt olsa bile (ters nokta yok) CORRECT.
  Varyantlar: antiderivative (C1), limit DNE (B3,B4), türev yok (B5), matris (B10), Product (C8,C9), LaTeX (C12),
  diff (C10), kapalı integral (C11). n positive_integer / nonneg_integer ise ret kalıyor (sembol varsayımı karar veriyor).
## p4 (120) + p5 (33): limit/integral
- _limits_refute iyileştirme: eq DNE/oo çelişkileri artık refuted (eski unknown) — doğru.
- BULGU C (unjust_reject, ÖNCEDEN VAR, #14 _integrals_refute'te korunmuş): sonsuz aralıklı integralde _numeric
  sp.N(Integral,40) çıktısını ('-0.e+0', '0.58', '1.6') 1e-15 güvenle değer sayıyor. Doğru Dirichlet ∫0^∞ sin x/x = π/2,
  ∫ sin²/x² = π/2, ∫ cos x/(1+x²) = π/(2e), Fresnel adımı refuted; I90 doğru çözüm INCORRECT (eski de aynı).
  Yanlış "= 0" refuted değil (unknown). ∫1/x (1,∞) = oo refuted (gelenek).
## p6 (61 durum)
- A varyantı: 21 noktalı Range (_MAX_INSTANCES=20 üstü) bölge yoluna düşüyor, rastgele örnekle verified:
  F21 1<=n<=21 binomial(n,21)=0 verified, G21 Product(n-k,(k,1,20))=0 verified (n=21'de yanlış; eski refuted).
- E7 case x=2 + given x²=4: doğru x**3=8 refuted (önceden var; §84(11) "unknown kalır" diyor, aslında refuted).
- Nested/ters aralık düzeltmeleri doğru (N1-N19).
## p7 (6) zamanlama: en çok ~10 s, takılma yok.
## p8 (23): B her alan türünde: "+ Sum(0, (k, 1, n - 5))" (her gelenekte 0) n positive_integer/nonneg/integer, hatta x real
  ile yanlış compute adımı unknown, çözüm CORRECT (eski INCORRECT). evaluate Sum(k,(k,1,10)) cevap 55 + yanlış adım CORRECT.
## p9 (21): A varyantları: log(x**2)=2*log(x) [x>-1/1000] verified + çözüm CORRECT (eski INCORRECT);
  sqrt(x**2-2x+1)=x-1 [x>0.99] verified; sqrt(x**3)=x*sqrt(x) [x>-1/1000] verified. atan(x)+atan(1/x)=pi/2 [x>1] artık verified (iyileşme).
## repro/ yazıldı ve iki kopyada koşuldu: A_region_random.py (yeni CORRECT x4, eski INCORRECT x4),
  B_backwards_withdrawal.py (yeni padded/antiderivative CORRECT, eski INCORRECT), C_infinite_integral.py (ikisinde de INCORRECT).
  sonda/indep.py mpmath ile bağımsız doğrulama tamam.
## p10 (18): eq/compute ters aralık; "compute n<0,n>-4: Sum(k,(k,1,n)) = n(n+1)/2" verified (ikisinde de; özdeşlik doğrulaması
  Karr'a dayanıyor; §80 ile çelişki, önceden var, düşük). p11 (38) iki taraflı uç limitleri: hepsi unknown (doğru).
## p12 (42) tek kök: düzgün.
## SIRADAKİ: fark fuzz (bölge/sonlu yol, bağımsız doğruluk), sonra bulgular.json + StructuredOutput.
## fuzz1 (250, seed 11, iki kopya): yeni FALSE_VERIFIED 5 (binomial 21 nokta = A; factorial(n)/factorial(n-1)=n aralıkta 0 dahil = D),
  TRUE_REFUTED 3 (sqrt(x**3)=x*sqrt(x) negatifte iki taraf da karmaşık: önceden var); eski 7/50. #14 haksız reddi 50->3 indirdi.
## p13 (26) BULGU D (önceden var, #14 V16 B(4) eksik): _undefined_at_premises yalnız tek sembol + FiniteSet(<=12) ya da tam pin;
  Range (tam sayı aralığı) hiç okunmuyor: -1<=x<=10 tam sayı, "x/x = 1" verified (x=0'da tanımsız); 2 sembol x^2=4,y^2=1
  "sqrt(x)**2 + sqrt(y)**2 = x + y" verified; 0<=n<=11 "factorial(n)/factorial(n-1)=n" compute verified.
## p14+p15 (14) BULGU E (unjust_reject, önceden var; #14 _on_premises havuzu görev aralığını almıyor): extremum/definite_integral
  görevinde aralıkta doğru compute adımı (diff(Abs(x)+x**2,x) = 1+2x [1,3]; Integral(Abs(x),x) = x**2/2 [0,2]; Abs(x)=x)
  aralık dışı noktada refuted, doğru çözüm INCORRECT; aynı iddia eq adımı olunca unknown (pencere okunuyor). Eski de aynı.
## dbg_r11b: A'nın kökü önceden var: bildirilmiş kısıt (x > 0, x < 1.58) ya da positive_integer ile eski kod da CORRECT
  (binomial(n,200)=0 n pozitif tam sayı: ikisi de verified). #14 yeni tetikleyiciler: verilenlerden bölge (_on_premises),
  21+ noktalı sonlu küme, zincir kısıt (N5 düzeltmesiyle uygulanıyor).
## p16 (14) Float/matris/LaTeX: düzgün (Float parse'ta kesirleşiyor).
## p17 (devam ediyor): BULGU F? takılma: öncül x**3 - 3*x + 1 = 0 ile tek compute adımı yeni kodda 282 s ve 211 s (eski <1 s).
  run.sh 600 s'de kesildi. Profil çıkarılacak. Eski kodda [tan(x) = x] Abs(x) = x verified (yanlış onay, önceden var).
## BULGU F (crash/takılma, #14): x**3-3x+1=0 öncülü, compute "x**3 = 3*x - 1": 166-390 s, hepsi süreç içinde
  (sandbox süre sınırı yok): _on_premises bölge yolu -> _check_compute(doms=Intersection(FiniteSet(casus radikalleri), Reals))
  -> random_point.sample_points -> _sample_one(Intersection) -> dom.contains(p) (is_real kararı) x ~3000. cProfile: sonda/prof_cubic2.py.
## p18: doğal x**3-3x+1=0, compute "x**3 - 3*x = -1": yeni 194 s CORRECT/unknown; eski 23 s INCORRECT/refuted (eski haksız red).
## p17b: tan(x)=x altında Abs(x)=x verified (eski de) -> kök: domain_for trig koşulunda solveset tek periyot [0,2π) döndürüyor.
  x**(1/3)=x altında Abs(x)=x verified (yeni; eski refuted): solveset esas kökle {0,1}, gerçel küp kök geleneğinde -1 de kök (sınırda; not).
## BULGU G (false_accept, önceden var, açı dışı ama adım alanını etkiliyor): domain_of tan(x) -> [0,2π)\{π/2,3π/2} CORRECT,
  log(sin x) -> (0,π) CORRECT, 1/sin x -> (0,π)∪(π,2π) CORRECT (iki kopyada). Adımda: evaluate tan(x) altında "x >= 0", "x < 7"
  verified; simplify tan(x)*cos(x) = sin(x) + yanlış adım Abs(x)=x CORRECT.
## Kalan: repro D,E,F,G,H yaz; bulgular.json; StructuredOutput.
## p21: G cevap düzeyinde de: solve_inequality log(sin x) < 0 -> (0,π/2)∪(π/2,π) CORRECT; count_integers sin x > 0 -> 3 CORRECT
  (ikisi de iki kopyada). x**(1/3) = x için {-1,0,1} ve {0,1} ikisi de INCORRECT (açı dışı, not).
## dbg_cbrt: evaluate (-8)**(1/3): hem -2 hem 1+sqrt(3)*I CORRECT (iki kopyada; açı dışı, gelenek -> UNKNOWN olmalı). K ile birleştir.
## repro: A,B,C,D,E,F(p18 ile ölçüldü),G,H,I,J,K hepsi iki kopyada koşuldu. Şimdi bulgular.json + çıktı.
## bulgular.json yazıldı (11 bulgu)

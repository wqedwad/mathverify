# wip/son-ayristirici üçüncü tur (EK 9) — düzeltici raporu özeti (23 Ekim ~10:30)
HEAD d1a1ee2. Commit'ler (d9527f7 sonrası): 77f9cfd (maddeler), a21b494 (kapanan '|'), 4976346 (mutasyon J13), d1a1ee2 (ek-fiil kısıtı).
- YO-T2-1 kapandı: argüman tarayıcısı '(', '\left(', '|…|' gruplarını bütün okur; sayıdan sonra gelen grup argümanın parçası (latex2sympy ve ders
  kitabının A sin B(x−C) yazımı: '\sin 2(x+\frac{\pi}{4})' = sin(2x+π/2)); harften sonra gelen grup iki okumalı → claim_ambiguous_juxtaposition.
- YO-T2-3 = RK-T2-1 kapandı: argümandan sonra e^…, \sqrt, \frac ayrı çarpan; ayraçlama latex2sympy'den yalnız işleçte ayrılır; çarpan izleyen
  argümanda iki okuma karşılaştırılır, ayrışırsa iddia okunmaz ('\sin 2\frac{x}{3}').
- RK-T2-2 kapandı (iç içe aralıklar tek geçişte). RK-T2-3 kapandı (x(1) kurulmaz; ad alanındaki değişken fonksiyon gibi uygulanırsa LaTeX okunmaz;
  52 s → 0,1–0,7 s UNKNOWN). YO-T2-2 kapandı (rasyonel öncüllerin karmaşık çözümü yoksa sonuç verilmez, sabit kat kuralı da yok;
  compute step_reading_undecided). RK-T2-4 kapandı (kümesi, aralığı, kökleri, çözümleri, değerini alır, eder, çıkar, oluyor; ek-fiil yalnız nötr
  kökte: '5 tanedir' CORRECT, '5 derecedir', '5 muhtemeldir' UNKNOWN).
- Kardeşler: kapanan '|' argümanı bitirir (|\cos x|; test_d4_d4h_ayristirici testi); ek-fiil kuralı nötr köklerle sınırlı.
- Kararla değişen beklentiler: 'x/(x−1)=1' altında compute 'x = x − 1' UNKNOWN; harften sonra grup gelen ders kitabı adımları
  ('\cos x(2\sin x − 1) = 0') UNKNOWN (d9527f7'de x(…) tanımsız fonksiyon okumasıyla CORRECT'tiler; iki okumalı adım CORRECT'i engeller);
  '\ln 2|x|' ln(2|x|).
- Ölçüm (d9527f7 → d1a1ee2): ayrıştırıcı sondası 589 vaka (L 52, M 7, N 28 yeni) 67 → 0 (0e93ed5'te 257); test 361 (65 düşüyordu; 0e93ed5'te 193);
  mutasyon 87/87; fark 558: 0 (dökümler aynı); kap 68/1/20 aynı; derlem temizleyicisi 1986: 0; adversaryal 100/7115: flipped 0, accepted_wrong 0;
  bütün takım 5239 geçti/101 atlandı/4 staged_check (git'siz kopya); parça sondaları hepsi 0; adım 407: 0 değişim; sayısal 341: tek değişim C3
  sin vakası tohuma bağlı (0e93ed5 tabanlı ağaçlarda; birleşikte kararlı UNKNOWN). Denetçi sondaları: ret-kapsama uyum 209 → 247/363; yanlış onay
  sondalarında 35 değişim, hepsi beklenen yönde. Deneme birleşimi d6e3d65: çakışmasız; son sondaları ayristirici 589, adım 407, sayısal 356,
  kalkülüs 220, integral 226 hepsi 0; 1215 test geçti.
- Açık/kayıt: YO-T2-4, YO-T2-5, YO-T2-6, RK-T2-5, RK-T2-6; boş öncülde yanlış eq özdeşliği unknown.

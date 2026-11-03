# wip/son-adim ikinci tur (EK 2) — düzeltici raporu özeti (21 Ekim ~18:50)
Commit'ler: d59d282 (1) SA-YO-1/SA-RK-3/SA-RK-8; 4aeeb16 (2) sınır kuralı daraltma, payda kökü, SA-RK-4/5/6; e2b30ca (3) değerlerinden biri
dışlanan liste seçim değil; 8b1e884 (4) koşul şıkkı option_unreadable (d59d282 gerilemesi); f657528 (5) sonda L/M/N, mutasyon S35–S56;
e65a8b4 (6) okunmayan şık IR'ı tutarsız yapmaz; 0dfadd9 (7) SA-RK-1 testi (S38 yaşıyordu).
- SA-YO-1 kapandı: şık okuyucusu yalnız dolgu sözcüğünü atar; birim sözcüğü yalnız IR.units bildiriyorsa; başka sözcükte şık okunmaz.
- SA-RK-3 kapandı: başka birimde şık UNKNOWN. SA-RK-8 kapandı: bilinmeyeni anan şık değer değil.
- SA-YO-2/SA-RK-2 kapandı: sınır yolundan unknown adım öncül havuzuna girmez. SA-YO-3: sınır kuralı yalnız Eq ve Eq'lerin Or'u.
  SA-YO-4: öncül/kısıt başka sembol de anıyorsa kural yok. SA-RK-1 (karar gereği): kesin kısım ∩ tanım kümesi boş değil kanıtı.
- SA-RK-7 payda kökü kapandı (pay = 0 ve payda = 0 kritik; seçenek çarpımı; adım her seçenekte çürütülürse refuted); kalan (Δ<0, deneme
  noktası, K1) kayıt. SA-RK-4: units derece/°/%/yüzde iken işaret düz sayı (iddia, şık, option_value, adım). SA-RK-5: angles_in_radians
  genelleştirildi. SA-RK-6: meta şık pencere dışı; pencere sertifikanın değerinden bir kez (TOLERANCE_WINDOW); sqrt(1+x³) 12.1 → 5.4 s.
- Kardeşler: 'x = 1 or x = -5' yanlış kök listesi seçim sayılıp skipped (CORRECT) oluyordu → Eq'lerin Or'u ancak her değeri serbestse seçim;
  wordproblem okunmayan şıklarla ir_inconsistent → şıklar okunmuyorsa iddia kendi başına.
- Ölçüm: sonda 346 vaka taban 171 → 0; tests/test_d4_son_adim.py 226 test (tabanda 115 düşer); mutasyon 57/57; parça sondaları hepsi 0;
  pytest 5104 geçti/101 atlandı (staged_check belge adı testi 0e93ed5'te de düşer, d8a76b4'te düzeldi); fark 558: 0.
- Açık/kayıt: '1/2 saat' iddiası INCORRECT (iddia okuyucusu gevşek, şık okuyucusu katı); içi boş eşitsizlikte 'x = 5' çürütülmüyor
  (karar gereği, testli); kök denkleminden sonra tek nokta/hepsi içeride liste skipped (tabanla aynı); SA-RK-7 kalanı, G5, SA-RK-10 kayıt;
  compute sınır adımları kapsam dışı; units'siz '30^\circ' UNKNOWN (tabanda CORRECT: kapsama kaybı, sayılmalı).
- Çakışma riski: verifier (_from_letter, _sanitize_payload strict, _option_claim_value, _options_in_tolerance, _META_OPTION), base.py Ctx,
  algebra._verify_evaluate, calculus.definite_integral (son-integral abs_tol), wordproblem._z3_check, deterministic (check_steps, _free_choice).

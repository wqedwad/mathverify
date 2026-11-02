# wip/son-kalkulus ikinci tur (EK 6, EK 7) — düzeltici raporu özeti (23 Ekim ~10:00)
HEAD cad4874. Commit'ler (4e2e4d7 sonrası): f0ed29f, 69974f3, 9b616b0, 2ab804b, 7ea425c, 976df86, d256009, cad4874.
- YO-K1 = RK-PW-EQ = SK-RK-2 kapandı: diff'in değer okuması (_value_step) formül değeri farklı noktaya kesin kuralların kanıtladığı türevi koyar
  (calculus.exact_point_slopes); yazılı okuma aynı kurallarla aynı değeri denetler, kanıt yoksa kararsız (_formula_values_unproved); _piecewise_rule
  eğimi verir; point_derivative parçalıda önce kural; _at önce o noktada alınan dal. Yollar: at(diff), verilen x = p, şık, f' + f, f' = 0 / f' > 0
  kümeleri, adım, noktada türev görevi.
- YO-K2 + SK-RK-3 kapandı: _value_holes: formül değeri kanıtlı eğime eşit değilse nokta karşılaştırma dışı, iddia o eğimle ölçülür;
  ∛(x³)' = 1, (|x|·sign x)' = 1 CORRECT; sign(x)² INCORRECT.
- YO-K4 kapandı: 'R − A ∪ B' iki okuma; aynı kararsa o, farklıysa UNKNOWN; 'R − ({2} ∪ {3})' okunur.
- SK-RK-1 kapandı (süre ve belirlenim): hesap işlemi içeren hedef yapısal okunmaz (iddia zaten check_claim_is_value ile reddedilir; testle).
- SK-RK-7 kapandı: birleşimde G2RK-10 Contains'i okur; tek başına dal için istisna koruması (UNKNOWN).
- Kayıttan yapılıp ölçülenler: YO-K3 (Derivative(...), diff(f, (x, n)) varlık koşulu), YO-K5 (n ≥ L tam sayı = positive_integer), SK-RK-6 (gerçel a
  için |a|^(2k) anahtar değil). Kayıt: SK-RK-4, SK-RK-5.
- Kardeşler: atlamalı fonksiyonda f''(1) = 2 CORRECT (DNE INCORRECT) çıkıyordu → yüksek mertebede alt türev kanıtlatılır; yazılı okumada at() dal
  koşulu; değer denetimi istisnasında fail-open → kararsız; Derivative form olarak kalır (d4d bağlama, _written_poles testleri); set_difference
  bayrakları (d4j CAP-K1).
- Ölçüm (cad4874): son/kalkulus 473 vaka (A–F, K 220 + yeni G 253 tur2.py; G 0e93ed5 ve 4e2e4d7'de 147/253 beklenmeyen) → 0; test 213 (82 yeni;
  4e2e4d7'de 66'sı, 0e93ed5'te 59'u düşer); mutasyon 63/63 (K58 etkisiz değişiklikle birlikte kaldırıldı, K59 testle); denetçinin 1360 vakası
  4e2e4d7: 338 beklenmeyen (yanlış onay 12, haksız ret 48, layer_exception 6, 629 s) → 267 (yanlış onay 3, haksız ret 25, layer_exception 0, 270 s;
  en uzun 25,2 → 7,8 s; 71 iyileşme, 0 kötüleşme); kalan 3 yanlış onay RK-EXT-1 (sayısal dalında kapalı); parça sondaları hepsi 0; kap 69/1/19
  (afab1ac 68/1/20; kayıp 0, kazanç 1); fark: karar 0, ilk kötü adım 0; tam takım: yalnız git isteyen 4 staged_check testi (arşiv kopya).
  Birleşim d6e3d65 + cad4874 (merge-tree temiz): son sondaları kalkulus 473, integral 226, sayisal 356, adim 407, ayristirici 502 hepsi 0;
  test_d4_son_*.py 966 geçti; SK-RK-7 10/10. Belirlenim: 8 vaka × 12 tohum × 3 paralel süreç: cad4874, d6e3d65 + cad4874, 084ae53 + cad4874 96/96
  aynı (medyan 1,0–1,3 s); da5ba37 (integral dalı, ilk tur düzeltmesiz) tutarsız (f'(3) = 6: 1 CORRECT / 11 UNKNOWN), INCORRECT üretilmedi.
- Açık (taban): cbrt ilkelleri F31/37/38 reddi; şıkta 'Yoktur' (T112, N0/4/8/12); D2-5; route0 testi bir kez yük altında düştü (9/9 tekrar geçti).

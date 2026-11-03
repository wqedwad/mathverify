# wip/son-adim üçüncü tur (EK 7, EK 8) — düzeltici raporu özeti (22 Ekim ~15:00)
HEAD 816747f. Commit'ler (0dfadd9 sonrası): cf7a4f9 bütün düzeltmeler; a3abe6b sonda P/Q/R ve EK 8 beklentileri; 52ba61e mutasyon S58–S76
(eski birim mutasyonları S43–S46 silindi); c718d67 S15/S21 testleri; 816747f S15 hedef testi EK 8 testine.
- Birim kuralı (T2-RK-1/2, T2-OT-1, SA2-YO-4): IR.units okunmaz. İddia/şık yalnız tamamı tek işaretli sayı ('%20', '30°', '\boxed{30^\circ}') VE
  IR değerinin o birimde olduğu kanıtlıyken düz okunur; kanıt: evaluate ifadesi yazıldığı biçimde ×100 / ×180/π; angle() hedefi; cevabın değişkeni
  trig ilişkilerine pi·(kx+c)/180 olarak girer (deg(x), (x)°, cos(pi*C/180)). Yoksa G1RK-3 iki okuma. Adım her zaman iki okuma; ancak ikisinde
  çürütülürse refuted.
- SA2-YO-1: iki okumada doğrulanmayan işaretli adım öncül havuzuna da seçimlere de girmez ('A = 40°' sonrası yanlış 'C = 2*B' refuted).
- SA2-YO-2: ondalık virgüllü ('9,95'), aralık ('7–8'), sayı olmayan ('[7, 8]') şık pencerede None. SA2-YO-3: okunmayan şıklardan hiçbiri iddianın
  sayısıyla başlamıyorsa ir_inconsistent. T2-RK-3: 'x = 6' şıkkı 6; Python set → FiniteSet; yalnız harf {{6}} hatası kapandı.
- T2-RK-4: aynı kritik kökleri paylaşan yazımlar tek seçim; 16'dan fazla seçenekte sınır okunmaz; _tick ve _bounded; 13 yazımda 2.2 s (önce 265 s).
- T2-RK-6: _META_OPTION Türkçe İ/ı ve ASCII katlamasıyla; 'yukarıdakiler(in|den) hiçbiri(si)', 'hiçbiri değil(dir)', 'bilinemez', 'belirsiz(dir)'.
- Ölçüm: son/adim 407 vaka (taban 202, 0dfadd9 66 → 0); tests/test_d4_son_adim.py 277 (tabanda 139, 0dfadd9'da 54 düşer); mutasyon 72/72;
  parça sondaları hepsi 0; fark 558: 0; pytest 5157/101 atlandı (staged_check belge adı testi, 0e93ed5'te de); son/ayristirici 502: taban 237 → 235
  (iki iyileşme, gerileme yok); son/sayisal 341: 104 → 105, fark iki C3 vakası ('sin(C3)+sin(8): 1', 'argmin … 0') koşudan koşuya değişiyor
  (tabanda da 'argmin … 0' bir koşuda CORRECT) → #7. Denetçi sondaları: yanlış onay 95 vakada 41 değişim, ret-kapsama 73 değişim, hepsi beklenen
  yönde. Kapsama (169 ortak vaka): CORRECT→INCORRECT 0; INCORRECT→CORRECT 23; UNKNOWN→CORRECT 8; CORRECT→UNKNOWN 27 (birimi kanıtsız
  işaretli cevaplar: '%20' kesir IR'ında, '180°' ters trig toplamında, '60°' 2x'te, '45°' extremum'da; EK 8'in bilinen bedeli).
- Açık/kayıt: T2-RK-5; birimi kanıtsız ters trig/argmax 'X°' UNKNOWN (tabanda CORRECT); '1/2 saat' iddiası INCORRECT (birim sözcüğü asimetrisi);
  SA-RK-7 kalanı, SA-RK-10.

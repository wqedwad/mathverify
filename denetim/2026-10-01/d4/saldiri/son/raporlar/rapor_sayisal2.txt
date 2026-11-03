# wip/son-sayisal ikinci tur (EK 4) — düzeltici raporu özeti (22 Ekim ~09:30)
HEAD 54aca55. Commit'ler (4153cc1 üstünde): 0f64222 SS-YO-1; 87dfb80 RK-SAY-1/2/3, RK-ARG-STEP; 54aca55 yaşayan üç mutasyon için testler
(src 87dfb80 ile aynı). Düzeltme: 87dfb80 mesajında yeni sonda gruplarının dağılımı "31/21" yazıyor, doğrusu 32/20 (toplam 52 doğru).
- SS-YO-1 kapandı (taban, yüksek yanlış onay): ops.critical_points sıfırları rd (exact_solveset) kümesinden alır, tekil noktaları ekler; biri
  bulunamazsa None; None'da aday kümesi asla tam değil; gerçelliği kararsız nokta _kinks ve certify_local_extremum'da listeyi eksik yapar.
  RK-EXT-1'i de kapatır: 14 Abs/Max-trig fonksiyonunun 13'ünde doğru maksimum CORRECT (tabanda 6 INCORRECT, 1 UNKNOWN).
- RK-SAY-1/RK-ARG-CALC kapandı: noktasal görevde [0, 2π) Piecewise'ı noktadaki im(u) işaretiyle yerelde; kararsız okuma arg_reading_undecided.
- RK-ARG-STEP kapandı: yalnız bir okumada çürütülen adım unknown; first_bad_step iki okumada çürütülen ilk adım.
- RK-SAY-2 kapandı: INCORRECT uyuşması yalnız ortak düşen katman/adımla; yoksa UNKNOWN.
- RK-SAY-3 kapandı: bütün şıklar sayı ve yalnız bir okumanın değeri şıklarda → şıklar aralığı bildirir; sayı olmayan şık, iki değer
  şıklarda, derece şıkları (G1RK-3) → UNKNOWN.
- SS-OT-1, SS-ND-1 kayıt.
- Ölçüm (0e93ed5 → 54aca55): son/sayisal 341 vaka 104 → 0 (103 kötüden iyiye, iyiden kötüye 0; tek beklenti değişimi 'MC arg(−1−i): B 5π/4'
  UNKNOWN → CORRECT, RK-SAY-3); son/adim 346 ve son/ayristirici 502 vaka bazında 0 değişim; tests/test_d4_son_sayisal.py 53 (tabanda 42 düşer);
  mutasyon 38/38 (S24, S27 gerçek girdiyle ulaşılmaz, mekanizma testi); parça sondaları hepsi 0 (d4c H grubu 20 dk'yı aşar, iki parçada);
  fark 558: 0 (karar, ilk kötü adım, adım durumu, K4); kap/kap2: 0 fark; dokunulan modüllerin testleri 2723 geçti; critical_points'in None
  döndüğü 10 düz fonksiyonda 20 iddianın kararı aynı.
- Açık (önceden var kapsama): Max(sin x, cos x) + x/4 maksimumu, sin x cos x tipi sıfırlar UNKNOWN; Σ iᵏ değersiz; LaTeX \arg ve Arg okunmuyor.

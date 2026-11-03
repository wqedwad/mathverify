# wip/son-sayisal üçüncü tur (EK 7, EK 10) — düzeltici raporu özeti (22 Ekim ~21:00)
HEAD 35c358d. Commit'ler: f8dd783 (SS2-RK-1/2/3, SS2-CR-1), 35c358d (S33–S35 mekanizma testi). f8dd783 mesajı "tam ölçüm sonraki commit'te"
diyor; 35c358d yalnız mutasyon sonucunu taşıyor (tam sayılar burada).
- SS2-RK-1 + SS2-RK-2 kapandı: verifier._convention_steps_unknown: bir okumada çürütülüp ötekinde doğrulanan adım iki okumada da unknown; karar
  cevap sertifikasından; first_bad_step onu göstermez. (1−i)^10 = −32i, (√3−i)^6 = −64 CORRECT; 32i, 64 INCORRECT. [0,2π) şıklı 7π/4, 11π/6
  INCORRECT → CORRECT; 5π/6 INCORRECT. Ek olarak iki okumada yanlış adım varsa INCORRECT, first_bad_step 2.
- SS2-CR-1 kapandı: _arg_options_reading sandbox'ta 8 s (arg_options_worker); '10**10**10' 120 s karar yok → 8,9 s UNKNOWN.
- SS2-RK-3 kapandı (yerel): ±∞ im(u)'nun polinom baş katsayısı işaretiyle (parse._eventual_sign); verilenlerde tek eşitlikle sabitlenen parametre;
  lim x→∞ arg(1+xi) = π/2, a = 2 türev 2/5, a = 1 limit π/4 CORRECT; 0, 1/5 INCORRECT; x→−∞ ve polinom olmayan im(u) UNKNOWN.
- Ölçüm: son/sayisal 356 vaka taban 112 → 0 (120 değişim: iyi→kötü 0); son/adim 407, son/ayristirici 589: değişim 0; parça sondaları hepsi 0;
  fark 558: 0/0/0/0; kap/kap2: 0; test 2729 geçti; test_d4_son_sayisal.py 58; mutasyon 46/46 (f8dd783'te 43/46); denetçi sondaları gerileme yok
  (ret 236: INCORRECT→CORRECT 5, UNKNOWN→CORRECT 13; ret2 106: U→C 12, I→C 3; ret5 8: U→C 4, U→I 2 yanlışlar). Deneme birleşimi 084ae53'e
  çakışmasız; birleşikte 5 son test dosyası 884 test, son sondaları sayisal 356, adim 407, ayristirici 502, kalkulus 220, integral 226: 0.
- Açık: SS2-YO-1, SS2-YO-2 kayıt; LaTeX \arg, Arg, Σ i^k, Max(sin, cos) + x/4 UNKNOWN.

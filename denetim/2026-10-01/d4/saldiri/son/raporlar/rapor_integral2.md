# wip/son-integral ikinci tur (EK 5, EK 7) — düzeltici raporu özeti (22 Ekim ~14:30)
Commit'ler (3afddba üstüne): 14769a8 (ara: dört madde), cbaea02 (gerçel değere karmaşık iddia kararsız, d4c SG-1; (-oo, oo) testi), da5ba37 (ölçümler).
- SON-INT-RK-1 kapandı: within_abs_tol/within_rel_tol karmaşık farkta |d|² = Re² + Im² kesin okunur (göreli t²|v|²); dışarıda her zaman çürütür,
  içeride yalnız karmaşık değere karşı kabul; gerçel değere gerçel olmayan iddia kararsız (e ≈ 2.71828 + 1e-9 i UNKNOWN; d4c SG-1).
- SON-INT-RK-2 kapandı: sertifika denetiminin zarfı ≤ 500 hücre; cval'ı tutan sonlu toplam 8 turda 1/8 daralmazsa durur (settle, _CHECK_BUDGET);
  32 zarf çağrısında durum aynı, süre 57.2 → 4.5 s; süre sondası 60 vaka 0e93ed5 159.0 s / 3afddba 220.5 s / cbaea02 162.3 s, karar değişimi 0.
- SI-YO-3 dar fail-closed: duran merdiven son iki basamağın err/ölçeği ≤ 1e-10; ∫_{-1}^{8} x^(-1/3) = 9/2 CORRECT.
- SI-YO-2 dar fail-closed: yarı sonsuz zarfta sertifika yalnız son basamağa 100·err payla yakınsa ve err/ölçek ≤ 1e-8 (merdivenin hata tahmini
  gerçek hatanın 2.3–38 kat altında; doğru değerlerde en çok 1.0e-10, ıraksaklarda 1.8e-4–5e-3); ∫_0^2 |x−1|^(−2/3) = 6 CORRECT.
  Kardeş: zarf ağırlık kuralı uçtaki tek başına kuvvet ve |u|^p'yi ağırlık sayar (∫_0^1 x^(−99/100) zarfı [100, 100]); u < 0 hücrede ağırlık yok
  (eski kod ∫_{-1}^0 2x^(−1/3) için yanlış [3, 3]; verify yolundan tetiklenmedi).
- Ölçüm (cbaea02): tests/test_d4_son_integral.py 129 (ikinci turun 36 testinin 21'i 3afddba'da düşer); son/integral 226 vaka 0 (3afddba'da 15,
  0e93ed5'te 120); parça sondaları hepsi 0; fark 558: 0; kap aynı; 39 test dosyası 2988 geçti/86 atlandı; mutasyon 69/69 (I06 testle).
- Açık/kayıt: SI-YO-2 bedeli: iç noktada üssü −19/20, −99/100 güçlü tekillik 4 vaka CORRECT → UNKNOWN (ağırlık kuralı iç sıfırlara genişletilmedi);
  G2YO-2 bedeli: işaret değiştiren 4 vaka (sign(x)|x|^(−4/5) [−1, 32] = 5) UNKNOWN (karar değişikliği önerisi; durma kuralıyla kayıt);
  evaluate içindeki Integral(...) formu sertifikayı denetlemeden alıyor (equiv/forms.py; yalnız ekilmiş sertifikayla) kayıt;
  kalkülüs sondasında '|x²−4|' at 3' koşudan koşuya CORRECT/UNKNOWN/INCORRECT (3afddba tabanlı dalda) → kalkülüs düzelticisine iletildi.

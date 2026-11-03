# wip/son-ayristirici ikinci tur (EK 3) — düzeltici raporu özeti (22 Ekim ~09:00)
HEAD d9527f7. Commit'ler (1ea9b43'ten sonra): 14937e2, 4a7f251, 693d2cc, 3868076 (dört maddenin kodu), 3c5fecb (kardeşler, sonda, testler),
6c7d33a, a305ec2, cd8bf58 (mutasyon listesi), 3b08689 (F6 gerilemesi), d9527f7 (test adı).
- SA-YO-1 kapandı: boş öncülde açık adımın çürütmesi yalnız adım kanıtlı sonuçsa geri çekilir (öncülün sıfırdan farklı sabit katı ya da öncülün
  bütün kesin karmaşık çözümlerinde doğru); kesin bir karmaşık çözümde yanlışsa çürütme kalır; karar yoksa compute adımı step_reading_undecided
  (_BLOCK_POSITIVE_FLAGS: CORRECT'i her durumda engeller) → UNKNOWN. Kardeş: değerlendirme sadeleştirince yazılı kutuplar kayboluyordu
  ((x⁴−1)/(x²+1)): _written_poles dışlanır. Kayıt: boş öncülde yanlış eq adımı tabandaki gibi unknown (iii).
- SA-RK-1/SA-RK-2 kapandı: 'gerçek', 'gerçek sayılarda', T.K./TK/D(f)/ÇK/Ç.K. önekleri, '(∅)', ''dir', 'There is no solution'; yalnız 'kök yok'
  anan şık ∅ yanında en kötü UNKNOWN. Kardeş: hiçbir okumanın almadığı şık ('Sağlayan bir x değeri yoktur') küme cevabında INCORRECT → UNKNOWN.
  'Reel sayılarda çözüm yok' artık CORRECT.
- SA-YO-2 + SA-RK-3 kapandı: izin sözlüğü; ret ifadesi payload_negated; bilinmeyen sözcük UNKNOWN. harness/adversarial.py enjeksiyon
  kuyrukları (5'in 4'ü UNKNOWN oluyordu, test_f6_robustness 2 test) sözlüğe eklendi; rakamsız etiketler düzyazı sayılmaz.
- SA-RK-5/SA-RK-6 kapandı: simge ya da tek harf atılmaz (INCORRECT → UNKNOWN); sondaki ','/';' noktalama; 1 öğeli demet değer değil.
- SA-YO-3/SA-RK-4/SA-YO-4 kapandı: LaTeX fonksiyon argümanı ilk işlece kadar, '_' tabanı atlanır; '\%', '^\circ', Unicode eksi aynı denetimde.
  Kardeş: latex2sympy '\sin x \cdot \cos x'i sin(x·cos x) okuyordu: argüman ayraç içine alınır.
- Ölçüm (1ea9b43 → 3b08689): sonda 502 vaka 144 → 0 (F 14/25, G 56/94, H 55/83, J 19/29; eski gruplar 0/271); test 289 (tabanda 112 düşer);
  fark 558: 0 (dökümler bayt bayt aynı); kap 89: aynı (68/1/20); derlem temizleyicisi 1986 metin: fark 0; adversaryal 100 öğe/7115 saldırı:
  özet aynı, flipped 0, accepted_wrong 0; mutasyon 75/75 (F06 eşdeğer, gerekçeli çıkarıldı); parça sondaları hepsi 0; adim sondası 346: 0;
  sayisal sondası tek değişim: 'sin((1+√3i)³)+sin(8) = 1' iki ağaçta da PYTHONHASHSEED'e bağlı rastgele CORRECT (önceden var yanlış onay;
  wip/son-sayisal'da UNKNOWN) → #7'ye gözlem.
- wip/son-adim ile deneme birleşimi: 3 mekanik çakışma (parse.py, verifier.py, _sanitize_payload sıkı kip + bütün kuyruk okuması);
  betik ayr/resolve_merge.py; birleşikte ayristirici 502/0, adim 346/0, 769 test. '50\%' birleşikte UNKNOWN (G1RK-3).
- Açık/kayıt: boş öncülde yanlış eq özdeşliği unknown; \bigl, \displaystyle bölenden sonra çarpan sayılır (UNKNOWN; ölçülmedi).

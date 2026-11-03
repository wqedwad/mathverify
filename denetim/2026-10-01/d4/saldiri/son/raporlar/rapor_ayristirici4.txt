# wip/son-ayristirici EK 11 — 'Yoktur' değer yükü (23 Ekim; düzeltici raporunu veremeden durdu, özet commit mesajlarından)
Commit'ler: 797f931, 84b7162 (d1a1ee2 üstüne).
- 797f931: küme ya da aralık olmayan cevapta yalnız bir DNE sözcüğünden oluşan 'value' yükü ('Yoktur', 'yok', 'Türevi yoktur.', 'mevcut değil',
  'tanımsız', 'DNE', 'does not exist') 'dne' iddiası (_dne_word_claim); '5 yoktur' gibi değer içeren yük girmez. Ölçüm (worktree, Lean'siz):
  denetçinin N grubu 18 vakada 0 beklenmeyen (N0/N8 'dne' eşleri gibi UNKNOWN, N4/N12 CORRECT, N16 INCORRECT), T112 UNKNOWN (önce INCORRECT);
  test 378; sonda 610 (yeni P 21) 0; mutasyon kalıpları 90/90.
- 84b7162: 797f931'de mutasyon 90'dan 89 öldü, Y03 (küme cevabı koruması) yaşadı; koruma gözlenebilir tek durumda haksız ret veriyordu
  (x**2 + 1 = 0 için 'Yok' değeri 'Yok' şıkkı yanında INCORRECT); koruma kaldırıldı (karar şekil sınırlamıyor): orada UNKNOWN; x - 1 = 0'da
  aynı yük INCORRECT → UNKNOWN (kapsama, yanlış onay değil). Ölçüm: test 378; sonda 611, 0; mutasyon 90/90.
- Düzelticinin fark, kap ve parça sondası ölçümleri yapılamadı (ajan kuruluş erişim hatasıyla durdu); son ölçüm turunda birleşik kodda ölçülür.

# 26 Eylül 2026: kademeli kontrolün ve paralel taramanın mutasyon denetimi

`mutasyon.py`, DECISIONS §59'daki üç parçanın testlerini mutasyonla sınar: kademeli kontrol kuralı
(`scripts/check.py --plan` ve `--full`'un günlüğü), çalışma anı belge-okuma bekçisi
(`tests/doc_read_guard.py`) ve 4 sürece dağıtılan adversaryal tarama (`harness/adversarial.py`).
Her mutasyon tek bir davranışı bozar (bir denetimi kaldırır, bir koşulu gevşetir, bir sayacı
sıfırlar); onu tutması gereken test dosyası mutasyonlu kodda koşar ve düşmelidir ("öldü"). Yaşayan
mutasyon, hiçbir testin tutmadığı bir davranıştır.

İnceleme sırasında mutasyonlar oturumun geçici betikleriyle koşmuştu; bu dizin sayının depodan
yeniden ölçülebilmesi için eklendi (üçüncü inceleme turu bulgusu).

## Koşturma (Linux/bulut; Windows'ta `.venv/Scripts/python.exe`)

```bash
PYTHONUTF8=1 .venv/bin/python denetim/2026-09-26/mutasyon.py --list      # mutasyonların adları
PYTHONUTF8=1 .venv/bin/python denetim/2026-09-26/mutasyon.py -j 3 C G    # kural ve bekçi, 3 klonda
PYTHONUTF8=1 .venv/bin/python denetim/2026-09-26/mutasyon.py A           # paralel tarama, tek klonda
```

- Ölçülen, **commit edilmiş HEAD**'dir: betik HEAD'in atılabilir klonlarını (uzaksız; `.env`
  klondan hemen silinir, geçmişi `.git`'te kalır) geçici dizinde açar, yolunu başta yazar ve işi
  bitince siler; SIGTERM/SIGHUP'ta da (koşan testleri öldürüp) siler. Silemezse yolu yazar ve
  3 ile çıkar. Checkout'a ve uzağa dokunmaz; commit edilmemiş değişiklik ölçülmez. Testler klonun
  kendi `src`'siyle koşar (`PYTHONPATH`): venv'in düzenlenebilir kurulumu checkout'u gösterir.
- Önce mutasyonsuz test dosyaları klonda geçmeli; geçmezse ölçüm yapılmaz (çıkış 2). Hiçbir
  mutasyonla eşleşmeyen ad da çıkış 2'dir.
- Çıkış 0 yalnız bütün mutasyonlar uygulanıp öldüyse. Deseni kodda bulunamayan mutasyon
  "UYGULANMADI" diye yazılır: kod değiştiyse desen de güncellenir. Ölçülen sayılar ve commit
  DECISIONS §59'da.
- `A` mutasyonları (`tests/test_adversarial_parallel.py`) zamanlamaya bağlı bir ön koşul taşır (ilk
  öğe ikinciden yavaş); makine yüklüyken tek klonla (`-j 1`) koşulur. Bir mutasyonun hangi testle
  öldüğü satırda yazar: öldüren test, mutasyonun bozduğu davranışı sınayan test olmalıdır.
- Adlar: `C` kural, günlük ve adım zaman aşımı, `G` bekçi, `A` paralel tarama (ve `check.py`'nin
  tarama satırı). Ad bir önektir: `C1` C1, C10–C19 ve C100–C117'yi seçer.

Pyflakes kapısının ve pytest'in dışında durur, `denetim/2026-09-25/` gibi. Betikteki hiçbir dizgi
bir belgeyi adlandırmaz: `check.py` deponun bütün Python dizgi sabitlerini okur.

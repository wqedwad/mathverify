# Başvuru kaydı: yayın sürümü

Bu depo, mathverify'ın bir başvuru için herkese açılan sürümüdür. Geliştirme 18 Eylül–3 Kasım 2026
arasında özel bir depoda yürüdü. Bu kayıt, yayın sürümünün özel sürümden nasıl ayrıldığını ve bunun
nasıl doğrulandığını tutar. Projenin kendisi için `README.md`, kararlar için `DECISIONS.md`, güncel
durum ve açık maddeler için `HANDOFF.md` okunur.

## 1. Özel sürümden farkı

Geçmiş yayından önce `git-filter-repo` (a40bce5) ile yeniden yazıldı. Commit sırası, tarihleri ve
mesajları korunur; commit kimlikleri değişti (§2). Çıkarılanlar:

| Ne | Neden | Yerine |
|---|---|---|
| `.env` (iki API anahtarı) | Özel dönemde depoda izleniyordu (DECISIONS §35); kural "depo açılacaksa önce geçmişten temizlenir" idi ve uygulandı | Yok; `.env` artık izlenmez (`.gitignore`) |
| `denetim/2026-10-01/d4/wip/` (17 arşiv sürümü, ~68 MB; yamalar) | Ara yedeklerdi (bundle, tar.gz) ve eski geçmişi taşıyorlardı; içerikleri zaten `master`daydı | Yok |
| Kişisel e-posta (commit kimliği) | Kişisel veri | GitHub'ın hesaba bağlı noreply adresi |
| Yerel kullanıcı adı, WSL disk kimliği | Kişisel makine izi | `kullanici`, `WSL-GUID` |
| Claude oturum bağlantıları ve kimlikleri | Hesaba bağlı iz | Commit mesajlarından silindi; dosyalarda `session_GIZLI` |
| Birkaç kişisel çalışma notu ve sohbet alıntısı (on kalıp) | Teknik içerik taşımıyordu | Kararın kendisi ve tarihi yerinde bırakıldı |

Değişmeyenler: kaynak kod, testler, değerlendirme seti, ölçüm betikleri, raporlar, LLM önbelleği,
karar kayıtlarının teknik içeriği. Özel uçla (`596f2f7`) karşılaştırmada 13 dosya farklıdır (`.env`
silindi; 12 belge ve günlükte yukarıdaki değişimler); `src`, `tests`, `harness`, `scripts`,
`evalset`, `lean`, `llm_cache`, `reports/*.md`, `pyproject.toml` ve `requirements.lock`'ta fark
**0**.

## 2. Commit kimlikleri

`DECISIONS.md`, `HANDOFF.md`, `docs/` ve `reports/` içindeki kısa commit kimlikleri (ör. `62fb71e`)
yeniden yazımdan **önceki** özel geçmişe aittir. Bu depodaki karşılıkları
`docs/yayin-commit-esleme.txt` dosyasındadır (628 eşleme; yalnız çıkarılan dosyalara dokunan 2
commit düştü). Commit mesajlarındaki göndermeleri araç yeniledi. `reports/check_full.log` eski
kimliği gösterdiği için `scripts/check.py --plan` o koşuyu bu depoda kabul etmez; ilk kod
değişikliğinden önce yeni bir `--full` gerekir.

## 3. Doğrulama (ölçüldü, 24–25 Kasım 2026, bulut)

Özel depoda tarama kapsamı: GitHub'daki bütün ref'ler (2 dal, 10 etiket, 15 PR ref'i, 1 araç
ref'i), 632 commit, 3185 benzersiz dosya sürümü, commit mesajları; gömülü 9 bundle sürümü (559
commit, ana depoda olmayan nesne 0) ve 8 tar.gz sürümü (15 065 dosya). Gerçek sır yalnız `.env`'de
bulundu; değerler başka hiçbir dosyada, mesajda ya da arşivde yoktu.

Yeniden yazılmış geçmişte (628 commit, 3159 dosya sürümü, 7446 git nesnesi), bu kayıttan önce:

| Denetim | Sonuç |
|---|---|
| Anahtar değerlerinin her 12 karakterlik penceresi; düz, ters, base64 (üç hizalama), hex, URL kodlu, büyük/küçük harf; boşlukları silinmiş metinde de; commit ve ağaç nesneleri dahil | 0 isabet (öz-sınama: özel geçmişte yalnız `.env`'i buluyor) |
| `.env` ve 17 arşiv blob'u nesne veritabanında | yok |
| Bilinen anahtar biçimleri (Anthropic, GitHub, AWS, Google, Slack, özel anahtar bloğu, JWT) | 0 gerçek; eşleşenler testlerdeki sahte değerler (`sk-ant-test-…`, `github_pat_TEST_…`, `proxyuser:proxypass`) |
| Yüksek entropili dizgi taraması | 56 aday, hepsi dosya yolu ya da sahte test verisi (öz-sınama: özel geçmişte iki anahtarı da buluyor) |
| `detect-secrets` 1.5.0 (uç) | 18 bulgu, hepsi sürüm pini ya da sahte test verisi |
| Kişisel e-posta; yerel kullanıcı adı; oturum kimliği | 0; 0; 0 |
| E-posta adresleri | yalnız `noreply@anthropic.com`, `git@github.com`, `*@example.invalid` ve noreply commit kimliği |
| Alan adları (32) | hepsi kamuya açık kaynak ya da araç adresi |
| IBAN, kart, telefon, SSH anahtarı, IPv6, MAC kalıpları | 0 (telefon kalıbına uyan üç sayı milisaniye ölçümü) |
| Düz yazıda kişisel bağlam sözcükleri ve özel ad taraması (184 farklı sözcük) | kişiye ait ad, kurum ya da yer yok |
| İkili dosya | yok |

Testler: yeniden yazılmış geçmişin ucunda tam takım **6045 passed / 5 skipped** (Python 3.14.6,
Lean'li; atlananlar beklenen beş test). Sayı, özel depodaki son `check.py --full` koşusununkiyle
aynıdır.

## 4. Sınırlar

- Tarama bilinen biçimler, değerlerle birebir arama, entropi ve sözcük listeleriyle yapıldı;
  belgeler satır satır insan gözüyle okunmadı.
- `scripts/check.py --full` bu geçmişte koşmadı (§2).
- Özel depo, etiketleri, PR kayıtları ve yerel yedekleri eski geçmişi taşır; yayımlanmaz. Özel
  dönemin iki API anahtarı 25 Kasım 2026'da iptal edildi (kullanıcının bildirimi; buluttan
  doğrulanmadı).
- GitHub kullanıcı adı, depo adı, bulut konteynerinin yolları (`/home/user`, scratchpad
  dizinleri), sağlayıcı istek kimlikleri ve maliyet sayıları bilerek bırakıldı: kişiye özel ya da
  gizli değil.

## 5. Yayın (25 Kasım 2026)

Yeniden yazılmış geçmiş yeni bir depoya (`wqedwad/mathverify`, dal `master`) tek ref olarak
gönderildi; etiket ya da başka dal gönderilmedi. Gönderimden sonra depodan alınan taze, tam
kopyada dosya ağacı taranan uçla aynıydı, `.env` nesnesi yoktu ve §3'teki anahtar penceresi
araması 0 isabet verdi. Aynı gün `README.md` yeniden yazıldı (eski hâli
`docs/arsiv/README-2026-09-27.md`). Depo ana sayfası `README.md` İngilizcedir (kullanıcı isteği); aynı içeriğin
Türkçesi `README.tr.md`'dedir. Kod değişmedi.

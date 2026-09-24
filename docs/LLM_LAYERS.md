# LLM katmanları (F3–F4): yapılandırma, roller ve maliyet

## Aileler ve roller

İki model ailesi kullanılır; bir çözümü üreten aile o çözümü yargılayamaz (handoff §3 kural 3,
§11/9).

| Rol | Aile | Varsayılan model | Gerekçe |
|---|---|---|---|
| IR çıkarıcı | anthropic | `claude-opus-5` | Formalizasyon kalitesi birincil |
| Round-trip yargıcı A | anthropic | `claude-opus-5` | İki aileli konsensüs şart (§5) |
| Round-trip yargıcı B | meta | `muse-spark-1.3` | Bağımsız aile |
| Çözücü (yol a) | meta | `muse-spark-1.3` | Doğrulayıcı tarafından farklı aile kalsın |
| L4 yeniden çözücü | çözücünün **karşıtı** | — | Çapraz aile zorunlu |
| L6' kritik | çözücünün karşıtı | — | Aynı model kendi hatasını görmüyor [6] |
| L6' meta-doğrulayıcı | kritiğin karşıtı | — | Kritik çıktısı ham kabul edilmez [4] |
| Lean ispatı | çözücünün karşıtı | — | İspatı Lean denetler, aile yine de ayrık |

Ortam değişkenleri: `MATHVERIFY_ANTHROPIC_MODEL`, `MATHVERIFY_META_MODEL`,
`MATHVERIFY_ANTHROPIC_BASE_URL` (24 Eylül 2026'da eklendi, aşağıda).
Anahtarlar `.env` dosyasından okunur (`ANTHROPIC_API_KEY`, `META_MODEL_API_KEY`); `.env`
git tarafından yok sayılır ve önbellek kayıtlarına hiçbir kimlik bilgisi yazılmaz.

**Düzeltme (24 Eylül 2026):** `.env` artık git tarafından yok sayılmıyor; kullanıcının açık
kararıyla bu özel depoda izlenir (`DECISIONS.md` §35). Önbellek kayıtlarına kimlik bilgisi yazılmaması
değişmedi; anahtar değerleri hiçbir çıktıya yazılmaz.

**Ek (24 Eylül 2026): Anthropic uç noktası, `MATHVERIFY_ANTHROPIC_BASE_URL`.** Anthropic SDK'sı
`base_url` verilmezse `ANTHROPIC_BASE_URL`'i ortamdan okur. Claude Code'u çalıştıran ortamlar (bulut
oturumu, masaüstü uygulaması) bu değişkeni Claude Code'un kendi trafiği için tanımlar ve her alt
süreç onu miras alır: gerçek bulut oturumunda tanımlı ölçüldü, `ANTHROPIC_API_KEY` ise tanımlı değil
(`docs/bulut_tani_2026-09-24.md`). Düzeltmeden önce projenin F3 çağrıları `.env`'deki anahtarla
platformun uç noktasına gidecekti. Artık `AnthropicClient` `base_url`'i her zaman açıkça verir
(`llm/anthropic_client.py::resolve_base_url`, commit `4002898`, DECISIONS §48):
`MATHVERIFY_ANTHROPIC_BASE_URL` tanımlı ve boş değilse o, değilse SDK'nın varsayılanı
`https://api.anthropic.com` (anthropic 1.7.0'dan okundu; bir test ikisini birbirine bağlar, SDK
yükseltmesi varsayılanı sessizce değiştiremez). Yerel davranış aynı kaldı: masaüstü oturumunda da
değişken tanımlı ve değeri varsayılana eşit ölçüldü. Testler: `tests/test_llm_base_url.py`
(10 çevrimdışı test, hiç istek gönderilmez).

Meta istemcisinin adresi sabittir (`https://api.meta.ai/v1/chat/completions`) ve ortamdan
etkilenmez. Ama `api.meta.ai` bulutun varsayılan (Trusted) ağında **kapalı** (vekil 403,
24 Eylül'de ölçüldü): F3/F4 bulutta koşulacaksa ağ ayarı Custom yapılır, varsayılan liste korunur ve
`api.meta.ai` eklenir. `api.anthropic.com` Trusted ağda açık ölçüldü (`docs/BULUT.md` §3.1).

Kod içinden model sabitlemek veya test için sahte istemci takmak:

```python
from mathverify.llm import set_client_override, clear_client_overrides
set_client_override("meta", my_client)
```

## Determinizm: kayıt/tekrar önbelleği

Güncel modellerde sıcaklık/seed parametreleri yok; determinizm bu önbellekten gelir. Her çağrı
(sağlayıcı, model, tüm istek parametreleri, sistem ve kullanıcı promptu, şema) SHA-256'sı ile
anahtarlanır.

| `MATHVERIFY_LLM_CACHE` | Davranış |
|---|---|
| `auto` (varsayılan) | Kayıt varsa tekrar oynatır, yoksa çağırıp kaydeder |
| `replay` | Ağa hiç çıkmaz; kayıt yoksa `CacheMiss` |
| `off` | Her zaman çağırır, kaydetmez |

## Maliyet

Sabit ön ek (talimatlar + 42 elle yazılmış örnek, ~10K token) sistem promptunda ve önbelleğe
alınmış olarak gönderilir; Anthropic tarafında okuma ~0.1x, Meta tarafında da ayrı bir "cached
input" tarifesi vardır. Ölçülen fiyatlar (USD / 1M token):

| Model | Girdi | Çıktı |
|---|---|---|
| `claude-opus-5` | 5.00 | 25.00 |
| `claude-fable-5-1` | 10.00 | 50.00 |
| `muse-spark-1.3` | 1.25 | 4.25 |
| `muse-spark-1.3-contributor` | 0.10 | 0.20 |

Her `LLMResponse` gerçek token sayımı ve hesaplanmış maliyeti taşır; harness raporları öğe
başına maliyeti yazar. `harness/run_f3.py --max-cost N` toplam harcama N dolara ulaşınca
taramayı durdurur. Sağlayıcı faturalama/kimlik hatası verirse tarama ilk hatada durur —
**20 Eylül 2026'da düzeltildi**, öncesinde durmuyordu (aşağıya bakın).

> Ölçülen maliyet: F3'ün ilk (yarım) koşusunda öğe başına **0,066 $**. Handoff'un 0,23 $
> kestirimi prompt caching eklenmeden önceydi.

Ölçüm durumu: F3'ün kendisi 218 öğenin 64'ünde ölçüldü, kalanı kredi bittiği için düştü.
**F4 (L6 kritik + meta-doğrulama) hiç koşmadı**; mantığı senaryolu istemcilerle test ediliyor
ve ölçüm hattı `--no-l6` bayrağı ile raporun "L6 kritik + meta-doğrulama (F4)" bölümü olarak
hazır, ama hiçbir sayısı yok.

## Yol (b): serbest metin çözüm

1. Deterministik nihai-cevap çıkarıcı (`\boxed{}`, "Cevap:", şık harfi, "limit yoktur"). IR'ın
   `answer_shape` alanı "(a, b)" ifadesinin aralık mı nokta mı olduğunu belirler; çözüm metnine
   bakılmaz.
2. LLM yeniden yapılandırma: metni **olduğu gibi** yapısal adımlara çevirir, hata düzeltmez.
   Ayrıştırılamayan iddia sessizce atılmaz, nota indirgenir ve raporlanır.
3. Çapraz kontrol: LLM'in çıkardığı cevap ile deterministik çıkarıcının cevabı karşılaştırılır;
   uyuşmazlık `restructure_answer_mismatch` bayrağıdır ve CORRECT'i engeller.

## Hata sınıflandırması

`LLMCreditError` ve `LLMAuthError` **`LLMFatalError`** altındadır ve bilerek `LLMError`'ın alt
sınıfı **değildir**. Her katman tek LLM çağrısını `except LLMError` ile sarıp başarısızlığı
kaydedilmiş bir "kullanılamadı" öğesine çevirir; bunlar da `LLMError` olsaydı boşalmış bir
bakiye 218 kez sessizce kaydedilirdi. Devam etmek isteyen, sınıfı adıyla yakalamak zorundadır.
Harness `fatal` alanını yapısal olarak işaretler ve ilk tanesinde taramayı durdurur; hangi
katmandan geldiği fark etmez (IR çıkarımı, L4, L5, kritik, Lean).

### Neden bu madde yeniden yazıldı

18 Eylül koşusu tam olarak bu güvenceyi ihlal etti: `reports/f3_results.json` içinde
`aborted: None` yazarken 151 öğe `Your credit balance is too low` ile düşmüştü. Zinciri:

1. `LLMCreditError` bir `LLMError`'dı → `extract_ir`'ın `except LLMError`'ı yuttu;
2. mesaj `str(e)[:120]` ile kırpıldı ve harness'in aradığı `credit` kelimesi **bir karakter
   önce** kesildi;
3. durdurucu o kırpılmış dizgiyi arıyordu → hiç ateşlemedi.

**Düzeltme (23 Eylül 2026).** "`aborted: None` yazarken" ifadesi dosyayla desteklenmiyor: o
koşunun `f3_results.json` dosyasında `aborted` anahtarı hiç yok, çünkü dosya bu alanı yazan
harness commit'inden (`828fb95`, 01:03) önce, 00:02'de yazılmış. Ölçülen kısım değişmiyor:
151/218 öğe aynı faturalama hatasıyla düştü, kırpılmış metin `'message': 'Your` ile bitiyor ve
`828fb95`'teki dizgi durdurucusu bu koşunun kendi kayıtlarında 0/218 ateşliyor
(`DECISIONS.md` §23).

Testteki hata da öğretici: `test_llm_error_stops_the_loop_and_is_reported` 24 karakterlik
sahte bir mesaj kullanıyordu, yani kırpmanın altında kalıyordu. Test artık sağlayıcının
gerçek mesajını kullanıyor; uzunluk fikstürün parçası.

## Çevrimdışı testler

F3/F4 mantığının tamamı ağ olmadan test edilir: `tests/conftest_llm.py` içindeki
`ScriptedClient` her role senaryolu yanıt verir, `set_client_override` ile takılır. Kapsanan
davranışlar: onarım döngüsü, iki aileli konsensüs, sızma savunması, L4/L5/L6 yetki sınırları,
önbellek anlamları.

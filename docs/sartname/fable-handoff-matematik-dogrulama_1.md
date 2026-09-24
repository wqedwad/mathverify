# AI Matematik Çözüm Doğrulama Aracı — Uygulama Dosyası (Ajan Devir Paketi)

**Bu doküman kime yazıldı:** Bu projeyi kodlayacak ajana (Claude Fable, Claude Code içinde).
**Ne içerir:** Araştırılmış kanıt tabanı + ölçülmüş davranış sözleşmeleri + modül bazında spec + kabul kapıları + yasaklar.
**Kaynak durumu:** Literatür iddiaları numaralı kaynaklara bağlı (§13). §6'daki E1–E10 bulguları **iddia değil**, SymPy 1.14.0 / mpmath 1.3.0 / z3-solver ile fiilen koşturulmuş ölçümlerdir.
**Tarih:** 18 Eylül 2026.

---

# BÖLÜM 0 — Ajana talimat: bu işe nasıl başlanır

Bu dokümanı bir "yap bunu" listesi olarak okuma. Sırayla üç şey yap:

1. **§2'deki 6 açık kararı kullanıcıya sor.** Bunlar mimariyi değiştirir. Cevap alamazsan §2'deki varsayılanları kullan ve hangi varsayılanı seçtiğini `DECISIONS.md` dosyasına yaz. Sessizce varsayım yapıp devam etmek bu projede en pahalı hatadır.
2. **Yalnızca Faz 1'i kur** (§10). Bütün 8 katmanı tek seferde yazmaya çalışmak, her modülü happy-path'te çalışan bir taslağa dönüştürür. §6'daki E3 ölçümü tam olarak bu tür bir sığlığın nasıl göründüğünü gösteriyor: naif `mp.quad` çağırmak "çalışıyor" gibi durur ama 4 basamak doğruluk verir ve doğrulayıcıyı yanlış karara sürükler.
3. **§6'daki assertion'ları ilk iş olarak `tests/` altına kendi test kodunla kur.** Hazır test dosyası veya referans implementasyon verilmedi — bu bilinçli bir tercih; tüm kodu sıfırdan yazacaksın. §6 bir girdi→beklenen-sonuç listesidir. Herhangi bir modül yazmadan önce testler yerinde olmalı; bunlar bu projenin davranış sözleşmesidir.

**Bu projede "çalışıyor" demenin tek geçerli kanıtı, §9'daki değerlendirme seti üzerinde ölçülmüş precision/recall sayılarıdır.** Kod koşuyor olması, testler geçiyor olması, örnek çıktının makul görünmesi kanıt değildir. Ölçüm seti yoksa önce onu kur (§9), sonra modül yaz.

---

# BÖLÜM 1 — Ürün tanımı ve çıktı sözleşmesi

**Girdi:** Bir matematik sorusu (Türkçe, TYT/AYT formatında çoktan seçmeli veya üniversite seviyesi açık uçlu) + bir AI'ın ürettiği çözüm. Opsiyonel: cevap anahtarı.

**Çıktı:** Üç değerli karar, güven skoru ve kanıt zinciri.

```python
from dataclasses import dataclass
from typing import Literal, Any

Verdict = Literal["CORRECT", "INCORRECT", "UNKNOWN"]

@dataclass
class LayerResult:
    layer: str                  # "certify.integral", "equiv.sympy", ...
    verdict: Literal["pass", "fail", "unknown"]
    confidence: float           # 0.0 - 1.0
    hard: bool                  # True ise füzyonda VETO yetkisi var (deterministik kanıt)
    evidence: dict[str, Any]    # {"code": str, "output": str, "seed": int, ...}
    latency_ms: float
    cost_usd: float = 0.0

@dataclass
class VerificationResult:
    verdict: Verdict
    confidence: float
    first_bad_step: int | None      # yalnızca deterministik katman lokalize ettiyse doldurulur
    layers: list[LayerResult]
    decision_trace: str             # insan okunur gerekçe
    versions: dict[str, str]        # sympy/mpmath/z3/model sürümleri — karara yazılır
```

**Üç değerli olmak isteğe bağlı değil, ürünün özüdür.** İki değerli bir doğrulayıcı (her girdiye DOĞRU/YANLIŞ demek zorunda olan) matematiksel olarak yanlıştır: §6/E1'de göreceğin gibi bazı sorular için SymPy'nin kendisi bile "karar veremiyorum" (`None`) döndürüyor, ve elementer ifadelerde sıfır-testi genel olarak **karar verilemez** bir problemdir (Richardson teoremi [24]).

**Hedef metrikler:**
- Pozitif precision (CORRECT dediğinde haklı olma oranı) **≥ 0.98**
- Negatif precision (INCORRECT dediğinde haklı olma oranı) **≥ 0.98**
- Kapsama (UNKNOWN olmayan oran): **hesaplama soruları ≥ 0.85**; **ispat soruları ayrı raporlanır** ve düşük kapsama beklenir (D3/D5: süre sınırı olmadığı için katmanların tamamı açık, bu yüzden hesaplama tarafında hedef yükseltildi)

Precision hedefleri kapsamadan önce gelir. Kapsamayı yükseltmek için precision'dan feragat etme — bir doğrulama aracında yanlış onay, cevapsız kalmaktan çok daha kötüdür.

---

# BÖLÜM 2 — KİLİTLENMİŞ KARARLAR (ürün sahibi onaylı, 18.09.2026)

Bu kararlar alındı; yeniden sorma, bu varsayımlarla ilerle.

| # | Karar | Değer | Mimari sonucu |
|---|---|---|---|
| **D1** | Çözümün kaynağı | **İkisi de**: (a) uygulama soruyu bir AI'a kendisi soruyor, (b) kullanıcı dışarıdan aldığı çözümü getiriyor | **İki ayrı intake yolu, ortak IR.** (a) yolunda çözücüye yapısal format zorunlu kılınır (§3, [1]). (b) yolunda "restructuring pass" gerekir ve o pass'in sadıklığı **ayrıca ölçülür** — sessiz anlam kaybı burada olur |
| **D2** | Cevap anahtarı | **Doğrulayıcı anahtarı GÖRMEZ.** Anahtar elde olsa bile doğrulama hattına girmez | Bkz. §4.1 — anahtar izolasyonu. `problem_ir` içinde `gold_answer` alanı **bulunmaz**. Anahtar yalnızca değerlendirme harness'inde ground truth olarak kullanılır (§9) |
| **D3** | Gecikme / maliyet | **Süre sınırı yok; doğruluk ve kalite birincil** | L5 (metamorfik), L6 (adım grafiği), **L7 (Lean/Mathlib)** ve verifier topluluğu + kalibrasyon **kapsam içinde**. Tek kısıt maliyet: soru başına **$0.30–1.00** üst sınır kabul edilebilir. Erken çıkış yine uygulanır (ucuz katman kesin karar verdiyse pahalı katman koşmaz) ama "yetişmedi" diye katman atlanmaz |
| **D4** | Çalışma ortamı | Tamamen API; yerel GPU yok | Yerel 7B–32B verifier yok. Lean konteynerde, prebuilt Mathlib cache'li imajla çalışır |
| **D5** | Kapsam | Lise (TYT/AYT) **ve** üniversite seviyesi; **ispat soruları dahil** | İspat kümesinde UNKNOWN oranı yüksek olacak — bu kusur değil, alanın gerçeği ([1]: recall 0.609; [30]: araştırma seviyesinde tüm modeller %20 altında). İspat sonuçları **ayrı raporlanır**, genel metriği kirletmez |
| **D6** | Hata maliyeti | Yanlışı onaylamak, doğruyu reddetmekten daha pahalı | Abstain eşiği precision lehine kurulur. Şüphede UNKNOWN |

---

# BÖLÜM 3 — Kanıt tabanı: neden tek katmanlı hiçbir çözüm yeterli değil

Bu tablo mimarinin gerekçesidir. Bir katmanı atlamak istediğinde buraya bak.

| Yaklaşım | Ölçülen performans | Kritik zafiyet | Kaynak |
|---|---|---|---|
| LLM-as-judge (referanssız) | Referans eklendiğinde kararların **%85'e kadarı değişiyor** | Referanssız iken aşırı cömert | [8] |
| Düz LLM ile doğrulama | 50 doğru çözüm yakalandı, **85 false positive** | Kullanılamaz precision | [1] |
| Self-verification (aynı model) | En küçük kazanç; FPR artıyor; güçlü çözücüde ~sıfır fayda | Model kendi hatasını görmüyor | [6] |
| Cross-family doğrulama | En büyük kazanç (çapraz aile > aynı aile > self) | — tasarım ilkesi | [6] |
| Kural tabanlı CAS | Precision **>%99**, recall **0.78–0.92** | Eşdeğer ama farklı formdaki cevabı reddediyor ("0.5π" vs "90°") | [12] |
| Eski regex grader'lar | Math-Verify'a geçişte leaderboard ort. **+4.66 puan**, bazı modelde ~+90 | Ölçülen "model hatası" aslında grader hatasıydı | [13] |
| PRM (Skywork-7B) | ProcessBench F1: GSM8K 70.8 → OlympiadBench **22.9** | Zor problemde çöküyor | [3] |
| En iyi PRM (Qwen2.5-Math-PRM-72B) | ProcessBench ort. **78.3 F1** | Akıl yürüten kritik modellerin altında | [3] |
| Kritik model (o1-mini sınıfı) | 93.2 / 88.9 / 87.2 / 82.4 F1 | Maliyet + kalibrasyon yok | [3] |
| Model tabanlı verifier (RL'de) | Adversaryal önek saldırısı: generatiflerde **%15–77** başarı; diskriminatif xVerify-3B'de %0.2–1.1 | Reward hacking; "{" gibi çöple kandırılıyor | [12] |
| Lean 4 autoformalizasyon | **%89.5 derleniyor, %60.5 sadık** → %29 puan boşluk; prover modellerinde sadıklık %4–5 | Derleme ≠ doğru şartname | [5] |
| Lean tabanlı uçtan uca hat | Precision **0.942–0.984**, recall **0.609**; geometri kapsam dışı | Mükemmel precision, yarı recall | [1] |
| SymPy+Z3 adım doğrulama (MATH-VF) | MATH500'de **%93.2–95.7** doğrulama doğruluğu; ProcessBench 74.1 F1 (eğitimsiz) | Formalizasyon sözdizim hataları | [9] |
| Uzmanlaşmış verifier modelleri | xVerify-3B %97.2 F1 (referanslı); CompassVerifier-32B matematikte %84.1 acc (GPT-4o %63.9) | Referanslı senaryoda iyi, referanssızda değil | [11][14] |
| Zayıf verifier topluluğu (Weaver) | Majority voting'e göre **+15.5 puan**; naive ortalama Weaver'dan **17.1 puan** geride | Kalibrasyon için %1–5 etiketli veri şart | [7] |
| Self-consistency | 2026 modellerinde MATH-500'de **+1.6 puan / ~15× token**; 15 örnekten sonra düşüyor | Artık birincil sinyal değil | [15] |
| Majority vote ile *doğrulama* | Örnek artırmak doğruluğu %76 → **%32**'ye düşürebiliyor | Sistematik hatayı büyütüyor | [10] |
| Kanonik olmayan doğru çözümler | False rejection **%75.56–85.28**; ilk hatalı adım tespiti %95 → **%14–24** | "Template sensitivity" | [10] |

### Bu tablodan çıkan 6 kural (ihlal edilmemeli)

1. Referanslı ve referanssız yollar **ayrı hatlar**. [8]
2. Sıra **kural tabanlı → model tabanlı** (yalnızca işaretlenene). Hibrit: >%98 precision + ~3 puan recall kazancı. [12]
3. Çözücü ve doğrulayıcı **asla aynı model ailesi/aynı çağrı** olmayacak. [6]
4. Formal katman yalnızca **pozitif** kanıt üretir; "kanıtlayamadım" ≠ "yanlış". [1]
5. Formalizasyon sadıklığı **ayrı ve ölçülen** bir bileşen. Derleme başarısı yanıltıcıdır. [5][17]
6. Doğrulayıcı **kanonik olmayan doğru çözümlerle** test edilmeden yayına alınmaz. [10]

### Ek olarak bilinmesi gereken 4 içgörü

- **Darboğaz kontrol değil, şartname.** Lean/Z3/SymPy kontrol tarafını neredeyse bedava çözüyor; hata bütçesinin tamamı doğal dildeki problemi doğru matematiksel nesneye çevirmekte. [5]'teki %29 puanlık boşluk ve [1]'deki 0.61 recall aynı olgunun iki yüzü.
- **Yapı doğrulanabilirliği satın alır.** [1]'in en önemli bulgusu mimari değil sözleşme: çözücüden her adımı *tek sonuçlu, öncülleri açıkça referanslı* bir lemma olarak yazması istendiğinde formalizasyon başarısı ve doğruluk birlikte yükseldi. Serbest CoT doğrulanamaz.
- **Trajektori uzunluğu negatif sinyaldir.** Tool-feedback'li formalizasyonda 1–2 adımda sadıklık %81.3, 19–24 adımda **%12** [5]. "Sonunda derledi/geçti" güveni **düşürür**, yükseltmez. Güven skoruna negatif katkı olarak gir.
- **Meta-doğrulama en ucuz FP düşürücüdür.** Verifier'ın "tespit ettiğin hata gerçekten var mı?" diye denetlenmesi ortalama kaliteyi 0.85 → **0.96**'ya çıkardı [4]. Kritik model çıktısı ham kabul edilmez.

---

# BÖLÜM 4 — Mimari

```
[soru + AI çözümü (+ opsiyonel anahtar)]
   │
L0 NORMALİZASYON   OCR/LaTeX kanonikleştirme · TR→EN iç temsil · tip sınıflandırma · çözüm şemasına dönüştürme
   ▼
L1 PROBLEM IR      sembolik problem nesnesi (§5) + round-trip sadıklık kontrolü
   ▼
L2 EŞDEĞERLİK      (anahtar varsa) Math-Verify + latex2sympy2_extended + mpmath        [hard]
   ▼
L3 SERTİFİKA       ters işlem / yerine koyma / brute-force / domain guard (§7)          [hard]
   ▼
L4 YENİDEN ÇÖZÜM   sembolik çözücü + çapraz-aile LLM+kod · ÇS'de şık eleme & teklik     [hard: teklik]
   ▼
L5 METAMORFİK      parametre değiştir / ters problem / dejenere değer kontrolü
   ▼
L6 ADIM KONTROLÜ   çözüm grafiği → kenar başına SymPy/Z3 + çapraz-aile kritik + meta-doğrulama
   ▼
L7 FORMAL          Lean 4 + Mathlib (Kimina server) + sadıklık + aksiyom denetimi — yalnız POZİTİF
   ▼
L8 FÜZYON          kalibre ağırlıklı Naive-Bayes + abstain eşiği → VerificationResult
```

**Füzyon kuralları (uygulanması zorunlu):**
- `hard=True` katman kesin sonuç verdiğinde LLM sinyalleri onu **veto edemez**.
- Hiçbir yumuşak sinyal tek başına ne CORRECT ne INCORRECT üretebilir.
- Katman çıktıları **ortalanmaz**, kalibre edilir: naive ortalama Weaver'dan 17.1 puan geride [7].
- Güveni düşüren sinyaller: uzun düzeltme trajektorisi [5], IR round-trip uyuşmazlığı, CAS timeout, katmanlar arası çelişki, cevabın bilinen çeldirici kalıbına uyması.

## 4.1 — Üç hesap türü ve anahtar izolasyonu (D2'nin gerekçesi)

Bu alt bölümün kuralı ürün sahibinin doğrudan talimatıdır: **araç, cevabı kendisi üretip karşılaştırarak karar vermez; verilen iddiayı sınayarak karar verir.** Hesabın rolü "cevabı çıkarmak" değil "iddiayı sınamak"tır — sınamanın kendisi elbette bir hesaptır ve her nicel iddia için kod yürütülür. Doğrulamanın üç hesap türü vardır ve **yetkileri farklıdır**:

| Tür | Ne yapar | Güç | Yetki |
|---|---|---|---|
| **Üreten hesap** (L4) | Problemi baştan çözer, kendi cevabını verilen cevapla karşılaştırır | Zayıf — çözücünün hata modlarını miras alır; aynı model ailesindeyse hatalar korele olur [6] | **Verdict üretemez.** Yalnızca güveni düşürür / UNKNOWN'a iter. Çapraz aile zorunlu |
| **Kontrol eden hesap** (L3) | Verilen iddiayı sınar: türev alır, kökü yerine koyar, tanım kümesini denetler, teklik testi yapar | **En yüksek** — asimetrik ve ucuz; cevabı üretmeden doğruluğunu kanıtlar | `hard=True`, **veto yetkisi var** |
| **Saf mantık kontrolü** (L6, hesapsız) | Verilen adımların birbirini takip edip etmediğine bakar | **En düşük** — kanonik olmayan geçerli çözümlerde false rejection %75–85, ilk hata lokalizasyonu %95 → %14–24 [10]; en iyi PRM'ler 78.3 F1 [3] | Tek başına **asla** karar veremez |

**L4'ün yetkisi (bağlayıcı kural).** L4 kendi cevabını üretse bile o cevap **hiçbir zaman verdict üretmez**. İki meşru kullanımı vardır: (i) uyuşmazlık → güveni **düşürür** ve gerekirse UNKNOWN'a iter; (ii) çoktan seçmelide şık eleme — ki bu üretme değil sınama formudur. `LayerResult.hard` bayrağı L4 için yalnızca teklik testinde (E7) True olabilir; serbest yeniden çözümde asla.

**Saf mantık kontrolü neden tek mekanizma olamaz.** Bir çözüm adım adım tutarlı görünüp yanlış cevaba varabilir; ya da doğru cevaba geçersiz bir adımla varabilir — ikincisi ProcessBench'in en zor sınıfıdır ve mevcut PRM'lerin yapısal olarak kaçırdığı yerdir [3]. Ayrıca adım geçerliliğini kontrol etmek zaten hesap gerektirir: `3x+2=14 → x=4` adımının doğruluğu ancak hesaplanarak sınanır. Küçük modellerde doğrulama hatalarının kaynağının akıl yürütme değil aritmetik/bellek olduğu, araç verilince düzeldiği ölçülmüştür [16]. Dolayısıyla: **her nicel iddia için kod yürütme zorunlu, LLM'e hiçbir aritmetik bırakılmaz.**

**Anahtar izolasyonu (D2).** Anahtar elde olsa bile doğrulayıcı hattına sokulmaz. İki gerekçe:

1. **Sinyal bastırma.** LLM yargıcı referans cevabı görünce kararlarının %85'e kadarını değiştiriyor [8]. Anahtar hatta girdiği anda diğer tüm sinyalleri bastırır ve sistem "anahtara uyuyor mu" kontrolüne dejenere olur — yani gerçek bir doğrulayıcı olmaktan çıkar, bir karşılaştırıcı olur. Yeni/anahtarsız sorularda ne kadar iyi çalıştığını da bir daha asla bilemezsin.
2. **Anahtar dışarıda tutulunca bedava ground truth'a dönüşür.** Çıkmış soru + anahtarı, doğrulayıcının *kendisini* ölçmek için hazır etiketli veridir (§9). Hatta girerse bu ölçüm imkânı yok olur.

Mühendislik sonucu: `problem_ir` şemasında `gold_answer` alanı **yoktur**; değerlendirme harness'i anahtarı ayrı bir yapıda tutar ve doğrulayıcıya asla geçirmez. Sızma (leakage) testi §11/madde 15'te.

---

# BÖLÜM 5 — Problem IR

IR'ın iki katmanı var. Tek katmanlı (yalnız skaler kısıt) bir IR sözel problem için doğru, AYT için yetersizdir.

```json
{
  "vars":      [{"name":"x","domain":"real","constraints":["x>0"]}],
  "givens":    ["3*x + 2*y == 12", "y == x - 1"],
  "functions": [{"name":"f","expr":"(2*x+3)/(x-1)","domain":"x != 1","params":["m"]}],
  "operators": [{"kind":"integral","arg":"f","wrt":"x","bounds":["0","1"]}],
  "unknown_of_interest": "x*y",
  "answer_shape": "scalar | expression | set | interval | condition_on_param | count | proof",
  "options":   {"A":"6","B":"8","C":"9","D":"10","E":"12"},
  "units":     null,
  "sanity":    ["0<=p<=1", "uzunluk>0", "tam sayı beklenir"],
  "domain_of_discourse": "x in (0, oo)"
}
```

**`domain_of_discourse` alanı kritiktir ve ifadelerden türetilemez, problemden gelmelidir.** §6/E4'te ölçüldü: `log(x²)` ile `2·log(x)` ifadelerin kendi tanım kümelerinin kesişiminde eşittir, ama problem reeller üzerinde tanımlıysa eşit değildir. Alanı ifadelerden çıkarırsan doğrulayıcı yanlış cevabı onaylar.

**IR round-trip kontrolü zorunlu:** IR'ı doğal dile geri çevir, orijinal soruyla **iki farklı model ailesine** karşılaştırt, ikisi de ≥9/10 vermezse UNKNOWN döndür. Bu ucuz testin gücü ölçülmüş: consensus-pozitif çıktıların %96'sı insan onaylı sadık, compile-pass consensus-negatiflerin %82.4'ü gerçekten hatalı [5].

---

# BÖLÜM 6 — Ölçülmüş davranış sözleşmeleri (E1–E10)

**Bunlar literatürden değil ölçümden gelir: aşağıdaki değerler SymPy 1.14.0 / mpmath 1.3.0 / z3-solver ile fiilen koşturularak alınmıştır.** Bu bölüm referans implementasyon değil, bir **assertion listesi**dir — test kodunu sıfırdan sen yazacaksın, ama testler aşağıda yazılı davranışları doğrulamalı. Bunlar tasarım tercihi değil, kütüphanelerin fiili davranışıdır; kendi ölçümün farklı çıkarsa **dur ve raporla** (ya sürüm farkı vardır ya da testin yanlıştır — ikisi de bilinmesi gereken şeydir), sessizce beklentiyi değiştirme.

### E1 — Sonsuz çözüm kümesi eşitliğini SymPy karar veremiyor

`solveset(cos(2x)=1/2, Reals)` → ImageSet birleşimi. Aday kümeyle `==` → **False** (yapısal karşılaştırma), `is_subset` → **None** (karar verilemedi).
**Kural:** trigonometrik genel çözümler asla doğrudan karşılaştırılmaz. Periyot tespit edilir, tek periyotta küme eşitliği kontrol edilir. Ölçüm: **165 ms, doğru karar**.

**Uygulanacak yöntem:** periyodu tespit et → denklemi `Interval.Ropen(0, P)` üzerinde çöz → aday kümenin temsilcilerini `Mod(v, P)` ile aynı pencereye indir → iki **sonlu** kümeyi karşılaştır.
**Assertion:** `cos(2x)=1/2`, `P=π` için her iki taraf da `{π/6, 5π/6}` vermeli, karar `True` olmalı. Ayrıca `solveset(...) == aday` ifadesinin `False`, `is_subset`'in `None` döndürdüğü de test edilmeli — bu tuzağa geri dönülmesin.

### E2 — `solve` ve `solveset` birbiriyle çelişiyor

`log(x−1)+log(x−3)=log 3` için: `solve` → `[4]` (doğru), `solveset` → **`{0, 4}`** (x=0 tanım kümesi dışında, yabancı kök).
`√(x+4)=x−2` için naif kareleme → `[0, 5]` (0 yabancı).
**Kural:** hiçbir çözücü API'si tek başına güvenilir değildir. Her aday kök **orijinal** ifadede ve tanım koşullarında sınanır. Ölçüm: aşağıdaki guard ikisini de temizliyor → `[4]`, `[5]`, **38 ms**.

**Uygulanacak yöntem:** ifade ağacını gez ve tanım koşullarını topla (`log(u)` → `u > 0`; `sqrt(u)` veya `u**(1/2)` → `u ≥ 0`; negatif üslü `u**(-n)` → `u ≠ 0`; ayrıca IR'dan gelen `domain_of_discourse`). Her aday kökü **hem** bu koşullara **hem de** orijinal ifadeye sınat (sadeleştirilmiş fark sıfır mı). Çözücünün döndürdüğü listeyi asla doğrudan kabul etme.
**Assertion:** `log(x−1)+log(x−3)=log 3` → `solveset` `{0,4}` verir, guard `[4]` bırakmalı. `√(x+4)=x−2` → naif kareleme `[0,5]` verir, guard `[5]` bırakmalı. `solve` ile `solveset`'in bu iki vakada farklı sonuç verdiği de ayrıca test edilmeli.

### E3 — Nümerik integralde kırılma/tekillik tespiti zorunlu; sabit tolerans false negative üretir

- `∫₀¹ ln x/√x dx` (gerçek: −4): SymPy **6.6 s sonra çözemedi** (meijerg yığını döndürdü). Naif `mp.quad` → −3.99999997553 (**8 basamak**). `method='tanh-sinh'`, dps=40 → **−4.0**. Değişken değişimi → −4.0.
- `∫₋₃³ (|x−1| + |x+2|) dx` (gerçek: 23): naif `mp.quad` → 22.9994651291 (**4 basamak**). Kırılma noktaları `[-3, -2, 1, 3]` verilince → **23.0**.

**Kural:** integrand'daki `Abs`/`sign`/`floor`/`ceiling` argümanlarının sıfırları ve tekillikler önce çözülür, `quad`'a nokta listesi olarak verilir; tanh-sinh + yüksek dps kullanılır; karşılaştırma **göreli** toleransla yapılır ve gerekirse basamak artırılır. Sabit `1e-12` eşiği doğru cevabı reddeder. Ölçüm: **55 ms**.

### E4 — Rastgele nokta testi alan-farkında olmalı

`√(x²)` vs `x`: yalnızca pozitif noktalardan örneklenirse test **"eşit" diyor** (30 noktada geçti). Negatif noktalar dahil edilince False.
`log(x²)` vs `2 log x`: ifadelerin tanım kümesi kesişiminde (x>0) **eşit** — verdict bildirilen alana bağlı.
**Kural:** örnekleme alanı **IR'dan** gelir (§5), ifadelerden türetilmez. `continuous_domain` pahalı (**~2.3 s**) → cache'lenir.

### E5 — Ekstremum sorularında iki taraflı sertifika şart

`f(x)=x³−3x`, `[−2,3]`, iddia max=18: kritik noktalar + uçlar `[(−1,2), (1,−2), (−2,−2), (3,18)]` → max 18. **Ayrıca** `{x ∈ [−2,3] : f(x) > 18} = ∅` boşluk kanıtı.
**Kural:** adayın sağlanması yetmez; **daha iyisinin olmadığı** ayrıca kanıtlanır. Ölçüm: **51 ms**.

### E6 — Limitte her zaman iki tek yönlü limit hesaplanır

`limit(|x|/x, x, 0)` → **1** döndü (yanıltıcı; SymPy varsayılanı sağdan). Tek yönlüler `(1, −1)`.
`limit(sin(1/x), x, 0)` → `AccumBounds(-1, 1)`.
**Kural:** sınıflandırıcı: `AccumBounds` → DNE; tek yönlüler farklı → DNE; `oo/-oo/zoo` → INF; aksi → VAR. Ölçüm: **7 ms**.

### E7 — Çoktan seçmeli teklik testi doğrulandı

`a+b=30 ∧ 2a+4b=88 ∧ a,b>0` → z3 `sat`, `a=16, b=14`. `∧ a≠16` → **`unsat`**.
**Kural:** ÇS sorularında sertifika = `sat(kısıtlar ∧ şık)` **ve** `unsat(kısıtlar ∧ şık≠cevap)`. Sonuçların yorumu:
- tam olarak 1 şık `sat` → cevap sertifikalı (çözücünün akıl yürütmesine hiç güvenmeden)
- ≥2 şık `sat` → **IR eksik/hatalı**, IR'a geri dön
- 0 şık `sat` → IR hatalı veya soru tutarsız → UNKNOWN + bayrak

### E8 — İntegral sabiti sorunu türev sertifikasıyla kendiliğinden çözülür

`d/dx(x ln x − x) − ln x` → **0**. Yanlış ilkel `x ln x` için fark → **1** (yakalandı). `F+7` için fark → yine **0**.
**Kural:** belirsiz integral cevaplarında sabit farkı asla hata sayılmaz; türev sertifikası bunu otomatik halleder.

### E9 — Karmaşık sayı/dal kesiği vakalarında sembolik yol tıkanır

`simplify(i^i)` → `I**I` (sadeleşmedi), `expand_complex` → aynı. `N(i^i)` → **0.207879576350762**.
**Kural:** karmaşık sayı ve dal kesiği içeren doğrulamalarda **nümerik ana yol**, sembolik destek.

### E10 — Kök/tam sayı sayımı kesin ve ucuz

`x⁵−3x³+x+1`: `Poly.count_roots(-oo, oo)` = 3, `real_roots` = 3, **7 ms** (Sturm).
`x²−5x−14<0` → `Interval.open(-2,7)`, içinde **8 tam sayı**.
**Kural:** "kaç kök / kaç tam sayı" soruları Sturm + aralık sayımıyla kesin doğrulanır; asla nümerik tahminle değil.

**Toplam:** AYT'ye özgü 10 zor vakanın tamamı deterministik doğrulanabiliyor, tipik maliyet **7–170 ms**. Tek pahalı nokta alan hesabı (~2.3 s, cache). Sonuç: bu iş LLM katmanına sanıldığından **çok daha az** yük bırakıyor.

---

# BÖLÜM 7 — Modül bazında spec

Her modül: `verify(problem_ir, claimed_answer, solution_steps) -> LayerResult`. Hepsi ayrı süreçte, timeout'lu, deterministik (sabit seed).

| Modül | Sertifika | Kabul kriteri | Bilinen tuzak |
|---|---|---|---|
| `equiv/` | Math-Verify + latex2sympy2_extended + göreli toleranslı nümerik | Eşdeğer form çiftlerinde recall ≥0.95, FP=0 | Rule-based recall 0.78–0.92 [12]; "0.5π vs 90°" |
| `certify/algebra.py` | Kökleri yerine koy + kök sayısını CAS ile doğrula | E2 yeşil | Kayıp/yabancı kök; `solve` vs `solveset` çelişkisi |
| `certify/wordproblem.py` | IR kısıtlarına cevabı koy → z3 `sat`; teklik için `unsat(∧ x≠a)` | E7 yeşil | IR eksikse ≥2 şık sat olur — bunu hata olarak raporla |
| `certify/calculus.py` | İntegral→türevle; belirli integral→kırılma noktalı tanh-sinh; ODE→yerine koy | E3, E8 yeşil | Sabit tolerans; tekillik; parçalı fonksiyon |
| `certify/limits.py` | İki taraflı tek yönlü + AccumBounds sınıflandırma | E6 yeşil | SymPy `limit` varsayılanı sağdan |
| `certify/extremum.py` | Kritik+uç noktalar **ve** `{f>iddia}=∅` | E5 yeşil | Tek taraflı kontrol yetersiz |
| `certify/counting.py` | Sturm `count_roots` + aralıkta tam sayı sayımı | E10 yeşil | Nümerik kök tahmini kullanma |
| `certify/trig.py` | Periyoda indirgeyip küme eşitliği | E1 yeşil | `is_subset` → None; doğrudan karşılaştırma |
| `certify/combinatorics.py` | Küçük n brute-force + Monte Carlo + `0≤p≤1` & toplam=1 | Bilinen 20 vakada FP=0 | Büyük n'de brute-force patlar — n eşiği koy |
| `certify/linalg.py` | Matris çarpımı / Ax=b / özdeğer denklemi | Kesin | — |
| `certify/series.py` | Kısmi toplam yakınsama + kapalı formu n=1..20 test; `rsolve` | Rekürans vakalarında yeşil | — |
| `certify/geometry_numeric.py` | Kısıtları sağlayan rastgele konfigürasyon üret, hedefi ölç, çok kez tekrarla | TYT geometri setinde precision ≥0.98 | Dejenere konfigürasyon; tek konfigürasyona güvenme |
| `certify/domain.py` | log argümanı>0, karekök≥0, payda≠0, tanım kümesi | E2 yeşil | En sık AYT tuzağı |
| `equiv/random_point.py` | Alan-farkında rastgele nokta testi, sabit seed | E4 yeşil | Alan IR'dan gelmeli |
| `meta/metamorphic.py` | Parametre değiştir / dejenere değer / ölçek değişmezliği | "Doğru cevap yanlış yöntem" vakalarında tespit >%50 | — |
| `steps/` | Çözüm grafiği + kenar başına SymPy/Z3 + kritik + meta-doğrulama | ProcessBench'te ≥0.74 F1 [9]; kanonik-olmayan altkümede false rejection <%10 | [10]: %75–85 false rejection riski |
| `formal/` | Lean 4 + Kimina server + sadıklık + aksiyom/`sorry` denetimi | "pass" dediğinde FP=0 | Trivial ispat FP'si [1]; aksiyom kaçağı [30] |
| `fuse/` | Kalibre Naive-Bayes + abstain | Hedef precision'da kapsama ≥%70 | Naive ortalama kullanma [7] |

**Teorik sınır:** genel elementer ifadelerde "bu sıfır mı?" **karar verilemez** (Richardson [24]) ve `simplify` sonsuza takılabilir (SymPy'de açık issue'lar [25]). Bu yüzden **her CAS çağrısı sert timeout'lu alt süreçte**; timeout → alan-farkında rastgele nokta testine düş; o da kararsızsa UNKNOWN. Polinomsal durumda rastgele nokta testinin hata olasılığı Schwartz–Zippel ile sınırlanabilir [26].

---

# BÖLÜM 8 — Sınav gerçekleri ve router tablosu

**TYT Temel Matematik: 40 soru = 30 matematik + 10 geometri.** Matematik içinde **problemler 10–13 soru** (tek en büyük blok); temel kavramlar/sayılar 6–9; permütasyon-kombinasyon-olasılık 2–5. Geometride üçgenler 2–5, dörtgenler 2–4, katı cisimler ~2. [32][33]

**AYT Matematik: 40 soru**, geometri **7–10** (2018–2025 ort. ~9). 2018–2025 toplamlarında en ağır bloklar: trigonometri 34, analitik geometri ~26, integral 22, türev 21, fonksiyonlar 21, çember/daire 14. [34][35]

**Bu iki dağılım farklı öncelik demektir:**
- **TYT'de** en yüksek getirili modül `certify/wordproblem.py` (z3) — 10–13 soru tek modülle kesinleşir.
- **AYT'de** o blok yok; en yüksek getirili modüller `certify/calculus.py`, `certify/trig.py`, `certify/domain.py` ve analitik geometri. z3'ün rolü sözel problemden **parametre koşulu ve teklik testine** kayar.
- **Geometri riski terstir:** TYT geometrisi zor olan (sentetik üçgen/dörtgen/katı cisim → nümerik realizasyon motoru şart), AYT geometrisi doğrulama açısından kolay (analitik + çember → koordinat kurulup kesin doğrulanır).

| Tip | L2 | L3 | L4 | L5 | L6 | L7 | Beklenti |
|---|---|---|---|---|---|---|---|
| TYT temel kavramlar/sayılar | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ `norm_num` | ~Kesin |
| TYT sözel problem (10–13) | ✓ | ✓✓ z3 | ✓ | ✓ | ✓ | ○ | Kesin (IR doğruysa) |
| Kümeler/mantık | ✓ | ✓ | ✓ | – | ✓ | ✓ `decide` | Kesin |
| Permütasyon/olasılık | ✓ | ✓✓ brute-force | ✓ | ✓ | ✓ | ○ | Kesin (küçük n) |
| Fonksiyon/polinom/eşitsizlik | ✓ | ✓✓ | ✓ | ✓ | ✓ | ✓ `nlinarith`/`polyrith` | Kesin |
| Trigonometri (AYT ağır) | ✓ | ✓✓ periyot+açı | ✓ | ✓ | ✓ | △ | Yüksek |
| Türev/İntegral (AYT ağır) | ✓ | ✓✓ ters işlem | ✓ | ✓ | ✓ | △ | Kesin |
| Sentetik geometri (TYT 10) | ✓ | ✓✓ nümerik realizasyon | ✓ | ✓ | △ | ✗ | Yüksek (en riskli) |
| Analitik geometri (AYT ağır) | ✓ | ✓✓ | ✓ | ✓ | ✓ | △ | Kesin |
| Üniv. lineer cebir | ✓ | ✓✓ | ✓ | ✓ | ✓ | △ | Kesin |
| Üniv. reel analiz (hesaplama) | ✓ | ✓✓ mpmath | ✓ | ✓ | ✓ | △ | Yüksek |
| Üniv. ispat | ✗ | ✗ | △ | △ | ✓✓ | △ | **Kısmi — UNKNOWN yüksek** |
| Kompleks analiz / ODE nitel | ✗ | ✓ nümerik | ✓ | ✓ | ✓ | ✗ Mathlib boşluğu | Orta |

✓✓ birincil kanıt · ✓ destek · △ koşullu · ○ düşük değer · ✗ kullanma

**Mathlib'de eksik olan üniversite konuları (resmî liste [31]):** Jordan normal formu, satır indirgeme/köşegenleştirme, sonlu grup temsil teorisi, karakter teorisi, kısmi kesirlere ayırma, konikler/kuadrikler, izometri-benzerlik, has olmayan integraller, Cauchy–Riemann, Laurent serileri, rezidü teoremi, dolanım sayısı, Sobolev uzayları, ODE'de maksimal çözüm/kararlılık, Lagrange çarpanları, konvolüsyon, Dirichlet/Fejér, dağılımlar, LU/Newton/FFT. **Bu bloklarda L7 devre dışı bırakılır.**

**Türkçe parse notları:** ondalık ayırıcı **virgül**, binlik ayırıcı **nokta** ("10.000") — parse hatası kaynağı #1. OBEB/OKEK = gcd/lcm. "en az/en çok", "ardışık", "birbirinden farklı" kalıpları IR'a kısıt olarak çevrilir. İç akıl yürütme ve formalizasyon **İngilizce+LaTeX kanonik temsilde** yapılır (Türkçe/düşük kaynaklı dilde akıl yürütme boşluğu ölçülmüş: bir örnekte 96.5% → 29.3%, baskın sebep "anlama" aşaması, performans çeviri kalitesiyle r=0.951 korele [18]); kullanıcıya dönen açıklama Türkçeye çevrilir.

---

# BÖLÜM 9 — Değerlendirme seti spesifikasyonu

**Bu set olmadan proje değerlendirilemez. Modül yazmadan önce kur.** Minimum 60, hedef 200 soru. Kritik olan sayı değil, **4 hücrenin hepsinin dolu olması**:

| Hücre | İçerik | Neden zorunlu | Min. oran |
|---|---|---|---|
| **A** | Doğru cevap + kanonik/beklenen çözüm yolu | Temel pozitif | %30 |
| **B** | **Doğru cevap + alışılmadık ama geçerli yol** | Bu hücre yoksa %75–85 false rejection'la ürün çıkar [10] | %25 |
| **C** | Yanlış cevap (hata enjeksiyonlu) | Temel negatif | %30 |
| **D** | **Doğru cevap + geçersiz ara adım** | Mevcut PRM'lerin yapısal olarak kaçırdığı sınıf [3] | %15 |

**Anahtarlı çıkmış sorular burada kullanılır (D2).** Doğrulayıcı anahtarı görmediği için, elde anahtarı olan her soru **bedava etiketli satır** demektir: A ve C hücrelerini doldurmanın en ucuz yolu budur — soruyu bir AI'a çözdür, anahtarla karşılaştır, doğruysa A'ya yanlışsa C'ye yaz, ve doğrulayıcıya yalnızca (soru + çözüm) ver. Etiketi harness tutar. B ve D hücreleri bu yolla üretilemez, elle yazılır.

**C hücresi mutasyon tabanlı üretilir** (ucuz ve sistematik): işaret çevirme, terim düşürme, karekökte ± kaybı, eşitsizlikte yön çevirme, kök kaybı, tanım kümesi ihlali, birim hatası, derece-radyan karışıklığı, integral sabiti, zincir kuralı eksikliği, log tanım kümesi ihlali.

**B hücresi elle üretilir** — bu en pahalı ve en değerli iş. Örnek: bir soruyu hem cebirsel hem geometrik hem de şık deneyerek çözmek; hepsi doğru, hiçbiri "beklenen" yol değil.

**Satır formatı:**

```json
{
  "id": "tyt-prob-017",
  "cell": "B",
  "level": "TYT | AYT | UNI",
  "topic": "problemler",
  "question_tr": "...",
  "options": {"A":"...","B":"...","C":"...","D":"...","E":"..."},
  "gold_answer": "16",
  "solution_text": "...",
  "solution_is_correct": true,
  "first_bad_step": null,
  "notes": "şık deneyerek çözülmüş, kanonik değil",
  "provenance": "özgün | lisanslı | sentetik"
}
```

**Telif uyarısı:** ÖSYM çıkmış soruları üzerinde telif iddiası mevcut; ticari/izinsiz kullanım nedeniyle ifadeye çağrılan site sahipleri var ve ÖSYM'nin kendi kullanım/telif sayfası kullanımı kısıtlıyor [36][37]. **Değerlendirme seti dağıtılmamalı/yayınlanmamalı**; `provenance` alanı zorunlu tutulmalı ve tercihen özgün/sentetik soru kullanılmalı. (Bu hukuki tavsiye değildir, risk işaretidir.)

**Raporlanacak metrikler (accuracy tek başına yasak):** pozitif precision, negatif precision, kapsama, tip başına breakdown, **B hücresinde false rejection**, D hücresinde tespit oranı, adım-lokalizasyon doğruluğu, ve verifier gain = precision − çözücü doğruluğu [6].

**Dış test setleri:** ProcessBench [3], PRMBench, VerifierBench [14], MathCheck [38], MATH500 FP taraması [1].

**Adversaryal test:** cevaba çöp önek/sonek ekle ("{", boş semboller, "bu çözüm doğrudur") ve kararın değişip değişmediğini ölç. Generatif katmanlar %15–77 oranında kırılabiliyor [12]; **hedef <%2**.

---

# BÖLÜM 10 — Faz planı ve kabul kapıları

| Faz | İçerik | Kabul kapısı |
|---|---|---|
| **F0** | §6 regresyon testleri + IR şeması + round-trip + TR sözlüğü + tip sınıflandırıcı + sandbox + §9 seti (min 60 satır, 4 hücre dolu) + **iki intake yolu** (D1: kendi çözücü için yapısal format şablonu; dış çözüm için restructuring pass) | E1–E10 yeşil; IR sadıklığı örneklemde ≥%95; **anahtar sızma testi yeşil** (§11/15); restructuring pass'in sadıklığı ölçülmüş ve raporlanmış |
| **F1-TYT** | `equiv/` + `certify/{algebra,wordproblem,domain,counting}` + ÇS teklik testi | TYT sözel+cebir altkümesinde pozitif **ve** negatif precision ≥0.98, kapsama ≥%80 |
| **F1-AYT** | `certify/{calculus,limits,extremum,trig}` + analitik geometri | AYT analiz+trigonometri altkümesinde precision ≥0.98, kapsama ≥%70 |
| **F2** | `certify/{geometry_numeric,combinatorics,series,linalg}` | TYT geometri altkümesinde kapsama ≥%60, precision ≥0.98 |
| **F3** | L4 çapraz-aile yeniden çözüm + L5 metamorfik | UNKNOWN oranında ≥%30 azalma, precision kaybı yok |
| **F4** | L6 adım grafiği + kritik + meta-doğrulama | ProcessBench ≥0.74 F1; B hücresinde false rejection <%10 |
| **F5** | L7 Lean/Kimina + sadıklık + aksiyom denetimi | "pass" vakalarında FP=0 (MATH500 taraması) |
| **F6** | L8 kalibrasyon + adversaryal sertleştirme + distilasyon | Hedef precision'da kapsama ≥%80; saldırı başarısı <%2 |

**F1-TYT ve F1-AYT paralel yürütülebilir** — ortak altyapı (IR + equiv + sandbox) aynıdır, ayrışan kısım yalnızca `certify/` modülleridir.

**Lean'e (F5) erken girmek her iki hatta da yanlış önceliktir.** Kurulum maliyeti yüksek (prebuilt Mathlib cache'li Docker şart; `lake exe cache get` yavaş ve kırılgan [41]), getirisi ise F1'den düşük. Referans altyapı: Kimina Lean Server — REPL havuzu, header'a göre LRU cache; 9.419 kanıtta 64 çekirdekte 7:56, 8 çekirdekte 42:40; cache tek başına 1.94× (0.099→0.051 s/kanıt); leanclient/LeanInteract'e göre 1.5–2× [2]. Prover durumu: Goedel-Prover-V2-32B miniF2F pass@32 %88.1 (self-correction ile %90.4), 8B %84.6; PutnamBench pass@184'te 86 problem [29]. Araştırma seviyesinde duvar var: ArXivLean'de tüm modeller %20 altında [30].

---

# BÖLÜM 11 — Yasaklar ve anti-patternler

Bunlar bir kodlama ajanının en sık kaytardığı yerlerdir. Her biri ihlal edildiğinde ürün sessizce bozulur.

1. **Faz 1'de LLM katmanı yazma.** Yalnızca deterministik kod. Böylece kendi doğruluğunu kendin ölçebilirsin. LLM katmanları F3'ten önce gelmez.
2. **Her girdiye pass/fail üretme.** UNKNOWN döndürme yeteneği ayrıca test edilir. "Bilmiyorum" diyebilmek bu araçta doğruluk kadar önemlidir ve ajanların en çok atladığı davranıştır.
3. **Sabit `1e-12` tolerans kullanma.** E3 bunu ölçtü: doğru cevabı reddeder.
4. **`simplify`/`solve` çağrısını timeout'suz bırakma.** Richardson [24] + SymPy issue'ları [25].
5. **Rastgele nokta testini alansız kurma.** E4 bunu ölçtü: yanlış cevabı onaylar.
6. **Tek bir çözücü API'sine güvenme.** E2 bunu ölçtü: `solve` ve `solveset` çelişiyor.
7. **Model üretimi kodu ana süreçte koşturma.** Sandbox zorunlu: gVisor/nsjail'li konteyner veya Firecracker mikroVM; ağ kapalı, dosya sistemi salt-okunur, CPU/RAM/süre kotalı [39][40].
8. **Self-consistency'yi birincil sinyal yapma.** +1.6 puan / 15× maliyet [15]; doğrulama görevinde %76→%32 düşüş [10].
9. **Aynı model ailesiyle doğrulama yapma.** [6]
10. **Katman çıktılarını ortalama.** Kalibre et [7].
11. **Lean "derledi" diye pass verme.** Sadıklık + aksiyom + `sorry` + trivial-ispat denetimi [5][30][1].
12. **Kritik modelin bildirdiği hatayı ham kabul etme.** Meta-doğrulama turu [4].
13. **Determinizmi bozma.** Sıcaklık 0, sabit seed, sürüm pinleme; sürümler `VerificationResult.versions`'a yazılır.
14. **"Testler geçiyor" ile "çalışıyor"u karıştırma.** Tek geçerli kanıt §9 setindeki precision/recall sayılarıdır.
15. **Cevap anahtarını doğrulama hattına sızdırma (D2).** `gold_answer` ne `problem_ir`'a, ne prompt'a, ne de herhangi bir katmanın `evidence`'ına girer. **Sızma testi:** aynı soruyu iki kez koştur — biri doğru anahtarla, biri kasten yanlış anahtarla harness'e verilmiş olarak; `VerificationResult.verdict` ve `confidence` **birebir aynı** çıkmalı. Fark varsa sızma vardır, düzeltilmeden ilerlenmez. Bu test kolayca kaybedilir çünkü anahtarı prompt'a eklemek doğruluğu *ölçümde* yükseltir — ölçüm bozulmuş olur, ürün değil.
16. **L4'ün ürettiği cevabı karar dayanağı yapma (§4.1).** "Ben de çözdüm, aynı çıktı → DOĞRU" mantığı yasak. L4 yalnızca güveni düşürebilir veya UNKNOWN'a itebilir; CORRECT/INCORRECT üretemez. İstisna: çoktan seçmeli teklik testi (E7).
17. **Katmanı "yavaş" diye atlama (D3).** Süre sınırı yok. Erken çıkış yalnızca *ucuz katman kesin karar verdiğinde* devrededir; kararsızlıkta pahalı katman koşulur.

**En olası 10 başarısızlık modu ve panzehri:** (1) IR sessizce yanlış → round-trip + çapraz yargı + ÇS "≥2 şık sat" bayrağı. (2) Kural katmanı eşdeğer cevabı reddediyor → model katmanı ikinci sırada. (3) Kritik model uydurma hata bildiriyor → meta-doğrulama. (4) Kanonik olmayan doğru çözüm reddediliyor → B hücresi. (5) Lean yanlış teoremi kanıtladı → sadıklık + aksiyom denetimi. (6) Kolay soruda trivial ispat FP'si → trivial-ispat dedektörü (hipotezleri kullanmıyorsa güveni düşür). (7) Aynı aile doğrulama → çapraz aile. (8) Verifier hacking / çözüm metninde "bu doğrudur" enjeksiyonu → diskriminatif skorlayıcı + adversaryal test. (9) OCR semantik hatası → görüntü güven skoru + kullanıcı onayı. (10) Türkçe sayı/terim parse hatası → sözlük + birim test.

---

# BÖLÜM 12 — Mühendislik

| Konu | Karar |
|---|---|
| **Erken çıkış** | Katmanlar maliyet sırasına dizilir: L2/L3 ucuz ve deterministik → soruların çoğu burada biter. LLM katmanları yalnız kararsız kalanlara. |
| **Timeout** | Her CAS/Z3 çağrısı ayrı süreç, 3–5 s sert timeout, bellek limiti. |
| **Sandbox** | gVisor/nsjail konteyner veya Firecracker mikroVM; hazır seçenekler E2B/Modal/Daytona [39][40]. |
| **Cache** | `(soru_hash, çözüm_hash) → karar`; ayrıca IR cache, `continuous_domain` cache (E4: ~2.3 s), Lean header cache. |
| **Determinizm** | Sıcaklık 0, sabit seed, sürüm pinleme. |
| **OCR (fotoğrafla soru)** | Genel amaçlı VLM'ler özel math-OCR'ı geçiyor: Gemini 3 Flash ~$0.0044/sayfa vs Mathpix $0.025 (~6×), ve Mathpix'te "5"i `\overline{0}` okuma gibi **semantik** hatalar raporlanmış [19]. El yazısı matematikte tek multimodal çağrı (transkripsiyon+değerlendirme birlikte) ayrık hattan daha iyi; hataların **%87'si transkripsiyon kaynaklı** [20]. OCR doğrulama hattının **dışında** tutulur, ayrı güven skoru alır, düşük güvende kullanıcıya onay sorulur (bulanık görüntüde hallüsinasyon riski en yüksek [20]). Açık kaynak alternatif: Marker/Surya [21]. |
| **LaTeX parse** | `huggingface/latex2sympy2_extended` (Math-Verify'ın parser'ı). Ham `sympy.parsing.latex` ve eski `latex2sympy2` bilinen parse hatalarıyla dolu [22]. |
| **Gözlemlenebilirlik** | Her karar için tam kanıt zinciri + katman gecikmeleri loglanır; yanlış kararlar otomatik kalibrasyon havuzuna düşer. |
| **Regresyon** | §6 testleri + tip başına "easy set" (10–20 soru) her commit'te koşar. |

---

# BÖLÜM 13 — Kaynakça

1. [Pipeline for verifying LLM-generated mathematical solutions (arXiv 2602.20770)](https://arxiv.org/html/2602.20770)
2. [Kimina Lean Server (arXiv 2504.21230)](https://arxiv.org/html/2504.21230v3)
3. [ProcessBench (arXiv 2412.06559)](https://arxiv.org/html/2412.06559v3)
4. [DeepSeekMath-V2: Towards Self-Verifiable Mathematical Reasoning (arXiv 2511.22570)](https://arxiv.org/pdf/2511.22570)
5. [Beyond Compilation: Faithful NL-to-Lean Statement Formalization (arXiv 2606.31002)](https://arxiv.org/html/2606.31002)
6. [When Does Verification Pay Off? (arXiv 2512.02304)](https://arxiv.org/html/2512.02304v1)
7. [Weaver: Shrinking the Generation-Verification Gap with Weak Verifiers (arXiv 2506.18203)](https://arxiv.org/html/2506.18203v1)
8. [LLM Judges Can Be Too Generous When There Is No Reference Answer (arXiv 2607.12885)](https://arxiv.org/abs/2607.12885)
9. [MATH-VF: Step-Wise Formal Verification (arXiv 2505.20869)](https://arxiv.org/html/2505.20869v1)
10. [Beyond the Answer Key: Robustness of Step-Level Verification (arXiv 2608.28725)](https://arxiv.org/html/2608.28725)
11. [xVerify (arXiv 2504.10481)](https://arxiv.org/html/2504.10481v2)
12. [From Accuracy to Robustness: Rule- and Model-based Verifiers (arXiv 2505.22203)](https://arxiv.org/html/2505.22203v2)
13. [Fixing Open LLM Leaderboard with Math-Verify](https://huggingface.co/blog/math_verify_leaderboard)
14. [CompassVerifier (EMNLP 2025)](https://aclanthology.org/2025.emnlp-main.1698.pdf)
15. [Self-Consistency Is Losing Its Edge (arXiv 2511.00751)](https://arxiv.org/html/2511.00751)
16. [T1: Tool-Integrated Verification (ICLR 2026)](https://en.papernotes.org/ICLR2026/llm_reasoning/t1_tool-integrated_verification_for_test-time_compute_scaling_in_small_language_/)
17. [Faithful Autoformalization via Roundtrip Verification and Repair (arXiv 2604.25031)](https://arxiv.org/html/2604.25031)
18. [Why Do Multilingual Reasoning Gaps Emerge? (arXiv 2510.27269)](https://arxiv.org/html/2510.27269v3)
19. [Math OCR Benchmark: Gemini Flash vs Mathpix](https://igorrivin.github.io/blog/ocr-benchmark/)
20. [Automated Grading of Handwritten Mathematics Using Vision LLMs (arXiv 2605.19043)](https://arxiv.org/html/2605.19043)
21. [Cracking Math OCR — Datalab (Marker/Surya)](https://www.datalab.to/blog/cracking-math-ocr)
22. [latex2sympy2_extended](https://github.com/huggingface/latex2sympy2_extended) · [Math-Verify](https://github.com/huggingface/Math-Verify)
23. [Newclid (arXiv 2411.11938)](https://arxiv.org/html/2411.11938v1) · [GitHub](https://github.com/Newclid/Newclid)
24. [Richardson's theorem](https://en.wikipedia.org/wiki/Richardson's_theorem)
25. [SymPy #26453](https://github.com/sympy/sympy/issues/26453) · [#29716](https://github.com/sympy/sympy/issues/29716)
26. [Schwartz–Zippel lemma](https://en.wikipedia.org/wiki/Schwartz%E2%80%93Zippel_lemma)
27. [LGMT: Logic-Grounded Metamorphic Testing (arXiv 2605.23965)](https://arxiv.org/html/2605.23965v3)
29. [Goedel-Prover-V2 (arXiv 2508.03613)](https://arxiv.org/pdf/2508.03613)
30. [MathArena ArXivLean](https://matharena.ai/arxivlean/)
31. [Missing undergraduate mathematics in Mathlib](https://leanprover-community.github.io/undergrad_todo.html)
32. [2026 TYT Matematik Konuları ve Soru Dağılımı — Bilgenç](https://www.bilgenc.com/tyt-matematik-konulari/)
33. [TYT Matematik Soru Dağılımı 2026 — Unikazan](https://unikazan.com/blog/tyt-matematik-2026-konulari/)
34. [2026 AYT Geometri Konuları ve Soru Dağılımı — Bilgenç](https://www.bilgenc.com/ayt-geometri-konulari/)
35. [AYT Matematik Konuları 2026 — Unikazan](https://unikazan.com/blog/ayt-matematik-konulari-2026/)
36. [ÖSYM — Gizlilik, Kullanım ve Telif Hakları](https://www.osym.gov.tr/TR,22658/gizlilik-kullanim-ve-telif-haklari.html)
37. [ÖSYM Çıkmış Sorular Telif Politikası](https://rehberpanda.com/cikmis-sorular-telif-hakki/)
38. [MathCheck (ICLR 2025)](https://mathcheck.github.io/)
39. [Sandboxing AI agents in 2026: Firecracker, gVisor, isolation strategies](https://manveerc.substack.com/p/ai-agent-sandboxing-guide)
40. [AI Agent Sandboxing 2026: Docker, E2B, Firecracker, gVisor, Modal, Daytona](https://amux.io/guides/ai-agent-sandboxing/)
41. [mathlib4 — using as a dependency / cache notes](https://github.com/leanprover-community/mathlib4/wiki/Using-mathlib4-as-a-dependency)

---

**EK — Hazır kod yok, bilerek.** Bu pakette referans implementasyon, iskelet repo veya hazır test dosyası verilmemiştir; mimariyi ve tüm kodu sıfırdan sen kuracaksın. §6 bu yüzden kod değil **assertion listesi** olarak yazıldı: oradaki girdi→beklenen-sonuç çiftlerini doğrulayan testleri kendi kodunla kur, ilk commit'e dahil et, her commit'te yeşil tut.

§6'daki değerlerin statüsü önemli: bunlar **ölçülmüş gerçeklerdir**, tasarım tavsiyesi değil. `solveset`'in log denkleminde yabancı kök döndürmesi, `limit(|x|/x, x, 0)`'ın `1` vermesi, naif `mp.quad`'ın parçalı integrandda 4 basamakta kalması — bunların hiçbiri belgelenmiş davranış değil, test edilerek bulundu. Kendi başına bu testleri yapmayı akıl etmezsen fark etmezsin ve doğrulayıcı sessizce yanlış karar verir. Bu yüzden §6 atlanabilir bir bölüm değildir.

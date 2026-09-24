# CLAUDE.md — mathverify kalıcı kuralları

Güncel durum, ölçülen sayılar ve sıradaki iş için önce `HANDOFF.md`, sonra `DECISIONS.md` okunur;
bulut oturumunda ayrıca `docs/BULUT.md`. Kullanıcının `~/.claude` belleği buluta taşınmaz: oturumun
bilmesi gereken her şey depoya yazılır.
Bu dosya yalnız **kalıcı** kuralları taşır; geçici durum buraya yazılmaz.

## Kullanıcıyla çalışma

- Kullanıcıyla Türkçe konuşulur. Belgeler, raporlar, karar izleri ve commit mesajları Türkçe;
  kod, tanımlayıcılar ve `src/` içindeki yorumlar İngilizce.
- Kullanıcı en kaliteli, kapsamlı ve özerk işi ister. "Emin ol" ya da "tek eksik bu mu" soruları
  harfiyen kastedilir: önceki cevabı tekrarlama, yeni ve sistematik bir denetim yap. Krediye bağlı
  olmayan bir açık bulunursa aynı turda düzelt.
- Ölçülmüş sayı ver; "testler geçiyor" kanıt değildir. Doğrulanmamış bilgiyi işaretle. Önceki bir
  iddia yanlış çıktıysa bunu açıkça söyle.
- Şartnamenin kilitli kararları (D1–D6, `DECISIONS.md` §1) yeniden sorulmaz. Şartname:
  `docs/sartname/fable-handoff-matematik-dogrulama_1.md`.
- Krediye bağlı ölçümler (F3/F4) ancak bütün lokal kalite işi bitip kod dondurulduktan ve API
  anahtarları yenilendikten sonra koşulur (kullanıcı kararı, 23 Eylül 2026).

## Doğrulayıcının değişmez ilkeleri

1. Cevap anahtarı ya da anahtar benzeri bir alan doğrulama hattına asla girmez
   (`ir.FORBIDDEN_KEYS`, `LeakageError`).
2. Karar üretilerek değil, kanıtlanarak verilir. İddia değer-yalnız bir ad alanında okunur
   (`normalize.parse.COMPUTING_OPERATORS`, `Ctx.claim_ns`); doğrulayıcı cevabı kendisi hesaplamaz.
3. İddia karşılaştırılmadan önce yeniden yazılmaz: `int()`, `nsimplify`, yuvarlama yok. Sayılar
   `equiv.exact_integer` ile okunur.
4. Nümerik eşitlik tek başına kanıt değildir. Kesin sayılar kesin karşılaştırılır; eşitlik her
   hassasiyet basamağında sağlanmalıdır. Math-Verify yalnız ikinci görüştür.
5. Adım reddedici yalnız somut karşı örnekle çürütür. Doğrulanamayan adım cezalandırılmaz;
   çözücünün kendi sembolüyle yazdığı adım atlanır.
6. Bir LLM sinyali sert bir sertifikayı ters çeviremez; yalnız CORRECT'i engelleyebilir.
7. Lean ifadesi modele yazdırılmaz, IR'dan şablonla üretilir. Yazıcı çeviremediğini tahmin etmez.
   Hiçbir ispat sorry/aksiyom/vakum/kullanılmayan hipotez denetiminden geçmeden kabul edilmez.
8. Lean'in junk değerlerine (`x/0 = 0`, `Real.sqrt` negatifte 0, `Real.log 0 = 0`,
   `Real.tan (π/2) = 0`) dokunan hiçbir ifade sertifika üretemez.
9. `first | …` zincirinde her alternatif `done` ile kapanır.
10. Faturalama/kimlik hatası (`LLMFatalError`) bir ölçüm değildir; yutulmaz, taramayı durdurur.
11. Ölçülmemiş iyileştirme, iyileştirme sayılmaz.
12. Tanımlılık, ifadenin yazıldığı biçimden okunur (`parse_as_written`, `Ctx.written_conditions`).
    SymPy'nin otomatik sadeleştirmesi (`x/x` → 1) tanımsız noktayı siler; değer için normal ayrıştırma,
    tanımlılık için yazıldığı biçim.

## Her değişiklikte

- Bitirmeden önce `scripts/check.py --full` bütün kapılardan geçmeli (~25–45 dk, arka planda;
  günlüğü `reports/check_full.log`a kendisi yazar). Hızlı döngüde `pytest` ve `scripts/check.py`
  yeterli. Lean'siz ya da Lean'i yarıda kaybeden bir koşuda Lean kapıları bilerek düşer; o koşu
  "geçti" sayılmaz.
- Her yeni Lean şablonu yanlış cevaplı öğelerde ve junk-value sondasında da koşturulur. Lean FP
  ve junk sertifikası 0 kalmalı.
- Her bulgu ölçümle bulunur, ölçümle doğrulanır, bir teste ya da kalıcı bir kapıya bağlanır.
- Kararlar gerekçe ve ölçümle `DECISIONS.md`'ye yazılır. Yanlış çıkan eski ifade silinmez,
  "Düzeltme (tarih)" notuyla düzeltilir.
- Raporlar (`reports/*.md`) üretilir, elle yazılmaz.

## Asla

- `.env`'i, `reports/*.json`'ı ya da herhangi bir anahtarı commit etme. Anahtar değerlerini ekrana,
  belgeye ya da günlüğe yazma.
  **Düzeltme (24 Eylül 2026):** `.env` kısmı geçersiz. Kullanıcının açık kararıyla `.env` bu özel
  depoda (`github.com/wqedwad/asd`) izlenir (`DECISIONS.md` §35). Geçerli kalanlar: `.env.*` ve
  `reports/*.json` commit edilmez (anlık görüntüsü `reports/arsiv/` altında); anahtar değeri hiçbir
  çıktıya yazılmaz. Anahtarlar yenilenince `.env` güncellenip commit edilir. Depo herkese açılacak
  ya da paylaşılacaksa önce anahtarlar yenilenir ve `.env` geçmişten temizlenir.
- Global git ayarını değiştirme. Kimlik gerekirse komut başına `git -c user.name=… -c user.email=…`
  ver; önceki commit'lerin kimliği `git log -1 --format='%an <%ae>'` ile görülür.
- Kullanıcı istemeden commit etme ya da dal birleştirme. Ana dal `master`; doğrudan onun üzerinde
  commit etme, önce dal aç.
- Yedeksiz birleştirme. Her `master` birleştirmesinden önce `yedek/master-YYYY-MM-DD[-N]` etiketi ve
  yerel makinede `C:\Users\kullanici\mathverify-yedek\` altına bir bundle alınır; geri dönüş
  `git reset --hard <etiket>` ya da `git clone --branch master <bundle>`. Etiket ve bundle'lar
  kullanıcıya sormadan silinmez (`HANDOFF.md` §5.4).
- Bulut oturumundan etiket ya da `master` push etmeye çalışma: bulut yalnız oturumun kendi dalını
  push edebilir. Birleştirme PR ile ya da yerel checkout'ta, yedek de yerelde alınır.
- **Düzeltme (24 Eylül 2026):** oturumun kendi dalı başladığı daldır; routine oturumu varsayılan
  dal `master`da başlar ve "kendi dalına push" `master`a push olur (24 Eylül'de böyle oldu,
  DECISIONS §45). Bir bulut routine istemi push hedefini açıkça **yeni bir dal** olarak verir ya da
  hiç push istemez; "kendi dalına" gibi göreli hedef yazılmaz.

## Commit biçimi

Başlık `alan: özet` biçiminde ve Türkçe (`denetim:`, `F7:`, `raporlar:`, `temizlik:`). Gövdede ne
ölçüldüğü ve nasıl doğrulandığı yazılır. Son satır:

```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## Ortam tuzakları

- SymPy ≥ 1.13'te `Float(3.0) == 3` False döner; tam sayılığı `sp.Rational(...)` ile kontrol et.
- Lean yoksa Lean testleri sessizce atlanır; `pytest -rs` ile kontrol et.
- Sandbox kullanan probe'lar gerçek bir dosyada ve `if __name__ == "__main__":` içinde olmalı
  (sandbox her işletim sisteminde multiprocessing `spawn` kullanır).

### Windows

- Python her zaman `.venv/Scripts/python.exe` ile ve `PYTHONUTF8=1` ile çalıştırılır.
- Git Bash heredoc'u `\\` karakterini çökertir. Ters eğik çizgi içeren Python'u Write aracıyla
  dosyaya yaz.
- `ctypes.windll` çağrılarında `restype`/`argtypes` verilmezse tutamaçlar 32 bit'e kırpılır.
- Lean, WSL `Ubuntu` içinde çalışır (`docs/LEAN_SETUP.md`).
- WSL içinde `df` C:'yi görmez, sanal diski gösterir. WSL'deki büyük kurulumlar `ext4.vhdx`'i
  büyütüp C:'yi doldurabilir (24 Eylül: 103.8 GB, C: 0 bayt, WSL açılamadı; `.vhdx` kendiliğinden
  küçülmez). WSL'de büyük bir kurulumdan önce C:'nin boş alanına Windows tarafından bak
  (`HANDOFF.md` §0.10).

### Linux / bulut

- Python `.venv/bin/python` ile (`PYTHONUTF8=1` yine verilir). Bulutta `.venv`'i oturum kancası
  `requirements.lock`'tan kurar; bağımlılık değişince kilit de yeniden üretilir.
- Lean WSL'siz, yerel `bash -lc` ile çalışır; yeri `ELAN_HOME`, `MATHVERIFY_LEAN_PROJECT`,
  `MATHVERIFY_LEAN_REPL` ile verilir (bulutta `/opt` altında). Sürümler `lean/PINS`'te sabit.
- Bulut ayrıntıları (kurulum betiği, kanca, `/opt`, günlükler, sınırlar): `docs/BULUT.md`.
- Bulutta boşta kalan VM geri alınınca arka plandaki iş kaybolur: `check.py --full` ya da Lean
  kurulumu sürerken oturum etkin tutulur.

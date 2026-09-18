# Yapısal çözüm formatı (D1, yol a)

Uygulamanın kendi çözücüsü bu formatı **zorunlu** olarak üretir. Handoff §3'teki bulgu:
"her adım tek sonuçlu, öncülleri açıkça referanslı bir lemma" olduğunda doğrulanabilirlik
satın alınır; serbest düz yazı doğrulanamaz.

## Problem IR (`problem_ir`)

```json
{
  "task": {"kind": "evaluate", "params": {"expr": "a"}},
  "vars": [{"name": "a", "domain": "positive_integer", "constraints": []},
           {"name": "b", "domain": "positive_integer"}],
  "givens": ["a + b = 30", "2*a + 4*b = 88"],
  "functions": [{"name": "f", "expr": "(2*x + 3)/(x - 1)", "args": ["x"], "params": []}],
  "unknown_of_interest": "a",
  "answer_shape": "scalar",
  "options": {"A": "12", "B": "14", "C": "16", "D": "18", "E": "20"},
  "units": null,
  "sanity": ["ans > 0"],
  "domain_of_discourse": null
}
```

* `gold_answer` **yoktur** ve herhangi bir seviyede anahtar benzeri bir alan görülürse
  yükleme `LeakageError` ile durur (D2).
* İfade dizgileri kanonik SymPy sözdizimindedir: `*` açık yazılır, `^` veya `**`, `=`
  eşitlik, `<= >= != <` bağıntılar, `log` doğal logaritma, `Abs`, `sqrt`, `pi`, `E`, `oo`.
  Derece `30°`, yüzde `%25`, unicode `√ π ∞ ≤ ≥ ≠ ²` ön-temizlemede çevrilir. LaTeX de kabul
  edilir (`\frac{\pi}{6}`).
* `domain_of_discourse` problemden gelir (`"x > 0"`, `"x in (0, oo)"`, `"Reals"`). İfadeden
  türetilmez (E4).
* `task.kind` ve `params` router anahtarıdır (`src/mathverify/router.py`). Örnekler:

| kind | params | claimed_answer.kind |
|---|---|---|
| `evaluate` | `expr` (veya `unknown_of_interest`) | value |
| `solve_equation` | `var`, opsiyonel `equation` (yoksa `givens[0]`) | set / value |
| `solve_inequality` | `var`, opsiyonel `inequality` | interval / set |
| `count_integers` / `count_roots` / `count_solutions` | `var` / `expr,var,lo,hi,distinct` / `bounds` | count |
| `domain_of` | `expr`, `var` | set / interval |
| `limit` | `expr`, `var`, `to`, opsiyonel `side` (`+`/`-`) | value / dne / infinite |
| `antiderivative` | `integrand`, `var` | expression (+ C serbest) |
| `definite_integral` | `integrand`, `var`, `a`, `b`, opsiyonel `rel_tol` | value |
| `derivative` | `f`, `var`, opsiyonel `order`, `at` | expression / value |
| `tangent_line` | `f`, `var`, `at`, opsiyonel `dep` | equation |
| `extremum` | `f`, `var`, `interval`, `which` ∈ max/min/argmax/argmin/local_max/local_min/local_argmax/local_argmin | value |
| `trig_solve` | `var`, opsiyonel `interval`; genel çözümde `k`/`n` tam sayı sembolü | set |
| `equation_of` | `object` ∈ line_points/line_point_slope/line_point_parallel/line_point_perpendicular/circle_center_radius/circle_center_point/circle_diameter/perpendicular_bisector/tangent_to_circle_at_point + nokta/parametreler | equation |

Yardımcı fonksiyonlar: `at(expr, var, value)`, `dist(x1,y1,x2,y2)`, `slope(...)`,
`tri_area(...)`, `point_line_dist(x0,y0,a,b,c)`, `det`, `trace`, `eigmax`, `eigmin`,
`gcd`, `lcm`, `binomial`, `P(n,k)`, `deg(x)`.

## Çözüm (`solution`)

```json
{
  "claimed_answer": {"kind": "value", "payload": "16", "option": "C"},
  "steps": [
    {"id": "s1", "kind": "eq",      "claim": "b = 30 - a",              "from": [],     "text": "baş sayısından"},
    {"id": "s2", "kind": "eq",      "claim": "2*a + 4*(30 - a) = 88",   "from": ["s1"], "text": "yerine koy"},
    {"id": "s3", "kind": "eq",      "claim": "a = 16",                  "from": ["s2"], "text": "çöz"}
  ]
}
```

`claimed_answer.kind`: `value | expression | set | interval | count | dne | infinite | equation | condition | none`.
Çoktan seçmelide `option` harfi verilir; harf ile `payload` tutarsızsa çözüm **yanlış**
sayılır (`mc.consistency`).

### Adım türleri ve deterministik denetim

| kind | Anlamı | Denetim |
|---|---|---|
| `eq` | Bu bağıntı, problemin bilinmeyenleri için öncüller altında geçerlidir | Öncülleri (IR verileri + önceki `eq` iddiaları + dalın `case` varsayımları) sağlayan ve alan içindeki bir noktada iddia **yanlışsa** REDDEDİLİR. Özdeşlikler (`sin(3x) = 3 sin x`) rastgele noktalarla sınanır. |
| `compute` | `lhs = rhs` biçiminde bir hesap: türev, integral, limit, toplam, aritmetik | `lhs` CAS ile hesaplanır, `rhs` ile alan-farkında karşılaştırılır; fark varsa REDDEDİLİR. `Limit(...)` iki yönlü sınıflandırılır (E6). Belirsiz integral türev sertifikasıyla (E8). |
| `case` | Durum varsayımı ("2x − 3 = 5 olsun") | Denetlenmez; bu adıma `from` ile bağlanan sonraki adımlarda öncül olarak kullanılır. |
| `assert` | Tanım kümesi / kısıt hatırlatması | Denetlenmez. |
| `note` | Düz yazı, açıklama | Denetlenmez. |
| `conclude` | Sonuç bildirimi ("teğet y = 2x − 1", "cevap C") | Denetlenmez; nihai cevap sertifikalarla sınanır. |

Kurallar:

1. **Tanımlayıcı eşitlikler `eq` değildir.** "Teğetin denklemi y = 2x − 1" gibi yeni bir
   nesneyi *tanımlayan* ifadeler `conclude`; "u = √(x+4) olsun" gibi yeni sembol tanımları
   `note`/`case`. (Reddedici yine de, öncüllerin kısıtlamadığı sembol içeren, özdeşlik
   biçiminde olmayan `eq` iddialarını atlar; ama doğru etiket kalite için şarttır.)
2. **Her `eq`/`compute` tek bir bağıntıdır.** Zincir (`0 <= p <= 1`) kabul edilir; iki
   bağımsız iddia iki adımdır.
3. **Yeni semboller IR'da yoksa** (u, t, n …) adım ayrıştırılamaz ve atlanır; bu ceza
   değildir ama denetim gücünü düşürür. Mümkünse IR sembolleriyle yazın.
4. `from` alt-atıf cezalandırılmaz (öncül havuzu tüm önceki `eq` iddialarını içerir) ama
   `case` dallarının doğru bağlanması şarttır: bir dalın sonucu o dalın `case` adımına
   `from` ile bağlanmalıdır.
5. Nicel her iddia kodla sınanır; düz yazıya aritmetik bırakılmaz (§4.1).

## Yol b (dış çözüm)

Faz 1'de `intake.restructure.extract_final_answer(text)`: `\boxed{}`, `Cevap:`, `Sonuç:`,
`Çözüm kümesi:`, şık harfi (`(C)`, `C şıkkı`) ve "limit yoktur" kalıplarını tanır; adımlar
boş kalır ve yalnız cevap düzeyi doğrulama yapılır. Sadıklığı `harness/run_eval.py`
"Restructuring (yol b) sadıklığı" satırında ölçülür. LLM ile adım yeniden yapılandırma F3.

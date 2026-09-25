# Metamorfik sağlamlık taraması (SymPy üretimli yanlış ve eşdeğer cevaplar)

Problem: **86** (A/B öğelerinin tekil IR'ları) · süre: 32 s

- **Yanlış cevap varyantı: 448** — yanlış onay (CORRECT): **0** (hedef 0) · UNKNOWN: 0
- **Eşdeğer cevap varyantı: 214** — yanlış red (INCORRECT): **0** (hedef 0) · UNKNOWN (kaybedilen kapsama): 0

## Adım düzeyi: geçerli dönüşüm hata değildir, bozulan adım yakalanmalıdır

- **Geçerli adım dönüşümü: 184** (iki tarafa ekle, 2 ile çarp, taraf değiştir, bir tarafa topla) — yanlış red (INCORRECT): **0** (hedef 0; [10] LLM adım doğrulayıcılarında %75–85 ölçüyor) · UNKNOWN: 0
- **Bir tarafı +1 bozulan adım: 46** — yakalanan (INCORRECT): 40 · kaçırılan (CORRECT): 6 · UNKNOWN: 0 · **nedeni açıklanmayan kaçırma: 0** (hedef 0)
  - `undeclared_symbol`: 5 — çözücünün kendi sembolü: özdeşlik mi çözülen denklem mi olduğu belirsiz, bilerek atlanır (DECISIONS §3.3)
  - `premises_have_no_solution`: 1 — öncüllerin hiç çözümü yok (altın cevap boş küme): karşı örnek olabilecek nokta yok
  - kaçırılan: ayt-ana-006 s2: `2 = (2*1 + n) + 1` — adım skipped, `undeclared_symbol`, sembol `n`
  - kaçırılan: ayt-diz-008 s1: `a(n) = (3*n + 2) + 1` — adım skipped, `undeclared_symbol`, sembol `a`
  - kaçırılan: ayt-lim-008 s2: `(t - 1)/(t**2 - 1) = (1/(t + 1)) + 1` — adım skipped, `undeclared_symbol`, sembol `t`
  - kaçırılan: tyt-den-003 s2: `x = (3 + 2*(x - 3)) + 1` — adım unknown, `premises_have_no_solution`
  - kaçırılan: tyt-den-007 s2: `u = (u**2 - 6) + 1` — adım skipped, `undeclared_symbol`, sembol `u`
  - kaçırılan: uni-la-002 s1: `(2 - t)**2 - 1 = ((t - 1)*(t - 3)) + 1` — adım skipped, `undeclared_symbol`, sembol `t`

## Varyant türüne göre

| Varyant | n | CORRECT | INCORRECT | UNKNOWN |
|---|---|---|---|---|
| `equiv:decimal` | 3 | 3 | 0 | 0 |
| `equiv:expanded` | 5 | 5 | 0 | 0 |
| `equiv:factored` | 5 | 5 | 0 | 0 |
| `equiv:moved_to_one_side` | 3 | 3 | 0 | 0 |
| `equiv:nsimplified` | 59 | 59 | 0 | 0 |
| `equiv:permuted` | 3 | 3 | 0 | 0 |
| `equiv:radsimp` | 59 | 59 | 0 | 0 |
| `equiv:same_matrix_rebuilt` | 2 | 2 | 0 | 0 |
| `equiv:same_set_rebuilt` | 5 | 5 | 0 | 0 |
| `equiv:scaled_by_2` | 3 | 3 | 0 | 0 |
| `equiv:sides_swapped` | 3 | 3 | 0 | 0 |
| `equiv:times_one_unevaluated` | 59 | 59 | 0 | 0 |
| `equiv:together` | 5 | 5 | 0 | 0 |
| `non_answer:diff_call` | 2 | 0 | 0 | 2 |
| `non_answer:integrate_call` | 4 | 0 | 0 | 4 |
| `non_answer:latex_integral` | 4 | 0 | 0 | 4 |
| `non_answer:limit_call` | 6 | 0 | 0 | 6 |
| `non_answer:own_function` | 5 | 0 | 0 | 5 |
| `non_answer:restates_target` | 23 | 0 | 10 | 13 |
| `non_answer:sum_object` | 2 | 0 | 0 | 2 |
| `wrong:doubled` | 57 | 0 | 57 | 0 |
| `wrong:dropped_member` | 3 | 0 | 3 | 0 |
| `wrong:entry_plus_one` | 2 | 0 | 2 | 0 |
| `wrong:extra_member` | 5 | 0 | 5 | 0 |
| `wrong:left_endpoint_flipped` | 3 | 0 | 3 | 0 |
| `wrong:left_endpoint_shifted` | 3 | 0 | 3 | 0 |
| `wrong:minus_one` | 59 | 0 | 59 | 0 |
| `wrong:negated` | 58 | 0 | 58 | 0 |
| `wrong:perturbed_1e-9` | 59 | 0 | 59 | 0 |
| `wrong:plus_half` | 59 | 0 | 59 | 0 |
| `wrong:plus_one` | 64 | 0 | 64 | 0 |
| `wrong:plus_x` | 2 | 0 | 2 | 0 |
| `wrong:relative_1e-6` | 59 | 0 | 59 | 0 |
| `wrong:rhs_doubled` | 3 | 0 | 3 | 0 |
| `wrong:rhs_plus_one` | 3 | 0 | 3 | 0 |
| `wrong:right_endpoint_flipped` | 1 | 0 | 1 | 0 |
| `wrong:shifted` | 5 | 0 | 5 | 0 |
| `wrong:shifted_argument` | 3 | 0 | 3 | 0 |

## Yanlış onaylar (0)

yok

## Yanlış redler (0)

yok

## Atlananlar (SymPy'nin kanıtlayamadığı varyantlar puanlanmaz)

- answer_kind_dne: 1
- gold_unparsed:ParseError: 1
- gold_unparsed:UndeclaredSymbolError: 1
- wrong:doubled:not_proved: 4
- wrong:plus_x:not_proved: 3
- wrong:shifted_argument:not_proved: 2

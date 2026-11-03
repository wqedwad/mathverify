# NOTLAR - d4 tanimlilik
- kopyalar hazir (yeni=eb3bccc, eski=aa67b20)
- sonda altyapisi: sonda/run.py, both.sh (yeni+eski paralel), cmp.py, common.py
- c1 (57 durum, araliklar): 
  * ADAY F1 (false_accept, onceden var): kesirli ALT sinir tam sayi aralikli: Sum(k,(k,1/2,5/2))=9/2 CORRECT (k integer bildirilmis); sembolik m=1/2,n=5/2 de CORRECT; "3" INCORRECT. _one_range_conditions yalniz gap'e bakiyor, lo'nun tam sayiligina bakmiyor.
  * ADAY C1 (coverage_regression): Product(Sum(1,(j,1,k)),(k,1,n)), n=3 -> 6 eski CORRECT, yeni UNKNOWN (problem_undefined_as_written; ic Sum'in span kosulu dis indise named -> _index_region None)
- c2 (40 durum, baglayici govdesi):
  * ADAY F2 (false_accept, onceden var): x positive_real, y + at(diff(sqrt(-x), x), x, -1) = -1/2 -> {} CORRECT (dogru {0}). Yazili okuma at() icinde bildirilmis x'i tutuyor, _written_diff written_domain(...,False) uretiyor -> nowhere -> bos kume.
  * ADAY F3 (false_accept, onceden var): x positive_real, evaluate Limit(sqrt(x)**2/x, x, -oo) = 1 CORRECT. _limit_conditions 'over' bolgesini bildirilmis z.is_nonnegative'den [0,oo) aliyor (deger okumasi x'i gercel aliyor).
- c3 (55): F2 dogrulandi (count_roots 0, ineq EmptySet, domain_of EmptySet, x nonneg, ayni degisken hep CORRECT, eski de). F3 dogrulandi (nonneg, log(x)-log(x), n posint, limit(), acos; compute adimi Limit(...,-oo)=1 verified).
- c4 (65): 
  * ADAY F4 (false_accept, cogu onceden var; limit+acos #14): verilen a=-1 ile x+log(a)-log(a): limit, derivative, defint, extremum, tangent, solve {2}, ineq, count_roots, domain_of, simplify, series_sum CORRECT. Yazili kosul a>0 yalniz parametrede; domain_for (var degil) duzuyor; _NOWHERE_PARAMS/written_undefined_everywhere baglamalari okumuyor.
    limit 'a*x + acos(a) - acos(a)', a=2 -> 2: yeni CORRECT eski UNKNOWN (#14 F9 pin).
  * ADAY F5 (false_accept, #14): celisen verilenler a=0, a-1=0, x>a: x^2=4 -> {2} yeni CORRECT (eski INCORRECT). given_bindings yalniz s=c'yi okuyor, celiski gormuyor.
- c5 (56):
  * F4 genis: sqrt(a), acos(a), a/a, tan(pi/2), log(a-1), Sum ters, factorial(-1), gcd(sqrt2) hep CORRECT (eski de). f(a) fonksiyon cagrisi da. 'b = log(a)-log(a)' verilen zinciri: yeni CORRECT (wordproblem), eski INCORRECT.
    kapali es (log(-1)-log(-1), f(-1)) UNKNOWN -> tutarsizlik.
  * F5 genis (#14): a=0 & a>1 / a**2=1 / 2a=1 / a positive bildirilmis / kisit a>1: x>a ile {2} CORRECT (eski INCORRECT); ineq, count_roots, domain_of, limit de CORRECT.
  * ADAY F6: x**a, a=2: solve {-2,2} INCORRECT (eski de; haksiz red), ineq x**a<4 -> (0,2) CORRECT & (-2,2) INCORRECT YENI (eski UNKNOWN; #14). x**a=-8,a=3 -> {-2} INCORRECT. Sembolik us kurali base>0 baglamadan once okunuyor.
- c6 (50):
  * ADAY F7 (false_accept, onceden var): acik kosullarin kesisimi bos/tek nokta (log(x)-log(x)+log(-x)-log(-x); acos x + acos(x-3); sqrt(x)+sqrt(-x)): derivative (ifade) CORRECT, derivative at 0 (P0, tanim kumesi {0}) CORRECT, antiderivative CORRECT (V3 biliniyor?), simplify CORRECT (B(4) kapali sanilan sinifin varyanti). _NOWHERE_PARAMS yalniz kapali false okuyor; derivative domain_for f'nin yazili kosullarini okumuyor.
  * ADAY F8 (false_accept, onceden var): 'nowhere' kumesi yok sayiliyor: trig_solve sin(x)+log(-1-x**2)-log(-1-x**2)=0 -> {0,pi} CORRECT (pencereli ve genel); count_solutions x pos int, x+y+sqrt(-x)-sqrt(-x)=4 -> 3 CORRECT.
- c7 (48):
  * F9 (=F7 ile ayni kok, birlestir): derivative/tangent f'nin yazili tanim kumesinin ucunda: x+sqrt(x)-sqrt(x) at 0, sqrt(x)**2 at 0, acos at 1, sqrt(1-x^2) at 1 -> CORRECT; tangent sqrt(x)**2 at 0 CORRECT. Ayrica Abs(x)+sqrt(x)-sqrt(x) ifade turevi '1' INCORRECT (haksiz red: R'de karsilastiriyor).
  * F10 (adim, dusuk): x=0 altinda 'x/x + sqrt(y) - sqrt(y) = 1' verified (y serbest; _undefined_at_premises tum semboller sabitlenmeli).
  * membership (5): temiz.
- c8/c9 (75): 
  * ADAY F11 (false_accept, #14, YUKSEK): verilenin sabitledigi n ile ters/kesirli aralik on_var/_with_bound_values ile iliskiye konuyor, aralik kosulu (n'de) x'in alanindan dusuyor -> Karr degeriyle CORRECT: ineq x*S>2,n=-2 -> (2,oo); x+S>5,n=-3; verilen x>S; m=3,n=1; n/2 n=7 (63/8); n=5/2 gercel; solve x^2=4 yan kosul x>S n=-3 -> EmptySet; count_roots 0; domain_of (3,oo); count_integers 1. Eski: UNKNOWN/INCORRECT.
  * extremum x*S n=-2 max -> 0 (bos toplam) CORRECT eski+yeni (onceden var).
  * trig sin(x)*S=0, n=-2 -> {0,pi} CORRECT (onceden var).
  * derivative x + S, n=-2 -> 1 CORRECT (onceden var; tutarsizlik).
  * F1 genis: limit/derivative/solve/latex/step/Sum(k,(k,pi,pi+1)), n gercel serbest Sum(k,(k,n,n+2))=3n+3 CORRECT.
  * SURE: ineq x*Sum(k,(k,1,n/2))>2 n=7 ve n=5/2: 86 s (yeni), eski? -> olc
  * SURE dogrulandi: T1/T2 ~108-111 s (yeni), eski UNKNOWN hizli. Profil: on_var sonrasi degerlendirilmemis Sum(k,(k,1,7/2)) her ornek noktada evalf_sum/euler_maclaurin (_sample_inequality). F11'in crash varyanti.
- c10 (37): F4 serbest parametrede de (x+log(a)-log(a)=2 -> {2}; zayif, parametrik). Pinned: a/a a=0 (solve/ineq/count/domain_of) CORRECT; ineq binomial(a,2) a=-1 YENI CORRECT (#14 on_var).
  x*tan(a) a=pi/2 -> EmptySet CORRECT: konvansiyonla tutarli (bulgu degil).
- ADAY F12 (false_accept, onceden var, YUKSEK): extremum f'de parametre: a*x [0,1] max, a=3 verilen -> 0 CORRECT, 3 INCORRECT; a serbest de 0 CORRECT. Aday kumesi yalniz [0,0]; serbest sembollu uc deger dusuyor. x*Sum(k,(k,1,n)) n=3 de ayni (0 CORRECT, 6 INCORRECT).
- c11 (26): F12 dogrulandi (a*x max a=3 ->0 CORRECT, 3 INCORRECT; min a=-3 ->0; argmax 0; x**2+a max 4 INCORRECT; kisitla sabitlenen a; n posint). Kok: certify_extremum vals'tan sayisal olmayan adaylari sessizce atiyor (extremum.py ~142) ve parametreyi baglamiyor/cekimser kalmiyor.
- c12 (17): ADAY F13 (#14 eksik duzeltme): _reachable sonsuz siniri EmptySet sayiyor: der Int(1/t,(t,-oo,x)) x pos -> 1/x CORRECT (1/t^2, 1/sqrt|t|, exp(t)/t de); adim verified; solve y+Int(...)=0 -> EmptySet YENI INCORRECT (eski UNKNOWN). Varyant (onceden var): sonsuzda iraksak Int(1/(t+1),(t,x,oo)) turevi CORRECT.
- c13/c14: F2 Sum(at(diff)) varyanti; C1 dogrulandi (Product(Sum), Sum(k*Sum), Sum(Product), Sum(2^k*Sum) n=3: eski CORRECT, yeni UNKNOWN problem_undefined_as_written).
- bagimsiz.py: mpmath/Fraction kontrolleri tutarli.
- repro/: 12 betik, yeni+eski koşuldu (out_yeni.txt, out_eski.txt). Hepsi beklenen yanlis karari yeniden uretiyor.
- Toplam: 549 sonda durumu (c1..c14) + ~13 tek tek koşu; her biri yeni ve eski kopyada.
- SON: bulgular.json yaziliyor, StructuredOutput.
- bulgular.json yazildi (12 bulgu: TAN-01..TAN-12). StructuredOutput gonderiliyor.

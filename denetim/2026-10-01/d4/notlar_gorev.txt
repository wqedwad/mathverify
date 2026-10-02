# D4 gorev denetimi NOTLAR
- Kopyalar kuruldu (yeni=eb3bccc, eski=aa67b20).
- sonda/ altinda h.py (yardimci), run.sh (yeni|eski betik)
- p01_der: turev uc noktasi 42 durum, bulgu yok (yalniz: Abs(x) 0'da given x>=0 -> INCORRECT, dod x>=0 -> UNKNOWN: tutarsizlik, dusuk)
- p02_or: BULGU F1: Or(...) verileni side_conditions/_conditions_on'da sessizce dusuyor:
  ineq x^2<4 given Or(x<-3,x>1) (-2,2) CORRECT; croots x^2-4 -> 2 CORRECT; ext max -x^2 [-5,5] -> 0 CORRECT; domain_of sqrt(4-x^2) -> [-2,2] CORRECT.
  Dogru (1,2) ve 1 INCORRECT (haksiz red). Eski kodda da var (cons Or #14'te kapanmis, given Or kapanmamis).
- p03_chain: F1 genisledi: zincir/And verileni (0 < x < 3, And(x>0,x<3)) side_conditions'ta da dusuyor (Relational degil):
  ineq/croots/domain_of yanlis CORRECT, dogru INCORRECT; serbest b'li zincir (b<x<3) condition_not_applied bile vermiyor. Eski kodda ayni.
- p04_eval: BULGU F2: evaluate+verilen denklem yolu sp.solve'un tamligina guveniyor (periyodik denklemde yalniz esas cozumler):
  sin(x)=0, 3<x<7 iken x icin pi CORRECT (2pi de cozum), cos(x) icin -1 CORRECT (1 de olur), tan(x)=1, 0<x<4 -> pi/4 CORRECT.
  Eski kodda ayni (onceden var). z3 sin'i cevirmiyor -> tek katman algebra pass.
- p05_bind: BULGU F3: domain_for kisit yolunda _with_bound_values sonrasi sp.false olan kisit sessizce dusuyor
  (x positive, cons x<a, given a=0): x^2=4 icin {2} CORRECT, dogru {} INCORRECT; ineq (0,2) CORRECT; domain_of sqrt(x) (0,oo) CORRECT.
  (given yolu ve yazili kosul yolu false->EmptySet yapiyor; kisit yolu yapmiyor). Eski: kisit tamamen dusuyordu (ayni sonuc).
  BULGU F4: given_bindings degeri parametrenin oteki verilen/bildirim/kisitlariyla denetlemiyor: a=1 ve a<0 (celisik) iken
  x>a ile x^2<4 -> (1,2) CORRECT, croots 1 CORRECT, eq {2} CORRECT; a integer & a=1/2; a cons a>5 & a=1. Eski kodda INCORRECT idi. #14 getirdi.
  wordproblem katmani ayni durumda givens_without_an_instance diyor (tutarsizlik).
- p06_trig: BULGU F5: trig_solve sertifikasi params.interval disinda degiskenin hicbir kosulunu okumuyor (ek verilen,
  vars.constraints, dod, positive/integer bildirimi, ikinci denklem). cos2x=1/2 [0,2pi) + x>pi -> 4 kok CORRECT, dogru 2 kok INCORRECT;
  sinx=0 genel + x positive -> {n*pi} CORRECT. 20/21. Eski kodda ayni (onceden var).
- p07/p08: BULGU F6 (dusuk): general_solution_from_claim iki aile parametreli ogede ints[0]'i (set sirasi, hash'e bagli) seciyor;
  {n*pi + k*pi}, {k*pi + 2*n*pi}, tan x=0 {n*pi+k*pi} INCORRECT (dogru: hepsi {j*pi}); ayni girdi kosudan kosuya UNKNOWN/INCORRECT (determinizm yok). Eski kodda da.
  p07 geri kalan 46 durum beklendigi gibi (V17 kapanmis).
- p09_wp: wordproblem 50 durum, bulgu yok (CRootOf okunmuyor: kapsama)
- p10_count: 38 durum; yalniz real bildirilmis degiskende count_solutions tam sayi sayiyor (IR tanimi geregi; bulgu sayilmadi). natural=>=1 IR semasinda.
- p11_lim (44 durum): BULGU F7: limit sertifikasi vars.constraints/verilen/dod'u hic okumuyor (yalniz bildirilen alan: declared_side).
  |x|/x 0'da: positive_real -> 1 CORRECT; cons/given/dod x>0 -> DNE CORRECT, 1 INCORRECT (tutarsiz; haksiz red + yanlis onay).
  lim x->0 x, x>1 kisitiyla 0 CORRECT (bildirimde approach_outside -> UNKNOWN); x->-oo, x>0 kisitiyla -oo CORRECT. Eski kodda ayni.
  F4 varyanti: limit pins celisik/bildirime aykiri baglamayi uyguluyor (a=2 & a>3; a positive & a=-2; a integer & a=1/2) -> CORRECT. Eski UNKNOWN. #14.
  BULGU F8: limit pins sonrasi yazili kosul False olursa (log(a), sqrt(a), a/a, factorial(a), gcd(a,2) ile a=-1/0/1/2/pi) extra filtresi
  (free_symbols=={var}) onu atiyor: lim x + log(a) - log(a) (a=-1) = 1 CORRECT, a*x/a (a=0) = 1 CORRECT. Eski kodda da CORRECT (onceden var; pins yolu kapatmadi).
  coverage: lim factorial(x-2)/x**x (x pos int, oo) eski CORRECT -> yeni UNKNOWN (§84 'gercel degiskende' degil; dusuk).
- p12_pinwritten (36 durum): F8 GENELLESTI: yalniz parametreyi anan yazili kosul (log(a), a*x/a, factorial(a)) verilenin
  sabitledigi degerde hic denetlenmiyor (domain_for: var kosulda yoksa _with_bound_values dokunmuyor, kosul 'several variables' diye atiliyor).
  a=-1 / a=0 iken der, tan, dint, ext, simp, eq, ineq, croots, domain_of hepsi CORRECT (29/36). Eski kodda ayni (onceden var).
- p13_ext (51), p14/p15: BULGU F9: extremum araliginin ucu sembol (b) iken -- verilen b=3 ile sabitlenmis, serbest ya da b positive --
  certify_extremum adayin (b) degeriyle karsilastirmasi karar verilemeyince 'daha iyi degil' sayip EVT ile onayliyor:
  max x [0,b], b=3 -> 0 CORRECT; min x [b,5], b=1 -> 5 CORRECT, dogru 1 INCORRECT; max x [0,b], b=3 -> 3 INCORRECT (not_attained);
  bos aralik [b,1], b=5 -> max 1 CORRECT. Eski kodda ayni (onceden var). Aralik baglamalarla yerine konmuyor.
- p16 (35, hepsi UNKNOWN: sembolik nokta/sinir guvenli), p17/p18: BULGU F10 (dusuk-orta): evaluate+verilen yolunda karar verilemeyen
  esitsizlik/alan uyeligi (x = atan1+atan2+atan3 = pi, x > pi) cozumu 'tutuyor' (in_domain None -> kept; _num_relation_holds None -> meets):
  tutarsiz IR'da y=7 CORRECT; x^2=T^2, x>pi, y=x/|x| -> 1 CORRECT (cozum yok). Eski kodda ayni. #14'un 'ne tutulur ne dusurulur' ilkesiyle celisik.
- Sonda sayaci (yaklasik): p01 42, p02 35, p03 16, p04 24, p05 21, p06 21, p07 49, p08 11, p09 50, p10 38, p11 44, p12 36, p13 51, p14 10, p15 17, p16 35, p17 11, p18 11 = 522
- p19_solve: 50 durum, bulgu yok (periyodik solve_equation guvenli)
- p21_period (37 durum): BULGU F11 (YUKSEK): sp.solveset(periyodik esitsizlik, x, Reals) yalniz [0, 2pi) donduruyor
  (sin(x)>0 -> (0,pi); tan(x)>1 -> (pi/4,pi/2); Ne(cos(x),0) -> [0,2pi) eksi noktalar). domain_for (kisit, yan kosul, yazili kosul),
  _with_given_inequalities, extremum._conditions_on, count_integers bunu tanim kumesi sayiyor:
  domain_of log(sin(x)) -> (0,pi) CORRECT; 1/cos(x) -> [0,2pi)\{..} CORRECT; x^2=49 & sin(x)>0 -> {} CORRECT, {7} INCORRECT;
  x^2+tan(x)-tan(x)=4 -> {2} CORRECT; cint 0..10 & sin>0 -> 3 CORRECT (dogru 6). Yeni 28/37, eski 20/37:
  #14 yeni gorevlere tasidi (count_roots domain_for, extremum cut, domain_of yan kosul: ext max -(x-7)^2 sin>0 -> 0 eski CORRECT yeni INCORRECT).
- p22_inf (22), p23_dod (56): yalniz F11 varyanti (x int + cons sin(x)>0). dod yazimlari guvenli.
- cmp.py: eski/yeni farklari incelendi (p01,p07,p09,p10,p13,p16,p19,p22,p23): eski CORRECT -> yeni UNKNOWN olanlarin hepsi ya eski yanlis onay ya §84 listesinde.
- p24_param (23): bulgu yok. p25_badgiven (60): F1 GENISLEDI (F12 birlesti): okunamayan verilen yazimlari ("x > 0 and x < 3",
  "x > 0, x < 3", "x in (0, 3)", "(x>0) & (x<3)", "x ∈ (0,3)", "x>0 ve x<3", "x > 0; x < 3") side_conditions ve extremum._conditions_on'da
  'except: continue' ile sessizce dusuyor -> ineq/croots/domain_of/extremum yanlis CORRECT (41/60). solve_equation UNKNOWN (tutarsiz). Eski 49/60.
- p26_calc (26): BULGU F13 (onceden var): antiderivative alan okumasi tutarsiz: x positive iken 1/x icin log(-x) CORRECT (x>0'da tanimsiz);
  cons x>0 iken |x| icin x^2/2 INCORRECT (dogru); given x<0 iken 1/x icin log(-x) INCORRECT (cons x<0 ile CORRECT). Eski ayni.
- SIRADAKI: bagimsiz matematik dogrulamasi (mpmath), repro betikleri, bulgular.json.
- repro/ altinda F1..F14 betikleri yazildi ve iki kopyada kosuldu (sonuclar notlardaki gibi). F6 PYTHONHASHSEED'e bagli: seed 0,1,2,4-7 INCORRECT, seed 3 UNKNOWN.
- p28_crash (55): cokme/takilma yok (en uzun 9.6 s). p29_closedgiven (12): F4 GENISLEDI (#14): baglama verileninin yazili tanimliligi
  denetlenmiyor: a = 4 + log(-1) - log(-1) -> a=4, x^2=a {-2,2} CORRECT (eski INCORRECT); a = 0**0 -> 1 (gelenek); a = sqrt(-4)**2 -> -4.
- p30_zeropow (7): BULGU F16 (onceden var): 0**0 = 1 gelenegi sessizce: evaluate 0**0 -> 1 CORRECT; x**0 = 1 -> Reals CORRECT, R\{0} INCORRECT;
  Sum(0**k, k=0..3) ise UNKNOWN (tutarsiz). DECISIONS'ta 0^0 karari yok.
- Toplam sonda ~900 durum (yeni), cogu eski kopyada da.
- SONRAKI: bulgular.json + StructuredOutput.
- bulgular.json yazildi: G1..G14 (G1=F1+F12, G2=F11, G3=F5, G4=F9, G5=F2, G6=F7(+turev tutarsizligi), G7=F4+F15, G8=F3, G9=F8, G10=F10, G11=F6, G12=F13, G13=F16, G14=F14).
- DURUM: rapor (StructuredOutput) asamasi.

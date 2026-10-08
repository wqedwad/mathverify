export const meta = {
  name: 'd4-saldiri',
  description: 'Bir d4 düzeltme parçasının diffine iki lensli bağımsız saldırgan gözden geçirme ve her bulgunun bağımsız doğrulanması',
  phases: [{ title: 'Saldırı', detail: 'iki lens: yanlış onay; haksız ret/kapsama/takılma' }, { title: 'Doğrulama', detail: 'her bulgu bağımsız yeniden üretim + matematik' }],
}
const A = args
const SP = '/tmp/claude-0/-home-user-asd/e165cf01-9b9f-5e2f-87e7-b8341da4ce60/scratchpad'
const DIR = `${SP}/d4/saldiri/${A.parca}`
const FINDINGS = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      klass: { type: 'string', enum: ['false_accept', 'unjust_reject', 'coverage_loss', 'crash_or_timeout', 'nondeterminism', 'other'] },
      severity: { type: 'string', enum: ['high', 'medium', 'low'] },
      title: { type: 'string' },
      repro: { type: 'string', description: 'Tam, kendi başına çalışan Python kodu (verify çağrısı, IR ve iddia) ya da bir sonda dosyasının yolu + vaka adı' },
      expected: { type: 'string' },
      actual_new: { type: 'string', description: 'yeni kodda (A.commit) ölçülen karar/durum' },
      actual_base: { type: 'string', description: 'taban kodda (A.taban) ölçülen karar/durum' },
      math: { type: 'string', description: 'doğru cevabın bağımsız matematik gerekçesi (gerekirse mpmath yüksek hassasiyet)' },
      introduced_by_piece: { type: 'string', enum: ['yes', 'no', 'unknown'] },
      mechanism: { type: 'string', description: 'kök neden: dosya:fonksiyon ve neden' },
    }, required: ['id', 'klass', 'severity', 'title', 'repro', 'expected', 'actual_new', 'actual_base', 'math', 'introduced_by_piece', 'mechanism'] } },
    probes_run: { type: 'integer' },
    summary: { type: 'string' },
  },
  required: ['findings', 'probes_run', 'summary'],
}
const VERDICT = {
  type: 'object',
  properties: {
    reproduced: { type: 'boolean' },
    math_expected_correct: { type: 'boolean', description: 'bulgunun beklentisi matematikçe/gelenekçe doğru mu (CLAUDE.md ilkesi: yanlış olabilecek cevaba CORRECT yok, gelenek/kanıtsızlık UNKNOWN)' },
    real: { type: 'boolean', description: 'gerçek bir hata mı (yeniden üretildi VE beklenti doğru VE gözlenen karar beklentiye aykırı)' },
    introduced_by_piece: { type: 'string', enum: ['yes', 'no', 'unknown'] },
    severity: { type: 'string', enum: ['high', 'medium', 'low'] },
    corrected_expectation: { type: 'string' },
    note: { type: 'string' },
  },
  required: ['reproduced', 'math_expected_correct', 'real', 'introduced_by_piece', 'severity', 'corrected_expectation', 'note'],
}
const COMMON = `Bağlam: mathverify (/home/user/asd), Türkçe matematik sorusu + çözüm için CORRECT/INCORRECT/UNKNOWN veren kanıta dayalı doğrulayıcı. CLAUDE.md'nin değişmez ilkeleri geçerli; en önemlisi: doğrulayıcı yanlış olabilecek hiçbir cevaba CORRECT demez; anlam bir geleneğe bağlıysa ya da kanıtlanamıyorsa UNKNOWN; doğru cevabın haksız reddi (INCORRECT) de hatadır.
Gözden geçirilen parça: ${A.parca}. ${A.odak}
Yeni kod: commit ${A.commit}. Taban (parçasız): commit ${A.taban}. Parçanın diff'i: ${A.diff}.
Parçanın kendi kararları ve notları: ${A.notlar}.
ÇALIŞMA KURALLARI: Ana checkout /home/user/asd'ye YAZMA, orada git checkout/stash/reset/commit YASAK; yalnız 'git -C /home/user/asd show/diff/log/archive' ile oku. Kendi kopyalarını şuraya kur: mkdir -p <dizin> && git -C /home/user/asd archive <commit> | tar -x -C <dizin> (kopya .env içerir; işin bitince kopyaları rm -rf ile sil). Python: /home/user/asd/.venv/bin/python, ortam PYTHONUTF8=1 PYTHONPATH=<kopya>/src:<kopya> MATHVERIFY_LEAN_REPL=/nonexistent; her komutu timeout ile sınırla (tek komut ≤10 dk). Sondaları gerçek dosyalara yaz, 'if __name__ == "__main__":' içinde (sandbox spawn kullanır), toplu koş, çıktıya yalnız özet yazdır. Var olan sondaları ve düzenekleri yeniden kullan: denetim/2026-10-01/<parça>/sonda.py, tests/test_d4_*.py (verify çağırma kalıpları orada). Makinede başka ağır işler var: aynı anda en çok 2 ağır süreç.
Bulgu ölçütü: her bulgu yeni kodda ÖLÇÜLMÜŞ olmalı (actual_new), tabanda da ölçülmeli (actual_base) ve doğru cevabın matematiği bağımsız hesaplanmalı (sembolik akıl yürütme + gerekirse mpmath 50+ basamak). Matematikçe emin olmadığın beklentiyi bulgu yapma ya da severity low ve math alanında belirsizliği yaz. Aynı kök nedenli vakaları tek bulguda topla (repro'da 2-3 örnek). Çıktın yapılandırılmış bulgu listesi.`
const LENSES = [
  { key: 'yanlis-onay', prompt: `${COMMON}
SENİN LENSİN: YANLIŞ ONAY avcısı. Parçanın değiştirdiği mekanizmalarda ve aynı kalıbın kardeş yollarında (aynı yardımcıyı çağıran başka görevler: eq/solve, solve_inequality, evaluate, count_solutions, extremum, domain, adım reddedici compute/eq adımları) yanlış bir cevabın CORRECT aldığı ya da yanlış bir adımın verified olduğu girdiler bul. Korumanın tek yazıma mı yoksa mekanizmaya mı konduğunu sına: eşdeğer yazımlar (LaTeX, farklı fonksiyon adları, iç içe, parametreli, verilenlerle sabitlenmiş sembol, bileşik fonksiyon argümanı), sınır durumları (kökte/kutupta/aralık ucunda değer, sign(0), Max/Min eşitliği, katlı kök, boş küme, sonsuz küme). Çalışma dizinin: ${DIR}/yanlis-onay.` },
  { key: 'ret-kapsama', prompt: `${COMMON}
SENİN LENSİN: HAKSIZ RET, KAPSAMA KAYBI ve SAĞLAMLIK avcısı. Parçanın getirdiği (tabanda olmayan) şu durumları bul: doğru cevabın INCORRECT alması ya da doğru adımın refuted olması; tabanda kanıtlı biçimde doğru karar verilen (CORRECT/INCORRECT) bir vakanın gereksiz yere UNKNOWN'a düşmesi (gerekçesi yoksa); istisna/layer_exception, 60 s'yi aşan tek verify, PYTHONHASHSEED ya da sıraya bağlı karar. Ayrıca parçanın kendi sondasındaki ve testlerindeki beklentilerin matematiğini denetle: yanlış beklenti (testin doğru diye kilitlediği yanlış karar) da bulgudur. Çalışma dizinin: ${DIR}/ret-kapsama.` },
]
const results = await pipeline(
  LENSES,
  l => agent(l.prompt, { label: `saldiri:${A.parca}:${l.key}`, phase: 'Saldırı', schema: FINDINGS }),
  (rev, l) => {
    if (!rev) return []
    log(`${l.key}: ${rev.findings.length} bulgu, ${rev.probes_run} sonda`)
    return parallel(rev.findings.map(f => () => agent(`${COMMON}
SEN BAĞIMSIZ DOĞRULAYICISIN (şüpheci). Bir saldırgan gözden geçirici şu bulguyu bildirdi; varsayılan tavrın şüphe. Kendi kopyanı kur (${DIR}/dogrulama-${l.key}-${f.id}), bulguyu yeni kodda (${A.commit}) ve tabanda (${A.taban}) KENDİN yeniden üret ve doğru cevabın matematiğini bulgudan BAĞIMSIZ hesapla. Beklenti matematikçe ya da gelenekçe yanlışsa (ör. doğru cevap aslında tartışmalı ve UNKNOWN uygun, ya da saldırganın 'doğru' dediği yanlış) bunu söyle ve doğru beklentiyi yaz. real = yeniden üretildi VE beklenti doğru VE gözlenen karar ona aykırı.
BULGU: ${JSON.stringify(f)}`, { label: `dogrula:${l.key}:${f.id}`, phase: 'Doğrulama', schema: VERDICT })
      .then(v => ({ lens: l.key, ...f, verdict: v }))))
  },
)
const all = results.flat().filter(Boolean)
const real = all.filter(f => f.verdict && f.verdict.real)
log(`toplam ${all.length} bulgu, doğrulanan ${real.length}`)
return { parca: A.parca, toplam: all.length, dogrulanan: real.length, bulgular: all }

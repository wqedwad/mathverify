export const meta = {
  name: 'd4-saldiri-v4',
  description: 'Bir d4 parçasına iki lensli bağımsız saldırı + devralınan adayların bağımsız doğrulanması; her grubun bulgularını tek toplu bağımsız doğrulayıcı doğrular; kısa sonuç',
  phases: [{ title: 'Saldırı', detail: 'iki lens: yanlış onay; haksız ret/kapsama/takılma' }, { title: 'Doğrulama', detail: 'lens başına tek toplu bağımsız doğrulayıcı' }],
}
const A = args
const SP = '/tmp/claude-0/-home-user-asd/0a3a0f70-84de-519b-bab3-552b100d2487/scratchpad'
const DIR = `${SP}/d4/saldiri/${A.parca}`
const FINDINGS = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      klass: { type: 'string', enum: ['false_accept', 'unjust_reject', 'coverage_loss', 'crash_or_timeout', 'nondeterminism', 'other'] },
      severity: { type: 'string', enum: ['high', 'medium', 'low'] },
      title: { type: 'string' },
      repro: { type: 'string', description: 'kendi başına çalışan Python kodu ya da sonda dosyasının yolu + vaka adı' },
      expected: { type: 'string' }, actual_new: { type: 'string' }, actual_base: { type: 'string' },
      math: { type: 'string' }, introduced_by_piece: { type: 'string', enum: ['yes', 'no', 'unknown'] }, mechanism: { type: 'string' },
    }, required: ['id', 'klass', 'severity', 'title', 'repro', 'expected', 'actual_new', 'actual_base', 'math', 'introduced_by_piece', 'mechanism'] } },
    probes_run: { type: 'integer' }, summary: { type: 'string' },
  },
  required: ['findings', 'probes_run', 'summary'],
}
const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, reproduced: { type: 'boolean' }, math_expected_correct: { type: 'boolean' }, real: { type: 'boolean' },
      introduced_by_piece: { type: 'string', enum: ['yes', 'no', 'unknown'] }, severity: { type: 'string', enum: ['high', 'medium', 'low'] },
      corrected_expectation: { type: 'string' }, note: { type: 'string' },
    }, required: ['id', 'reproduced', 'math_expected_correct', 'real', 'introduced_by_piece', 'severity', 'corrected_expectation', 'note'] } },
    file: { type: 'string' },
  },
  required: ['verdicts', 'file'],
}
const COMMON = `Bağlam: mathverify (/home/user/asd), Türkçe matematik sorusu + çözüm için CORRECT/INCORRECT/UNKNOWN veren kanıta dayalı doğrulayıcı. CLAUDE.md'nin değişmez ilkeleri geçerli; en önemlisi: doğrulayıcı yanlış olabilecek hiçbir cevaba CORRECT demez; anlam bir geleneğe bağlıysa ya da kanıtlanamıyorsa UNKNOWN; doğru cevabın haksız reddi (INCORRECT) de hatadır.
Gözden geçirilen parça: ${A.parca}. ${A.odak}
Yeni kod: commit ${A.commit}. Taban: commit ${A.taban}. Diff: ${A.diff}.
Parçanın kararları ve notları: ${A.notlar}.
ÇALIŞMA KURALLARI: Ana checkout /home/user/asd'ye YAZMA, orada git checkout/stash/reset/commit YASAK; yalnız 'git -C /home/user/asd show/diff/log/archive' ile oku. Kendi kopyanı kur: mkdir -p <dizin> && git -C /home/user/asd archive <commit> | tar -x -C <dizin> (kopya .env içerir; işin bitince rm -rf ile sil). Python: /home/user/asd/.venv/bin/python, ortam PYTHONUTF8=1 PYTHONPATH=<kopya>/src:<kopya> MATHVERIFY_LEAN_REPL=/nonexistent; her komutu timeout ile sınırla (tek komut ≤10 dk). Sondaları gerçek dosyalara yaz, 'if __name__ == "__main__":' içinde; toplu koş, çıktıya yalnız özet yazdır. Var olan sondaları ve testleri (denetim/2026-10-01/<parça>/sonda.py, tests/test_d4_*.py) kalıp olarak kullan. Makinede başka ağır işler var (bir düzeltici ajan ve ana oturumun ölçümleri): SEN hafif çalış: aynı anda en çok 1 sonda süreci, her sonda koşusu ≤5 dk (küçük, hedefli sonda dosyaları); parçanın tam sondasını, tam test takımını, mutasyonu ya da fark.py'yi KOŞMA (ana oturum ölçer); uptime yükü 6'yı aşarsa kısa bekle. Tek bekleme ≤10 dk. Büyük dosyaları bütün okuma (grep + satır aralığı).
Bulgu ölçütü: her bulgu yeni kodda ve tabanda ÖLÇÜLMÜŞ olmalı, doğru cevabın matematiği bağımsız hesaplanmalı (gerekirse mpmath 50+ basamak). Emin olmadığın beklentiyi bulgu yapma ya da severity low ve math'ta belirsizliği yaz. Aynı kök nedenli vakaları tek bulguda topla. Önceki saldırıların bulgularını yeniden bildirme (yalnız kapanmadıysa, açıkça belirterek).`
const LENSES = [
  { key: 'yanlis-onay', prompt: `${COMMON}\nSENİN LENSİN: YANLIŞ ONAY avcısı. Parçanın değiştirdiği mekanizmalarda ve kardeş yollarında yanlış cevabın CORRECT ya da yanlış adımın verified olduğu girdiler bul. Korumanın tek yazıma mı mekanizmaya mı konduğunu sına (eşdeğer yazımlar, LaTeX, parametreli, verilenle sabitlenmiş sembol, iç içe, sınır durumları). Çalışma dizinin: ${DIR}/yanlis-onay.` },
  { key: 'ret-kapsama', prompt: `${COMMON}\nSENİN LENSİN: HAKSIZ RET, KAPSAMA KAYBI ve SAĞLAMLIK avcısı. Parçanın getirdiği (tabanda olmayan) şu durumları bul: doğru cevaba INCORRECT ya da doğru adıma refuted; tabanda kanıtlı karar verilen vakanın gerekçesiz UNKNOWN'a düşmesi; istisna, 60 s'yi aşan tek verify, PYTHONHASHSEED ya da sıraya bağlı karar. Parçanın sonda ve test beklentilerinin matematiğini de denetle. Çalışma dizinin: ${DIR}/ret-kapsama.` },
]
const ITEMS = A.devralinan && A.devralinan.length ? LENSES.concat([{ key: 'devralinan', inherited: A.devralinan }]) : LENSES
const results = await pipeline(
  ITEMS,
  l => l.inherited ? { findings: l.inherited, probes_run: 0, summary: 'devralınan adaylar (önceki yarım saldırıdan; bağımsız doğrulanacak)' }
    : agent(l.prompt, { label: `saldiri:${A.parca}:${l.key}`, phase: 'Saldırı', schema: FINDINGS }),
  (rev, l) => {
    if (!rev || rev.findings.length === 0) return { lens: l.key, findings: [], verdicts: [], file: null }
    return agent(`${COMMON}
SEN BAĞIMSIZ DOĞRULAYICISIN (şüpheci). Bir saldırgan gözden geçirici aşağıdaki ${rev.findings.length} bulguyu bildirdi; varsayılan tavrın şüphe. TEK bir kopya kur (${DIR}/dogrulama-${l.key}/yeni ve /taban) ve bulguların HER BİRİNİ sırayla yeni kodda (${A.commit}) ve tabanda (${A.taban}) KENDİN yeniden üret; doğru cevabın matematiğini bulgudan BAĞIMSIZ hesapla (gerekirse mpmath). Beklenti matematikçe ya da gelenekçe yanlışsa söyle ve doğru beklentiyi yaz. real = yeniden üretildi VE beklenti doğru VE gözlenen karar ona aykırı. Her bulguya aynı derinlikte bak; toplu olman yalnız kurulumu paylaşmak içindir.
Sonunda bulguları ve kararlarını birleştirip ${DIR}/bulgular-${l.key}.json dosyasına yaz (her öğe: bulgunun bütün alanları + 'verdict' nesnesi) ve file alanında bu yolu döndür. verdicts listesinde note ≤ 400, corrected_expectation ≤ 600 karakter olsun (ayrıntı dosyada).
BULGULAR: ${JSON.stringify(rev.findings)}`, { label: `dogrula:${A.parca}:${l.key}`, phase: 'Doğrulama', schema: VERDICTS })
      .then(v => ({ lens: l.key, findings: rev.findings, verdicts: v ? v.verdicts : [], file: v ? v.file : null }))
  },
)
const ok = results.filter(Boolean)
const ozet = []
for (const r of ok) {
  for (const f of r.findings) {
    const v = r.verdicts.find(x => x.id === f.id) || {}
    ozet.push({ lens: r.lens, id: f.id, klass: f.klass, real: v.real === undefined ? null : v.real, intro: v.introduced_by_piece || f.introduced_by_piece, sev: v.severity || f.severity, title: f.title.slice(0, 160) })
  }
}
return { parca: A.parca, toplam: ozet.length, dogrulanan: ozet.filter(o => o.real).length, dosyalar: ok.map(r => r.file).filter(Boolean), ozet }

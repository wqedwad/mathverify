# scripts/dev — geliştirme betikleri

Bu betikler **kapıların parçası değildir**; hiçbir test ya da `scripts/check.py` onları çağırmaz.
Fazlar geliştirilirken elle kullanıldılar ve yeniden işe yarayabilecekleri için tutuluyorlar.
Hepsi proje kökünden, `PYTHONUTF8=1` ile çalıştırılır: Windows'ta
`.venv/Scripts/python.exe scripts/dev/<ad>.py`, Linux'ta ve bulutta
`.venv/bin/python scripts/dev/<ad>.py`.

| Betik | Ne yapar | Gerektirdiği |
|---|---|---|
| `smoke_f2.py` | F2 sertifikalarının (geometri, seriler, lineer cebir) elle yazılmış doğru/yanlış örneklerde kararı | yalnız yerel |
| `smoke_lean.py` | Lean yazıcısı + taktik merdiveni birkaç öğede; ifadeyi, ispatı ve denetimi basar | Lean (Windows'ta WSL içinde, Linux'ta yerel) |
| `lean_try.py` | Aday taktikleri canlı REPL'de somut hedeflere karşı dener (yeni Lean şablonu geliştirirken) | Lean (Windows'ta WSL içinde, Linux'ta yerel) |
| `smoke_extract.py` | Birkaç öğede soru metninden IR çıkarımı ve elle IR ile karar karşılaştırması | **API kredisi** |
| `smoke_llm.py` | İki model ailesine birer yapısal çağrı | **API kredisi** |
| `clean_imports.py` | pyflakes'in bildirdiği kullanılmayan import adlarını **dosyalarda siler** (bilinçli olanlar `KEEP` içinde) | pyflakes |

`lean_try.py` içindeki bazı adaylar (`Matrix.dotProduct`) bugün elaborate olmaz; F5 geliştirme
kaydıdır (HANDOFF §4). Çalışan taktikler `src/mathverify/formal/prove.py` içindedir.

`scripts/diag_sandbox.py` 23 Eylül 2026'da silindi: yaptığı her şeyi (çağrı, zaman aşımı,
`mem_mode`) `tests/test_sandbox.py` sınıyor.

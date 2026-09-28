# scripts/dev/windows_full.ps1 - check.py --full on Windows, with a memory log (HANDOFF T8).
#
# The first Windows attempt (26 Sep 2026) froze Git Bash during or after the tests; the step and
# the cause were never known. This runs the same --full from PowerShell, sends its console output
# to a file instead of the window, and samples memory every 10 s (free RAM, the WSL VM that holds
# Lean, the Python processes) so a freeze leaves a record of what was happening.
#
# Run from the project root in PowerShell (not Git Bash), on a clean tree:
#     powershell -ExecutionPolicy Bypass -File scripts\dev\windows_full.ps1
# Output: %TEMP%\mathverify-full\ (console.txt, errors.txt, mem.csv, check_full.log copy,
# summary.txt). Nothing is written in the repository except what check.py itself writes
# (reports\). Afterwards `git restore reports/` puts the committed reports back.
#
# ASCII only on purpose: Windows PowerShell 5.1 reads a script without a BOM in the ANSI code page.

$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path (Join-Path $root 'scripts\check.py')) -or -not (Test-Path $py)) {
    Write-Host 'Proje kokunden calistirin (scripts\check.py ve .venv\Scripts\python.exe bulunamadi).'
    exit 2
}
$dirty = git status --porcelain
if ($dirty) {
    Write-Host 'Calisma agaci temiz degil; --full olcumu gecersiz olur. Once commit edin ya da geri alin:'
    $dirty | ForEach-Object { Write-Host "  $_" }
    exit 2
}

$out = Join-Path $env:TEMP 'mathverify-full'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$mem = Join-Path $out 'mem.csv'
$console = Join-Path $out 'console.txt'
$errors = Join-Path $out 'errors.txt'
$summary = Join-Path $out 'summary.txt'
Remove-Item -Force -ErrorAction SilentlyContinue $mem, $console, $errors, $summary

$os = Get-CimInstance Win32_OperatingSystem
$totalMB = [math]::Round($os.TotalVisibleMemorySize / 1024)
$cDisk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$cFreeGB = [math]::Round($cDisk.FreeSpace / 1GB, 1)
$wslconfig = Join-Path $env:USERPROFILE '.wslconfig'
$wslMem = if (Test-Path $wslconfig) { (Select-String -Path $wslconfig -Pattern '^\s*memory\s*=' | Select-Object -First 1).Line } else { 'yok (.wslconfig yok: WSL varsayilani)' }
$head = @(
    "baslangic: $(Get-Date -Format 's')",
    "commit: $(git rev-parse --short HEAD) ($(git rev-parse --abbrev-ref HEAD))",
    "RAM: $totalMB MB, islemci: $($env:NUMBER_OF_PROCESSORS), C: bos $cFreeGB GB",
    "WSL bellek ayari: $wslMem"
)
# Out-File -Encoding utf8, not Tee-Object: in PowerShell 5.1 Tee-Object writes UTF-16 (measured 27 Sep).
$head | Out-File -FilePath $summary -Encoding utf8
$head | ForEach-Object { Write-Host $_ }

# Memory sampler: a separate job, so a stuck check.py does not stop the record.
$sampler = Start-Job -ArgumentList $mem -ScriptBlock {
    param($path)
    'time,free_mb,commit_used_mb,wsl_vm_mb,python_n,python_mb,top_process,top_mb' | Out-File -FilePath $path -Encoding ascii
    while ($true) {
        $o = Get-CimInstance Win32_OperatingSystem
        $free = [math]::Round($o.FreePhysicalMemory / 1024)
        $commit = [math]::Round(($o.TotalVirtualMemorySize - $o.FreeVirtualMemory) / 1024)
        $vm = Get-Process -Name vmmem, vmmemWSL -ErrorAction SilentlyContinue | Measure-Object -Property WorkingSet64 -Sum
        $pyp = Get-Process -Name python -ErrorAction SilentlyContinue | Measure-Object -Property WorkingSet64 -Sum
        $top = Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 1
        $line = '{0},{1},{2},{3},{4},{5},{6},{7}' -f (Get-Date -Format 'HH:mm:ss'), $free, $commit,
            [math]::Round($vm.Sum / 1MB), $pyp.Count, [math]::Round($pyp.Sum / 1MB), $top.ProcessName,
            [math]::Round($top.WorkingSet64 / 1MB)
        $line | Out-File -FilePath $path -Append -Encoding ascii
        Start-Sleep -Seconds 10
    }
}

$env:PYTHONUTF8 = '1'
$t0 = Get-Date
$proc = Start-Process -FilePath $py -ArgumentList 'scripts\check.py', '--full' -WorkingDirectory $root `
    -RedirectStandardOutput $console -RedirectStandardError $errors -NoNewWindow -PassThru
$null = $proc.Handle     # PowerShell 5.1 reports no ExitCode unless the handle was taken early
Write-Host "check.py --full basladi (PID $($proc.Id)). Ilerleme her 60 s'de; donarsa baska bir"
Write-Host "PowerShell'de:  Get-Content $mem -Tail 5 ;  Get-Content reports\check_full.log -Tail 5"

$log = Join-Path $root 'reports\check_full.log'
while (-not $proc.HasExited) {
    Start-Sleep -Seconds 60
    $mins = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
    $last = if (Test-Path $log) { (Get-Content $log -Tail 1 -Encoding UTF8) } else { '(gunluk henuz yok)' }
    $m = Get-Content $mem -Tail 1 -ErrorAction SilentlyContinue
    Write-Host "[$mins dk] $last | bellek: $m"
}
$proc.WaitForExit()
$elapsed = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
Stop-Job $sampler | Out-Null
Remove-Job $sampler -Force | Out-Null

Copy-Item -Force $log (Join-Path $out 'check_full.log') -ErrorAction SilentlyContinue
$rows = Import-Csv $mem
function Col($name) { $rows | ForEach-Object { [double]$_.$name } }
$minFree = (Col 'free_mb' | Measure-Object -Minimum).Minimum
$maxWsl = (Col 'wsl_vm_mb' | Measure-Object -Maximum).Maximum
$maxPy = (Col 'python_mb' | Measure-Object -Maximum).Maximum
$maxPyN = (Col 'python_n' | Measure-Object -Maximum).Maximum
$result = @(
    "bitis: $(Get-Date -Format 's'), sure: $elapsed dk, cikis kodu: $($proc.ExitCode)",
    "bellek: en az bos $minFree MB (toplam $totalMB), WSL en cok $maxWsl MB, python en cok $maxPy MB ($maxPyN surec)",
    'adimlar:'
)
if (Test-Path $log) {
    $result += Get-Content $log -Encoding UTF8 | Where-Object { $_ -match '^\s+\w+: \d+ s \(exit' -or $_ -match 'kapi gecti|kap. ge.ti' }
}
$result | Out-File -FilePath $summary -Append -Encoding utf8
$result | ForEach-Object { Write-Host $_ }
Write-Host ''
Write-Host "Kayitlar: $out  (summary.txt, mem.csv, console.txt, check_full.log)"
Write-Host 'Raporlari geri almak icin: git restore reports/'

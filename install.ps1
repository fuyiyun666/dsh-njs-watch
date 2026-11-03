# install.ps1 -- one-shot installer for dsh-njs-watch (Windows)
# Usage:  powershell -ExecutionPolicy Bypass -File .\install.ps1 [-Profile desktop]
param([string]$Profile = "desktop", [switch]$SkipDeps, [switch]$SkipPlugin)

$ErrorActionPreference = "Stop"
$spec = "https://github.com/fuyiyun666/dsh-njs-watch/releases/download/v0.1.0/dsh-njs-watch-0.1.0.tgz"

if (-not $SkipDeps) {
Write-Host "[1/3] Python dependencies..."
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw "Python not found. Install Python 3.10+ first." }
& $py -m pip install --upgrade numpy pillow opencv-python
# optional OCR (ignore failures on non-Windows)
try { & $py -m pip install winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging winrt-Windows.Storage winrt-Windows.Globalization winrt-Windows.Foundation } catch { Write-Host "  (OCR packages skipped)" }

}
if (-not $SkipPlugin) {
Write-Host "[2/3] Installing plugin into profile '$Profile'..."
dsh plugin --profile $Profile add $spec
}

Write-Host "[3/3] Enabling in profile patch..."
$dir = Join-Path $env:USERPROFILE ".dsh\profiles\$Profile"
$patch = Join-Path $dir "cordis.patch.yml"
$block = @"
- insert:
    - id: njs-watch
      name: 'dsh-njs-watch'
      config:
        ocr: true
        maxSeconds: 120
"@
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
$existing = ""
if (Test-Path $patch) { $existing = Get-Content $patch -Raw -Encoding UTF8 }
if ($existing -notmatch "njs-watch") {
  Add-Content -Path $patch -Value $block -Encoding UTF8
  Write-Host "  added entry to $patch"
} else {
  Write-Host "  entry already present in $patch"
}

Write-Host ""
Write-Host "Done. Restart DSH, then check for tools: watch_screen / watch_file / watch_note / watch_clean"

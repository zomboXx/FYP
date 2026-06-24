param()

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Source = Join-Path $Root "src"
$BundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

function Test-Python([string]$Candidate) {
    if (-not $Candidate -or -not (Test-Path $Candidate)) {
        return $false
    }
    try {
        & $Candidate -c "import sys" | Out-Null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Find-Python {
    $candidates = @(
        (Join-Path $Root ".venv\Scripts\python.exe"),
        $BundledPython
    )
    foreach ($candidate in $candidates) {
        if (Test-Python $candidate) {
            return $candidate
        }
    }
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command -and (Test-Python $command.Source)) {
        return $command.Source
    }
    throw "Không tìm thấy Python chạy được."
}

function Set-AppPythonPath {
    $env:PYTHONPATH = $Source
}

Set-Location $Root
Set-AppPythonPath
$Python = Find-Python

Write-Host "Compile source..." -ForegroundColor Cyan
& $Python -m compileall src
& $Python -m compileall api

Write-Host "Run tests..." -ForegroundColor Cyan
& $Python -m pytest -q

Write-Host "Scan for stale comments/debug code..." -ForegroundColor Cyan
$patterns = "TODO|FIXME|print\(|console\.log|^\s*#\s*(def|class|return|import|from)\b"
$files = Get-ChildItem -Path src, api, tests -Recurse -File -Include *.py -ErrorAction SilentlyContinue
$matches = $files | Select-String -Pattern $patterns
if ($matches) {
    $matches | ForEach-Object { Write-Host "$($_.Path):$($_.LineNumber): $($_.Line)" -ForegroundColor Yellow }
    throw "Tìm thấy TODO/FIXME/debug print hoặc code bị comment-out."
}

Write-Host "Pre-check passed." -ForegroundColor Green

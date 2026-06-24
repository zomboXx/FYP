param(
    [int]$Port = 8000,
    [switch]$Install
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Source = Join-Path $Root "src"
$Requirements = Join-Path $Root "requirements.txt"
$RootVenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$BundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

function Test-Python([string]$Candidate) {
    if (-not $Candidate) {
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
    if ((Test-Path $RootVenvPython) -and (Test-Python $RootVenvPython)) {
        return $RootVenvPython
    }
    if ((Test-Path $BundledPython) -and (Test-Python $BundledPython)) {
        return $BundledPython
    }
    $commands = @("python", "py")
    foreach ($command in $commands) {
        $candidate = Get-Command $command -ErrorAction SilentlyContinue
        if ($candidate -and (Test-Python $candidate.Source)) {
            return $candidate.Source
        }
    }
    throw "Khong tim thay Python. Hay cai Python 3.12 va chay lai."
}

function Set-AppPythonPath {
    $env:PYTHONPATH = $Source
}

function Test-PortFree([int]$CandidatePort) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), $CandidatePort)
    try {
        $listener.Start()
        return $true
    }
    catch {
        return $false
    }
    finally {
        $listener.Stop()
    }
}

function Find-FreePort([int]$StartPort) {
    for ($candidate = $StartPort; $candidate -lt ($StartPort + 20); $candidate++) {
        if (Test-PortFree $candidate) {
            return $candidate
        }
    }
    throw "Khong tim thay port trong khoang $StartPort-$($StartPort + 19)."
}

Set-Location $Root
$Python = Find-Python
Set-AppPythonPath

if ($Install) {
    & $Python -m pip install -r $Requirements
}

try {
    & $Python -c "import fastapi, uvicorn, flet, flet_web, flet_map" | Out-Null
}
catch {
    Write-Host "Thieu dependency. Dang cai requirements..." -ForegroundColor Yellow
    & $Python -m pip install -r $Requirements
}

$ActualPort = Find-FreePort $Port
if ($ActualPort -ne $Port) {
    Write-Host "Port $Port dang ban, chuyen sang port $ActualPort." -ForegroundColor Yellow
}

Set-AppPythonPath
Write-Host "Dang chay Find Your Path tai http://127.0.0.1:$ActualPort" -ForegroundColor Green
Write-Host "Nhan Ctrl+C trong terminal nay de dung server." -ForegroundColor DarkGray
& $Python -m uvicorn app.main:app --host 127.0.0.1 --port $ActualPort

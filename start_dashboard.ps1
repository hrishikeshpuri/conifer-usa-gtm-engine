param([ValidateRange(1024, 65535)][int]$Port = 8501)

$ErrorActionPreference = 'Stop'
$pythonPath = Join-Path $PSScriptRoot '.dashboard-venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'The dashboard environment is missing. Install requirements-dashboard.txt in .dashboard-venv first.'
}
Push-Location -LiteralPath $PSScriptRoot
try {
    & $pythonPath -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port $Port `
        --server.headless true --server.enableStaticServing false --browser.gatherUsageStats false `
        --theme.base light --theme.primaryColor '#16735d' --theme.backgroundColor '#f6f8f5' `
        --theme.secondaryBackgroundColor '#e9f0eb' --theme.textColor '#193a30'
    if ($LASTEXITCODE) { throw "Streamlit exited with status $LASTEXITCODE" }
} finally {
    Pop-Location
}

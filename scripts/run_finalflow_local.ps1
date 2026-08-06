[CmdletBinding()]
param(
    [switch]$PreparedDataOnly,

    [ValidateRange(1024, 65535)]
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonPath = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
$appPath = Join-Path $repositoryRoot "paddydash\app.py"
$envPath = Join-Path $repositoryRoot ".env"
$envValidatorPath = Join-Path $repositoryRoot "scripts\validation\check_local_env.py"

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "The project virtual environment is missing. Create .venv and install requirements first."
}

if (-not (Test-Path -LiteralPath $appPath -PathType Leaf)) {
    throw "The FinalFlow Streamlit entry point is missing: $appPath"
}

$previousDisableExists = Test-Path Env:FINALFLOW_DISABLE_OPENAI
$previousTelemetryExists = Test-Path Env:STREAMLIT_BROWSER_GATHER_USAGE_STATS
$previousDisable = $env:FINALFLOW_DISABLE_OPENAI
$previousTelemetry = $env:STREAMLIT_BROWSER_GATHER_USAGE_STATS

function Restore-ProcessEnvironmentValue {
    param(
        [string]$Name,
        [bool]$PreviouslyExisted,
        [AllowNull()][string]$PreviousValue
    )

    if ($PreviouslyExisted) {
        [Environment]::SetEnvironmentVariable($Name, $PreviousValue, "Process")
    }
    else {
        [Environment]::SetEnvironmentVariable($Name, $null, "Process")
    }
}

try {
    $env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"

    if ($PreparedDataOnly) {
        $env:FINALFLOW_DISABLE_OPENAI = "true"
        Write-Host "Starting FinalFlow in prepared-data mode (no OpenAI request)."
    }
    else {
        Remove-Item Env:FINALFLOW_DISABLE_OPENAI -ErrorAction SilentlyContinue
        & $pythonPath $envValidatorPath $envPath
        if ($LASTEXITCODE -ne 0) {
            throw (
                "Edit .env and save a valid OpenAI key. " +
                "The launcher does not accept API keys in the terminal."
            )
        }
        Write-Host "Using the saved local configuration from .env."
    }

    Push-Location $repositoryRoot
    try {
        & $pythonPath -c "import openai, plotly, pydantic, streamlit"
        if ($LASTEXITCODE -ne 0) {
            throw "A required package is missing. Install requirements.txt into .venv."
        }

        Write-Host "FinalFlow is starting at http://localhost:$Port"
        Write-Host "Keep this window open. Press Ctrl+C to stop the app."
        & $pythonPath -m streamlit run paddydash\app.py `
            --server.port $Port `
            --browser.gatherUsageStats false
        if ($LASTEXITCODE -ne 0) {
            throw "Streamlit exited with code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    Restore-ProcessEnvironmentValue "FINALFLOW_DISABLE_OPENAI" $previousDisableExists $previousDisable
    Restore-ProcessEnvironmentValue "STREAMLIT_BROWSER_GATHER_USAGE_STATS" $previousTelemetryExists $previousTelemetry
}

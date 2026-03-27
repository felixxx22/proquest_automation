param(
    [string]$ConfigPath = ".\run_params.psd1"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

$config = Import-PowerShellDataFile -Path $ConfigPath

function Escape-NativeEmbeddedQuotes {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    # Windows PowerShell mangles embedded double-quotes for native commands.
    # Escaping them with backslashes preserves quoted ProQuest query fragments.
    return $Value.Replace('"', '\"')
}

$searchQuery = $config.SearchQuery
if ([string]::IsNullOrWhiteSpace($searchQuery)) {
    throw "Config must include a non-empty SearchQuery value."
}

$searchQuery = Escape-NativeEmbeddedQuotes -Value ([string]$searchQuery)

$numFiles = if ($null -ne $config.NumFiles) { [int]$config.NumFiles } else { 3 }
$startDate = if ($null -ne $config.StartDate) { [string]$config.StartDate } else { "" }
$outputDir = if ($null -ne $config.OutputDir) { [string]$config.OutputDir } else { "" }
$researchEmail = if ($null -ne $config.ResearchEmail) { [string]$config.ResearchEmail } else { "" }
$researchPassword = if ($null -ne $config.ResearchPassword) { [string]$config.ResearchPassword } else { "" }

if (-not [string]::IsNullOrWhiteSpace($startDate)) {
    $startDate = Escape-NativeEmbeddedQuotes -Value $startDate
}
if (-not [string]::IsNullOrWhiteSpace($outputDir)) {
    $outputDir = Escape-NativeEmbeddedQuotes -Value $outputDir
}
if (-not [string]::IsNullOrWhiteSpace($researchEmail)) {
    $researchEmail = Escape-NativeEmbeddedQuotes -Value $researchEmail
}
if (-not [string]::IsNullOrWhiteSpace($researchPassword)) {
    $researchPassword = Escape-NativeEmbeddedQuotes -Value $researchPassword
}

$pythonExe = "python"
if ($null -ne $config.PythonExe -and -not [string]::IsNullOrWhiteSpace([string]$config.PythonExe)) {
    $pythonExe = [string]$config.PythonExe
}
elseif (Test-Path ".\env\Scripts\python.exe") {
    $pythonExe = ".\env\Scripts\python.exe"
}

$args = @("proquest_download.py", $searchQuery, "-n", $numFiles)

if (-not [string]::IsNullOrWhiteSpace($startDate)) {
    $args += @("-d", $startDate)
}

if (-not [string]::IsNullOrWhiteSpace($outputDir)) {
    $args += @("-o", $outputDir)
}

if (-not [string]::IsNullOrWhiteSpace($researchEmail)) {
    $args += @("--research-email", $researchEmail)
}

if (-not [string]::IsNullOrWhiteSpace($researchPassword)) {
    $args += @("--research-password", $researchPassword)
}

Write-Host "Running: $pythonExe $($args -join ' ')"
& $pythonExe @args
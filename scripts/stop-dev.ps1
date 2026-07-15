$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$candidateIds = @()

foreach ($port in 8000, 5173) {
    $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($listener in $listeners) {
        $candidateIds += $listener.OwningProcess
    }
}

$workerProcesses = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and $_.CommandLine.Contains("app.workers.jobs")
}
$candidateIds += $workerProcesses.ProcessId

$candidateIds | Sort-Object -Unique | ForEach-Object {
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $_"
    if (-not $processInfo) {
        return
    }
    $commandLine = [string]$processInfo.CommandLine
    if ($commandLine.IndexOf($root, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
        Write-Warning "Skip PID $_ because it is outside $root"
        return
    }
    Write-Host ("Stopping PID {0}: {1}" -f $_, $processInfo.Name)
    Stop-Process -Id $_ -Force
}

Write-Host "Listen Book development services stopped."

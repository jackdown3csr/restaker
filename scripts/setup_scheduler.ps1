param (
    [string]$PythonPath,
    [string]$ScriptPath,
    [string]$WorkingDir,
    [string]$TaskName = "Galactica Auto-Restake",
    [int]$RepeatHours = 24,
    [string]$StartTime = "00:00"
)

[Version]$script:MinimumPythonVersion = [Version]"3.10.0"

function Resolve-PathOrThrow {
    param([string]$Path, [string]$Message)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw $Message
    }
    $expanded = [Environment]::ExpandEnvironmentVariables($Path)
    try {
        $fullPath = [System.IO.Path]::GetFullPath($expanded)
    }
    catch {
        throw "$Message`nUnable to resolve path: $expanded"
    }
    if (-not (Test-Path $fullPath)) {
        throw "$Message`nResolved path: $fullPath"
    }
    return $fullPath
}

function Get-CommandExecutablePath {
    param([string]$CommandName)
    $command = Get-Command $CommandName -ErrorAction SilentlyContinue
    if (-not $command) {
        return $null
    }
    if ($command.Source) {
        return $command.Source
    }
    if ($command.Path) {
        return $command.Path
    }
    return $command.Definition
}

function Get-PythonVersion {
    param([string]$Executable)
    try {
        $rawVersion = (& $Executable -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null).Trim()
        if ([string]::IsNullOrWhiteSpace($rawVersion)) {
            return $null
        }
        return [Version]$rawVersion
    }
    catch {
        return $null
    }
}

function Find-PythonInterpreter {
    param([string]$ExplicitPath)

    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        $candidates += $ExplicitPath
    }

    $repoRoot = Split-Path $PSScriptRoot -Parent
    $venvPython = Join-Path $repoRoot ".venv\\Scripts\\python.exe"
    $candidates += $venvPython

    foreach ($name in @('python.exe', 'python', 'python3.exe', 'python3')) {
        $commandPath = Get-CommandExecutablePath -CommandName $name
        if ($commandPath) {
            $candidates += $commandPath
        }
    }

    $pyLauncher = Get-CommandExecutablePath -CommandName 'py.exe'
    if ($pyLauncher) {
        try {
            $resolvedPy = (& $pyLauncher -3.10 -c "import sys; print(sys.executable)" 2>$null).Trim()
            if ($resolvedPy) {
                $candidates += $resolvedPy
            }
        }
        catch {
            # ignore launcher probe failures
        }
        $candidates += $pyLauncher
    }

    foreach ($candidate in ($candidates | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)) {
        $resolvedCandidate = Resolve-Path $candidate -ErrorAction SilentlyContinue
        if (-not $resolvedCandidate) {
            continue
        }
        $executable = $resolvedCandidate.ProviderPath
        $version = Get-PythonVersion -Executable $executable
        if (-not $version) {
            continue
        }
        if ($version -lt $script:MinimumPythonVersion) {
            Write-Host "Skipping $executable (Python $version is below required $script:MinimumPythonVersion)." -ForegroundColor Yellow
            continue
        }
        return [PSCustomObject]@{ Path = $executable; Version = $version }
    }

    throw "Unable to locate a Python interpreter that meets the minimum version requirement ($script:MinimumPythonVersion). Provide -PythonPath explicitly."
}

try {
    $pythonInfo = Find-PythonInterpreter -ExplicitPath $PythonPath
    $python = $pythonInfo.Path

    if ([string]::IsNullOrWhiteSpace($ScriptPath)) {
        $ScriptPath = Join-Path (Split-Path $PSScriptRoot -Parent) "restake.py"
    }
    $script = Resolve-PathOrThrow -Path $ScriptPath -Message "restake.py path is required."

    if ([string]::IsNullOrWhiteSpace($WorkingDir)) {
        $WorkingDir = Split-Path $script -Parent
    }
    $working = Resolve-PathOrThrow -Path $WorkingDir -Message "Working directory is required."
}
catch {
    Write-Error $_
    exit 1
}

if ($RepeatHours -le 0) {
    Write-Error "RepeatHours must be a positive integer."
    exit 1
}

$quotedScript = "`"$script`""
$taskAction = New-ScheduledTaskAction -Execute $python -Argument $quotedScript -WorkingDirectory $working

[DateTime]$parsedStart = Get-Date "00:00"
if (-not [DateTime]::TryParseExact($StartTime, "HH:mm", [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::None, [ref]$parsedStart)) {
    Write-Host "Invalid StartTime provided, defaulting to 00:00" -ForegroundColor Yellow
    $StartTime = "00:00"
}
else {
    $StartTime = $parsedStart.ToString("HH:mm")
}

$trigger = if ($RepeatHours -lt 24) {
    $interval = New-TimeSpan -Hours $RepeatHours
    $duration = New-TimeSpan -Days 1
    New-ScheduledTaskTrigger -Daily -At $parsedStart -RepetitionInterval $interval -RepetitionDuration $duration
}
else {
    New-ScheduledTaskTrigger -Daily -At $parsedStart
}

try {
    Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger $trigger -RunLevel Highest -Force -ErrorAction Stop | Out-Null
    Write-Host "Scheduled task '$TaskName' created/updated successfully." -ForegroundColor Green
    Write-Host "Using Python $($pythonInfo.Version) at $python" -ForegroundColor Cyan
    Write-Host "Runs every $RepeatHours hour(s) starting at $StartTime." -ForegroundColor Green
}
catch {
    Write-Error "Failed to register scheduled task: $_"
    exit 1
}

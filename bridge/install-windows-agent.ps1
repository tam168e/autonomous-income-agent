# Masoud Windows Bridge installer
# Uses a dedicated Git worktree so the normal project checkout is not switched.
# Run once from an elevated PowerShell window.

$ErrorActionPreference = "Stop"

$Repo = "C:\ai\AutonomousIncomeAgent_GitHub"
$Branch = "windows-bridge"
$BridgeWorktree = "C:\AI_WindowsBridge"
$LocalDir = Join-Path $env:LOCALAPPDATA "MasoudWindowsBridge"
$ConfigPath = Join-Path $LocalDir "config.json"
$ArmedPath = Join-Path $LocalDir "ARMED"
$Python = (Get-Command python -ErrorAction Stop).Source
$Agent = Join-Path $BridgeWorktree "bridge\windows_agent.py"

if (-not (Test-Path (Join-Path $Repo ".git"))) {
    throw "Git repository not found: $Repo"
}

New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null

Push-Location $Repo
try {
    git fetch origin $Branch
    if (Test-Path (Join-Path $BridgeWorktree ".git")) {
        Push-Location $BridgeWorktree
        try {
            git pull --ff-only origin $Branch
        } finally {
            Pop-Location
        }
    } else {
        git show-ref --verify --quiet ("refs/heads/" + $Branch)
        if ($LASTEXITCODE -eq 0) {
            git worktree add $BridgeWorktree $Branch
        } else {
            git worktree add --track -b $Branch $BridgeWorktree ("origin/" + $Branch)
        }
    }
} finally {
    Pop-Location
}

$config = @{
    branch = $Branch
    poll_seconds = 5
    repo_path = $Repo
    bridge_repo_path = $BridgeWorktree
    allowed_roots = @("C:\AI_System", $Repo)
    allowed_executables = @(
        "git","git.exe",
        "python","python.exe","py","py.exe",
        "node","node.exe",
        "npm","npm.cmd","npm.exe",
        "npx","npx.cmd","npx.exe",
        "bun","bun.exe","bunx","bunx.exe",
        "adb","adb.exe",
        "gradle","gradle.bat","gradle.exe"
    )
    armed_file = $ArmedPath
    max_run_seconds = 300
}
$config | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $ConfigPath
"ARMED" | Set-Content -Encoding ASCII $ArmedPath

& $Python -m py_compile $Agent
if ($LASTEXITCODE -ne 0) { throw "Python syntax check failed." }

$TaskName = "Masoud Windows Bridge"
$Pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $Pythonw) { $Pythonw = $Python }

$Action = New-ScheduledTaskAction -Execute $Pythonw -Argument ('"' + $Agent + '"') -WorkingDirectory $BridgeWorktree
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId ($env:USERDOMAIN + "\" + $env:USERNAME) -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Days 7)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null

Write-Host ""
Write-Host "Masoud Windows Bridge installed."
Write-Host "Workspace:    $Repo"
Write-Host "Bridge tree:  $BridgeWorktree"
Write-Host "Branch:       $Branch"
Write-Host "Config:       $ConfigPath"
Write-Host "Armed switch: $ArmedPath"
Write-Host ""
Write-Host "Your normal checkout is not switched."
Write-Host "Emergency stop: delete the ARMED file, or change its content so it is not exactly ARMED."
Write-Host 'Start now: Start-ScheduledTask -TaskName "Masoud Windows Bridge"'

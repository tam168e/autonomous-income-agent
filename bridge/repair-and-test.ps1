# Masoud Windows Bridge - repair and test
$ErrorActionPreference = "Continue"

$TaskName = "Masoud Windows Bridge"
$BridgeTree = "C:\AI_WindowsBridge"
$Agent = "$BridgeTree\bridge\windows_agent.py"
$Inbox = "$BridgeTree\bridge\inbox"
$Outbox = "$BridgeTree\bridge\outbox"
$LocalDir = "$env:LOCALAPPDATA\MasoudWindowsBridge"
$Config = "$LocalDir\config.json"
$Armed = "$LocalDir\ARMED"
$StdOut = "$LocalDir\worker-test.stdout.log"
$StdErr = "$LocalDir\worker-test.stderr.log"
$Bootstrap = "$Outbox\bootstrap-ping-001.json"

Write-Host ""
Write-Host "=== MASOUD WINDOWS BRIDGE REPAIR ==="
Write-Host ""
New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null
New-Item -ItemType Directory -Force -Path $Inbox,$Outbox | Out-Null

$Python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
$Git = (Get-Command git.exe -ErrorAction SilentlyContinue).Source
if (-not $Python) { Write-Host "ERROR: python.exe not found"; exit 2 }
if (-not $Git) { Write-Host "ERROR: git.exe not found"; exit 2 }
if (-not (Test-Path $Agent)) { Write-Host "ERROR: worker not found"; exit 2 }
if (-not (Test-Path $Config)) { Write-Host "ERROR: config not found"; exit 2 }
if (-not (Test-Path $Armed)) { Write-Host "ERROR: ARMED switch not found"; exit 2 }

Write-Host "Python: $Python"
& $Python --version

Write-Host "Updating bridge worktree..."
Push-Location $BridgeTree
try { & $Git pull --ff-only origin windows-bridge; if ($LASTEXITCODE -ne 0) { throw "git pull failed" }; Write-Host "Branch:"; & $Git branch --show-current; Write-Host "Syntax check:"; & $Python -m py_compile $Agent; if ($LASTEXITCODE -ne 0) { throw "worker syntax check failed" } }
catch { Write-Host "ERROR: $($_.Exception.Message)"; Pop-Location; exit 3 }
Pop-Location

Write-Host "Stopping old scheduled task..."
Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "Manual worker test (12 seconds)..."
Remove-Item $StdOut,$StdErr -Force -ErrorAction SilentlyContinue
$proc = $null
try {
  $proc = Start-Process -FilePath $Python -ArgumentList @("-u",$Agent) -WorkingDirectory $BridgeTree -RedirectStandardOutput $StdOut -RedirectStandardError $StdErr -PassThru -WindowStyle Hidden
  Write-Host "PID: $($proc.Id)"
  Start-Sleep -Seconds 12
  $alive = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
  if ($alive) { Write-Host "MANUAL_WORKER=RUNNING"; Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } else { Write-Host "MANUAL_WORKER=EXITED" }
} catch { Write-Host "ERROR: manual worker start failed: $($_.Exception.Message)" }

Write-Host "--- STDOUT ---"
if (Test-Path $StdOut) { Get-Content $StdOut -Raw } else { Write-Host "(none)" }
Write-Host "--- STDERR ---"
if (Test-Path $StdErr) { Get-Content $StdErr -Raw } else { Write-Host "(none)" }

Write-Host "Checking bootstrap..."
if (Test-Path $Bootstrap) { Write-Host "BOOTSTRAP=SUCCESS"; Get-Content $Bootstrap -Raw } else { Write-Host "BOOTSTRAP=NOT_FOUND" }

Write-Host "Rebuilding scheduled task..."
try {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  $CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
  $Action = New-ScheduledTaskAction -Execute $Python -Argument ("-u `"$Agent`"") -WorkingDirectory $BridgeTree
  $Trigger = New-ScheduledTaskTrigger -AtLogOn
  $Principal = New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType Interactive -RunLevel Limited
  $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null
  Start-ScheduledTask -TaskName $TaskName
  Start-Sleep -Seconds 10
  $TaskInfo = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
  $FinalTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  Write-Host "TASK_STATE=$($FinalTask.State)"
  Write-Host "TASK_LAST_RESULT=$($TaskInfo.LastTaskResult)"
  $bridgePython = Get-Process python,pythonw -ErrorAction SilentlyContinue
  if ($bridgePython) { Write-Host "PYTHON_PROCESS=YES"; $bridgePython | Select-Object Id,ProcessName,Path | Format-Table -AutoSize } else { Write-Host "PYTHON_PROCESS=NO" }
} catch { Write-Host "TASK_REPAIR_ERROR=$($_.Exception.Message)" }

Write-Host "Final outbox:"
Get-ChildItem $Outbox -Force -ErrorAction SilentlyContinue | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize
Write-Host ""
if (Test-Path $Bootstrap) { Write-Host "=== BRIDGE COMMUNICATION: SUCCESS ===" } else { Write-Host "=== BRIDGE COMMUNICATION: NOT YET CONFIRMED ===" }
Write-Host "=== FINISHED ==="
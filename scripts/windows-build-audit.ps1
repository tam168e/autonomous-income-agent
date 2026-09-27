# Autonomous Income Agent - Windows build and runtime audit
$ErrorActionPreference = "Continue"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Report = Join-Path $Root "windows-build-audit.txt"
$Lines = @()

function Add($s) { $Lines += [string]$s; Write-Host $s }

Add "=== AUTONOMOUS INCOME AGENT WINDOWS AUDIT ==="
Add ("DATE=" + (Get-Date -Format o))
Add ("ROOT=" + $Root)
Add ""

Add "=== TOOLS ==="
$java = Get-Command java.exe -ErrorAction SilentlyContinue
$gradle = Get-Command gradle.exe -ErrorAction SilentlyContinue
$adb = Get-Command adb.exe -ErrorAction SilentlyContinue
$python = Get-Command python.exe -ErrorAction SilentlyContinue

Add ("JAVA=" + [bool]$java + " PATH=" + $(if($java){$java.Source}else{"N/A"}))
if($java){ & $java.Source -version 2>&1 | ForEach-Object { Add $_ } }

Add ("GRADLE=" + [bool]$gradle + " PATH=" + $(if($gradle){$gradle.Source}else{"N/A"}))
if($gradle){ & $gradle.Source --version 2>&1 | ForEach-Object { Add $_ } }

Add ("ADB=" + [bool]$adb + " PATH=" + $(if($adb){$adb.Source}else{"N/A"}))
if($adb){ & $adb.Source version 2>&1 | ForEach-Object { Add $_ } }

Add ("PYTHON=" + [bool]$python + " PATH=" + $(if($python){$python.Source}else{"N/A"}))
if($python){ & $python.Source --version | ForEach-Object { Add $_ } }

Add ""
Add "=== ANDROID PROJECT ==="
if(Test-Path (Join-Path $Root "settings.gradle.kts")){
    Push-Location $Root
    try {
        Add ("BRANCH=" + (git branch --show-current))
        Add ("STATUS=" + (git status --short --branch))
        Add ("GRADLE_FILES_PRESENT=" + (Test-Path "gradle"))
        Add ("APP_DIR_PRESENT=" + (Test-Path "app"))
        Add ("WRAPPER_BAT=" + (Test-Path "gradlew.bat"))
        Add ("WRAPPER_JAR=" + (Test-Path "gradle\wrapper\gradle-wrapper.jar"))
    } finally { Pop-Location }
} else {
    Add "ANDROID_ROOT_NOT_FOUND"
}

Add ""
Add "=== ANDROID SDK ==="
$SdkCandidates = @(
    $env:ANDROID_HOME,
    $env:ANDROID_SDK_ROOT,
    "$env:LOCALAPPDATA\Android\Sdk"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

if($SdkCandidates.Count -gt 0){
    foreach($sdk in $SdkCandidates){ Add ("SDK=" + $sdk) }
} else {
    Add "SDK_NOT_FOUND"
}

Add ""
Add "=== BUILD ATTEMPT ==="
if((Test-Path (Join-Path $Root "gradlew.bat")) -and (Test-Path (Join-Path $Root "settings.gradle.kts"))){
    Push-Location $Root
    try {
        & .\gradlew.bat --no-daemon :app:assembleDebug 2>&1 | ForEach-Object { Add $_ }
        Add ("GRADLEW_EXIT=" + $LASTEXITCODE)
    } finally { Pop-Location }
} elseif($gradle -and (Test-Path (Join-Path $Root "settings.gradle.kts"))){
    Push-Location $Root
    try {
        & $gradle.Source --no-daemon :app:assembleDebug 2>&1 | ForEach-Object { Add $_ }
        Add ("GRADLE_EXIT=" + $LASTEXITCODE)
    } finally { Pop-Location }
} else {
    Add "BUILD_SKIPPED_WRAPPER_OR_GRADLE_OR_PROJECT_MISSING"
}

Add ""
Add "=== BACKEND ==="
if(Test-Path (Join-Path $Root "backend\requirements.txt")){
    Add "BACKEND_REQUIREMENTS_PRESENT=TRUE"
    Add ("BACKEND_MAIN_PRESENT=" + (Test-Path (Join-Path $Root "backend\app\main.py")))
} else {
    Add "BACKEND_NOT_FOUND"
}

Add ""
Add "=== FINAL ==="
$Lines | Set-Content -Path $Report -Encoding UTF8
Add ("REPORT=" + $Report)
Add "=== DONE ==="

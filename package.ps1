$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $projectRoot
try {
    $executablePath = Join-Path $projectRoot "dist\DungeonAndBardGame.exe"
    $runningGame = Get-CimInstance Win32_Process -Filter "Name = 'DungeonAndBardGame.exe'" |
        Where-Object { $_.ExecutablePath -eq $executablePath }
    if ($runningGame) {
        throw "Chiudi Dungeon & Bard prima di creare il pacchetto: l'eseguibile è ancora in uso."
    }

    & "$projectRoot\build.ps1"
    if ($LASTEXITCODE -ne 0) {
        throw "La creazione dell'eseguibile non è riuscita."
    }

    $compilerPath = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
    if (-not $compilerPath) {
        $candidates = @(
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
            "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
        )
        foreach ($candidate in $candidates) {
            if (Test-Path -LiteralPath $candidate) {
                $compilerPath = $candidate
                break
            }
        }
    }
    if (-not $compilerPath) {
        throw "Inno Setup 6 non è installato. Installalo con winget e rilancia package.ps1."
    }

    & $compilerPath "$projectRoot\installer.iss"
    if ($LASTEXITCODE -ne 0) {
        throw "La creazione dell'installer non è riuscita."
    }

    $installer = Join-Path $projectRoot "dist\DungeonAndBardSetup.exe"
    if (-not (Test-Path -LiteralPath $installer)) {
        throw "Inno Setup non ha prodotto l'installer atteso: $installer"
    }
    Write-Output "Installer creato: $installer"
}
finally {
    Pop-Location
}

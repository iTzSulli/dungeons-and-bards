$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $projectRoot
try {
    python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name DungeonAndBardGame `
        --distpath "$projectRoot\dist" `
        --workpath "$env:TEMP\DungeonAndBard-build" `
        --specpath "$env:TEMP\DungeonAndBard-spec" `
        --collect-all pygame `
        "$projectRoot\game.py"

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller non è riuscito a creare l'eseguibile."
    }

    Write-Output "Videogioco creato: $projectRoot\dist\DungeonAndBardGame.exe"
}
finally {
    Pop-Location
}

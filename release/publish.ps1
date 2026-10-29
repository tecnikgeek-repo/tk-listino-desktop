# Pubblica una versione di tk-listino per Windows, Mac e Linux: gli utenti la ricevono con l'aggiornamento automatico.
# Uso:  powershell -ExecutionPolicy Bypass -File release\publish.ps1 -Notes "Novità 1|Novità 2"
# Prima: VERSION alzata in tklistino\__init__.py e commit fatto (lo script fa push e attende le build Mac e Linux su GitHub).
# -SoloWindows: pubblica solo Windows (manifest senza chiavi mac/linux) quando le build su GitHub non possono partire
#   (quota Actions finita); Mac e Linux restano sull'ultima versione, le cartelle Mac\ e Linux\ di Dropbox non si toccano.
param(
    [Parameter(Mandatory = $true)][string]$Notes,
    [switch]$SoloWindows
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

$noteList = @($Notes -split '\|' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$version = (Select-String -Path 'tklistino\__init__.py' -Pattern 'VERSION = "(.+)"').Matches[0].Groups[1].Value
$repo = 'tecnikgeek-repo/tk-listino-desktop'
$sshConfig = "$env:USERPROFILE\Dropbox\CLAUDE\fleet\ssh-config"
$remoteDir = 'public_html/updates/tk-listino'
$baseUrl = 'https://pietrodefilippis.it/updates/tk-listino'
$dropbox = "$env:USERPROFILE\Dropbox\CLAUDE\tk-software\tk-listino"
Write-Host "== Pubblicazione tk-listino $version (Windows + Mac + Linux)"

# --- la versione non deve essere già pubblicata
try {
    $current = Invoke-RestMethod "https://pietrodefilippis.it/updates/tk-listino.json?t=$([DateTime]::Now.Ticks)" -TimeoutSec 15
    if ([version]$current.version -ge [version]$version) {
        throw "Sul server c'è già la versione $($current.version): alza VERSION in tklistino\__init__.py"
    }
} catch [System.Net.WebException] { Write-Host "   nessun manifest precedente" }

# --- Windows
$winZip = "dist\tk-listino-$version-windows.zip"
$winPortable = "dist\tk-listino-$version-portatile.zip"
if (-not (Test-Path $winZip) -or -not (Test-Path $winPortable)) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File installer\build.ps1
    if ($LASTEXITCODE -ne 0) { throw 'Build Windows fallita' }
}
$assets = @(@{ key = 'windows-zip'; file = (Resolve-Path $winZip).Path })
# installazione .exe: e' il download «Windows» della vetrina (pietrodefilippis.it/scarica-programma/...)
$setupWin = "dist\tk-listino-setup-$version.exe"
if (-not (Test-Path $setupWin)) { throw "Manca l'installazione ${setupWin}: rifai installer\build.ps1" }
$assets += @{ key = 'windows'; file = (Resolve-Path $setupWin).Path }

# --- Mac e Linux: build su GitHub del commit corrente, dmg e AppImage presi dalla release v<versione>
if (git status --porcelain --untracked-files=no) { throw 'Ci sono modifiche non committate: fai commit prima di pubblicare' }
git push -q
if ($LASTEXITCODE -ne 0) { throw 'git push non riuscito' }
# tag della versione: è il link «codice sorgente» del programma (URL_SORGENTE = .../tree/v<versione>)
git rev-parse -q --verify "refs/tags/v$version" | Out-Null
if ($LASTEXITCODE -ne 0) {
    git tag "v$version"
    if ($LASTEXITCODE -ne 0) { throw "git tag v$version non riuscito" }
}
git push -q origin "v$version"
if ($LASTEXITCODE -ne 0) { throw "git push del tag v$version non riuscito" }
if (-not $SoloWindows) {
# le build Mac e Linux non partono più da sole a ogni push: le avvio io, in parallelo, sul commit appena inviato
$sha = (git rev-parse HEAD).Trim()
foreach ($wf in 'build-mac.yml', 'build-linux.yml') {
    gh workflow run $wf --repo $repo --ref main
    if ($LASTEXITCODE -ne 0) { throw "Avvio di $wf su GitHub non riuscito" }
}
Start-Sleep -Seconds 5
$runs = @{}
foreach ($wf in 'build-mac.yml', 'build-linux.yml') {
    $runId = $null
    for ($i = 0; $i -lt 30 -and -not $runId; $i++) {
        $runId = gh run list --repo $repo --workflow $wf --commit $sha --json databaseId --jq '.[0].databaseId'
        if (-not $runId) { Start-Sleep -Seconds 5 }
    }
    if (-not $runId) { throw "$wf non trovata su GitHub" }
    $runs[$wf] = $runId
}
Write-Host "   attendo le build macOS e Linux del commit $($sha.Substring(0,7))…"
foreach ($wf in $runs.Keys) {
    gh run watch $runs[$wf] --repo $repo --exit-status | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "$wf fallita: https://github.com/$repo/actions/runs/$($runs[$wf])" }
}
$macDir = "dist\mac-$version"
if (Test-Path $macDir) { Remove-Item -LiteralPath $macDir -Recurse -Force }
New-Item -ItemType Directory -Force $macDir | Out-Null
gh release download "v$version" --repo $repo --dir $macDir --pattern '*.dmg'
if ($LASTEXITCODE -ne 0) { throw "Download dei dmg dalla release v$version fallito" }
foreach ($arch in 'arm64', 'x86_64') {
    $dmg = Join-Path $macDir "tk-listino-$version-mac-$arch.dmg"
    if (-not (Test-Path $dmg)) { throw "Manca il dmg $arch" }
    $assets += @{ key = "mac-$arch"; file = (Resolve-Path $dmg).Path }
}
gh release download "v$version" --repo $repo --dir $macDir --pattern '*.AppImage' --clobber
if ($LASTEXITCODE -ne 0) { throw "Download dell'AppImage dalla release v$version fallito" }
$appImage = Join-Path $macDir "tk-listino-$version-linux-x86_64.AppImage"
if (-not (Test-Path $appImage)) { throw "Manca l'AppImage Linux" }
$assets += @{ key = 'linux-x86_64'; file = (Resolve-Path $appImage).Path }
}

# --- manifest
$manifest = [ordered]@{ name = 'tk-listino'; version = $version; date = (Get-Date -Format 'dd/MM/yyyy'); notes = [Collections.ArrayList]$noteList }  # ArrayList: resta una lista anche con una nota sola
foreach ($a in $assets) {
    $name = Split-Path $a.file -Leaf
    $manifest[$a.key] = [ordered]@{
        url    = "$baseUrl/$name"
        sha256 = (Get-FileHash $a.file -Algorithm SHA256).Hash.ToLower()
        size   = (Get-Item $a.file).Length
    }
}
$manifestFile = Join-Path $env:TEMP 'tk-listino.json'
[IO.File]::WriteAllText($manifestFile, ($manifest | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding($false)))
# firma del manifest (Ed25519), dopo l'ultima modifica: il programma installa solo pacchetti firmati.
# Lo slug è il nome del file del manifest (tk-listino.json → tk-listino), lo stesso di updater.SLUG
python -I "C:\Users\TecnikGeek\Dropbox\CLAUDE\tk-software\librerie\firma_aggiornamenti.py" firma --slug tk-listino $manifestFile
if ($LASTEXITCODE -ne 0) { throw 'Firma del manifest non riuscita: niente pubblicazione' }

# --- upload: prima i file, per ultimo il manifest
Write-Host "   caricamento sul server…"
ssh -F $sshConfig pietrodefilippis "mkdir -p ~/$remoteDir/old"
foreach ($a in $assets) {
    scp -q -F $sshConfig $a.file "pietrodefilippis:~/$remoteDir/"
    if ($LASTEXITCODE -ne 0) { throw "Upload fallito: $($a.file)" }
}
scp -q -F $sshConfig $manifestFile "pietrodefilippis:~/public_html/updates/tk-listino.json.new"
$names = ($assets | ForEach-Object { Split-Path $_.file -Leaf }) -join ' '
$remote = @'
cd ~/__DIR__ && rm -f old/* && for f in tk-listino-*; do keep=0; for k in __NAMES__; do [ "$f" = "$k" ] && keep=1; done; [ $keep = 1 ] || mv -f "$f" old/; done && mv -f ~/public_html/updates/tk-listino.json.new ~/public_html/updates/tk-listino.json && ls ~/__DIR__
'@
$remote = $remote.Replace('__DIR__', $remoteDir).Replace('__NAMES__', $names).Trim()
ssh -F $sshConfig pietrodefilippis $remote
if ($LASTEXITCODE -ne 0) { throw 'Attivazione del manifest sul server fallita' }

# --- verifica pubblica
$check = Invoke-RestMethod "https://pietrodefilippis.it/updates/tk-listino.json?t=$([DateTime]::Now.Ticks)" -TimeoutSec 15
if ($check.version -ne $version) { throw "Il manifest pubblico non mostra $version" }
foreach ($a in $assets) {
    $url = $manifest[$a.key].url
    $resp = Invoke-WebRequest $url -Method Head -UseBasicParsing -TimeoutSec 30
    if ([int64]$resp.Headers['Content-Length'] -ne $manifest[$a.key].size) { throw "Dimensione errata online: $url" }
}
Write-Host "   manifest e file online verificati"

# --- cartella Dropbox: Windows (ZIP portatile), Mac (dmg) e Linux (AppImage), solo l'ultima versione
New-Item -ItemType Directory -Force "$dropbox\Windows", "$dropbox\Mac", "$dropbox\Linux" | Out-Null
Get-ChildItem $dropbox -File -Filter 'tk-listino-*' | Remove-Item -Force
$clean = if ($SoloWindows) { @("$dropbox\Windows") } else { @("$dropbox\Windows", "$dropbox\Mac", "$dropbox\Linux") }
Get-ChildItem $clean -File | Where-Object { $_.Name -notlike "*$version*" } | Remove-Item -Force
Copy-Item $winPortable "$dropbox\Windows\" -Force
$setupExe = "dist\tk-listino-setup-$version.exe"
if (Test-Path $setupExe) { Copy-Item $setupExe "$dropbox\Windows\" -Force }
foreach ($a in $assets | Where-Object { $_.key -like 'mac-*' }) { Copy-Item $a.file "$dropbox\Mac\" -Force }
foreach ($a in $assets | Where-Object { $_.key -like 'linux-*' }) { Copy-Item $a.file "$dropbox\Linux\" -Force }
& robocopy $root "$dropbox\progetto" /MIR /NFL /NDL /NJH /NJS /NP /XD .venv .venv-mac .venv-linux build dist __pycache__ .git Listini licenze-pacchetto /XF *.pyc | Out-Null

if ($SoloWindows) { Write-Host "== tk-listino $version pubblicato SOLO per Windows (Mac e Linux in sospeso)." }
else { Write-Host "== tk-listino $version pubblicato per Windows, Mac e Linux." }

# Crea dist\tk-listino-<ver>-windows.zip (aggiornamento) e dist\tk-listino-<ver>-portatile.zip (cartella da pennetta)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$version = (Select-String -Path 'tklistino\__init__.py' -Pattern 'VERSION = "(.+)"').Matches[0].Groups[1].Value
$stageRoot = Join-Path $env:TEMP 'tklistino-stage'
$stage = Join-Path $stageRoot 'app'
$dist = Join-Path $root 'dist'
# venv del repo (requirements.txt): PySide6, certifi, pypdfium2. Crearlo con
#   uv venv --python 3.13 .venv ; uv pip install --python .venv\Scripts\python.exe -r requirements.txt
$venv = Join-Path $root '.venv'
if (-not (Test-Path "$venv\Lib\site-packages\pypdfium2")) { throw "Manca il venv con le dipendenze ($venv): vedi requirements.txt" }
Write-Host "== tk-listino ${version}"
if (Test-Path $stageRoot) { Remove-Item $stageRoot -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null
New-Item -ItemType Directory -Force $dist | Out-Null

function Robo($src, $dst, [string[]]$extra) {
    & robocopy $src $dst /E /NFL /NDL /NJH /NJS /NP @extra | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy fallito ($LASTEXITCODE): $src" }
}

$homeLine = Get-Content "$venv\pyvenv.cfg" | Where-Object { $_ -match '^home\s*=' }
$pyHome = ($homeLine -replace '^home\s*=\s*', '').Trim()
$py = Join-Path $stage 'python'
Robo $pyHome $py @('/XD', 'test', 'tests', 'idlelib', 'tkinter', 'turtledemo', 'tcl', 'include', 'libs', 'Scripts',
                   'ensurepip', 'lib2to3', 'site-packages', '__phello__', 'pydoc_data',
                   '/XF', '*.pdb', '_tkinter.pyd', 'tcl*.dll', 'tk*.dll', 'EXTERNALLY-MANAGED')

$sp = "$venv\Lib\site-packages"
$dsp = Join-Path $py 'Lib\site-packages'
New-Item -ItemType Directory -Force $dsp | Out-Null
Robo "$sp\shiboken6" "$dsp\shiboken6" @()
Robo "$sp\certifi" "$dsp\certifi" @()
# PDF: pypdfium2 (Apache-2.0/BSD-3-Clause) con pdfium.dll; il programma a riga di comando (pypdfium2_cli) non serve
foreach ($pkg in @('pypdfium2', 'pypdfium2_raw', 'pypdfium2_cfg')) { Robo "$sp\$pkg" "$dsp\$pkg" @('/XD', '__pycache__') }
Get-ChildItem $sp -Directory -Filter 'pypdfium2-*.dist-info' | ForEach-Object { Robo $_.FullName "$dsp\$($_.Name)" @() }
$ps = "$sp\PySide6"
$dps = "$dsp\PySide6"
New-Item -ItemType Directory -Force $dps | Out-Null
$files = @('pyside6.abi3.dll', 'QtCore.pyd', 'QtGui.pyd', 'QtWidgets.pyd', 'QtPrintSupport.pyd',
           'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll', 'Qt6PrintSupport.dll', 'Qt6Svg.dll')
Get-ChildItem $ps -File | Where-Object {
    $_.Extension -eq '.py' -or $files -contains $_.Name -or $_.Name -match '^(msvcp140|vcruntime140|concrt140)'
} | ForEach-Object { Copy-Item $_.FullName $dps }
foreach ($plug in @('platforms\qwindows.dll', 'styles\qmodernwindowsstyle.dll', 'iconengines\qsvgicon.dll',
                    'imageformats\qjpeg.dll', 'imageformats\qgif.dll', 'imageformats\qico.dll',
                    'imageformats\qsvg.dll', 'imageformats\qwebp.dll', 'imageformats\qtiff.dll')) {
    $srcp = Join-Path "$ps\plugins" $plug
    if (Test-Path $srcp) {
        $dstp = Join-Path "$dps\plugins" $plug
        New-Item -ItemType Directory -Force (Split-Path $dstp) | Out-Null
        Copy-Item $srcp $dstp
    }
}
New-Item -ItemType Directory -Force "$dps\translations" | Out-Null
Copy-Item "$ps\translations\qtbase_it.qm" "$dps\translations\" -ErrorAction SilentlyContinue

Robo 'tklistino' "$stage\tklistino" @('/XD', '__pycache__')
Robo 'assets' "$stage\assets" @()
Copy-Item 'run.py' $stage
# .cmd di avvio della cartella portatile: viaggia anche dentro «app», così il programma lo rinnova dopo gli aggiornamenti
$cmdText = (Get-Content "$PSScriptRoot\Avvia tk-listino.cmd" -Raw) -replace "`r?`n", "`r`n"
[IO.File]::WriteAllText("$stage\assets\avvia.cmd", $cmdText, [Text.Encoding]::ASCII)
# testi delle licenze (AGPL + componenti inclusi, dai *.dist-info) e COMPONENTI.txt, accanto a run.py
# Python di base + librerie del venv: Smart App Control blocca .venv\Scripts\python.exe (lanciatore non firmato)
$env:PYTHONPATH = (Join-Path $venv 'Lib\site-packages')
& "$pyHome\python.exe" "$root\tools_licenze.py" "$stage\licenze" $sp
Remove-Item Env:PYTHONPATH
if ($LASTEXITCODE -ne 0) { throw 'Preparazione delle licenze fallita' }
if (Test-Path "$pyHome\LICENSE.txt") { Copy-Item "$pyHome\LICENSE.txt" "$stage\licenze\Python-LICENSE.txt" }
& "$py\python.exe" -m compileall -q "$py\Lib" 2>$null | Out-Null
# il codice di tk-listino va nel pacchetto SOLO compilato: .pyc accanto ai moduli (-b), sorgenti tolti
& "$py\python.exe" -m compileall -q -b "$stage\tklistino" 2>$null | Out-Null
Get-ChildItem "$stage\tklistino" -Recurse -File -Filter '*.py' | Remove-Item -Force
Get-ChildItem "$stage\tklistino" -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force
if (Get-ChildItem "$stage\tklistino" -Recurse -File -Filter '*.py') { throw 'Nel pacchetto sono rimasti dei sorgenti .py' }
Remove-Item "$py\python.exe"

# verifica: avvio reale dal runtime ridotto (finestra + PDF)
$shot = Join-Path $stageRoot 'selftest.png'
$p = Start-Process "$py\pythonw.exe" -ArgumentList "`"$stage\run.py`"", '--selftest', "`"$shot`"" -PassThru
if (-not $p.WaitForExit(60000)) { Stop-Process -Id $p.Id -Force; throw 'Selftest in timeout' }
if (-not (Test-Path $shot) -or -not (Test-Path "$stageRoot\selftest.pdf")) { throw 'Selftest fallito: il runtime ridotto non avvia tk-listino' }
Remove-Item $shot, "$stageRoot\selftest.pdf"
# verifica: importazione da PDF dal runtime ridotto (pypdfium2: testo con le posizioni)
$impOut = Join-Path $stageRoot 'import.txt'
$p = Start-Process "$py\pythonw.exe" -ArgumentList "`"$stage\run.py`"", '--import-test', "`"$root\tests\prova.pdf`"", "`"$impOut`"" -PassThru
if (-not $p.WaitForExit(90000)) { Stop-Process -Id $p.Id -Force; throw 'Test importazione in timeout' }
$impText = if (Test-Path $impOut) { Get-Content $impOut -Raw -Encoding UTF8 } else { '' }
if ($impText -notmatch 'OK 3 sezioni') { throw "Test importazione PDF fallito: $impText" }
Remove-Item $impOut
Write-Host "   test importazione PDF OK ($impText)"
Write-Host "   selftest runtime OK (finestra + PDF)"
# il selftest ha creato Listini accanto a app? no: in sviluppo/stage usa APP_ROOT; pulizia
if (Test-Path "$stage\Listini") { Remove-Item "$stage\Listini" -Recurse -Force }
Get-ChildItem $stage -Recurse -Directory -Filter '__pycache__' | Where-Object { $_.FullName -like "$stage\tklistino*" } | Out-Null

$zipCode = "import os,sys,zipfile`nsrc,dst=sys.argv[1],sys.argv[2]`nwith zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:`n  for d,_,fs in os.walk(src):`n    for f in fs:`n      p=os.path.join(d,f); z.write(p, os.path.relpath(p,src).replace(os.sep,'/'))"
$updateZip = Join-Path $dist "tk-listino-$version-windows.zip"
& "$pyHome\python.exe" -c $zipCode $stage $updateZip
if ($LASTEXITCODE -ne 0) { throw 'ZIP aggiornamento fallito' }

$pack = Join-Path $stageRoot "pack\tk-listino-$version"
New-Item -ItemType Directory -Force "$pack\Listini" | Out-Null
Robo $stage "$pack\app" @()
[IO.File]::WriteAllText("$pack\Avvia tk-listino.cmd", $cmdText, [Text.Encoding]::ASCII)
$readme = Get-Content "$PSScriptRoot\Leggimi.txt" -Raw -Encoding UTF8
[IO.File]::WriteAllText("$pack\Leggimi.txt", ($readme -replace "`r?`n", "`r`n"), (New-Object Text.UTF8Encoding($true)))
$portZip = Join-Path $dist "tk-listino-$version-portatile.zip"
& "$pyHome\python.exe" -c $zipCode (Join-Path $stageRoot 'pack') $portZip
if ($LASTEXITCODE -ne 0) { throw 'ZIP portatile fallito' }
# controllo del contenuto: licenze e pypdfium2 dentro, nessuna traccia di PyMuPDF (AGPL di terzi, non più usata)
$checkCode = "import sys,zipfile`nfor zp in sys.argv[1:]:`n  n=[x.lower() for x in zipfile.ZipFile(zp).namelist()]`n  bad=[x for x in n if 'pymupdf' in x or 'fitz' in x or 'mupdf' in x]`n  need=['licenze/copying-agpl-3.0.txt','licenze/componenti.txt','pypdfium2_raw/pdfium.dll']`n  miss=[k for k in need if not any(x.endswith(k) for x in n)]`n  if bad or miss: print(zp,'VIETATI',bad[:5],'MANCANTI',miss); sys.exit(1)`nprint('contenuto ZIP OK')"
& "$pyHome\python.exe" -c $checkCode $updateZip $portZip
if ($LASTEXITCODE -ne 0) { throw 'Contenuto degli ZIP non valido' }
# --- installer exe (stesso modello di tk-pdf: setup.cs = strumenti\tk-setup.cs); contiene il pacchetto di aggiornamento
$csc = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$sizeKb = [int]((Get-ChildItem $stage -Recurse -File | Measure-Object Length -Sum).Sum / 1KB)
$map = [ordered]@{
    NAME = 'tk-listino'
    SLUG = 'tk-listino'
    TAGLINE = 'listini con foto, sezioni e prezzi in PDF o stampati'
    SUBDIR = 'app'
    DATADIR = 'Listini'
    ICON = 'tk-listino.ico'
    ACCENT = '#e11d48'
    UNINSTALL = 'cmd'
    UNINSTALLKEY = 'tk-listino'
    LNK = 'tk-listino'
    LEGACYLNK = 'tkLISTINO'
    LAUNCHSCHEMA = ''
    ITEMS = ''
    # associazione dei file .listino e «App predefinite» (vedi tklistino\winreg_assoc.py): via con la disinstallazione
    REGKEYS = 'Software\Classes\.listino;Software\Classes\TKLISTINO.Listino;Software\TecnikGeek\tk-listino;Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.listino'
    REGAPPS = 'tk-listino;tkLISTINO'
    VERSION = $version
    SIZEKB = "$sizeKb"
}
$setupSrc = Get-Content "$PSScriptRoot\setup.cs" -Raw -Encoding UTF8
foreach ($k in $map.Keys) { $setupSrc = $setupSrc.Replace("@@$k@@", [string]$map[$k]) }
$genSrc = Join-Path $stageRoot 'setup.cs'
[IO.File]::WriteAllText($genSrc, $setupSrc, (New-Object Text.UTF8Encoding($true)))
$setupExe = Join-Path $dist "tk-listino-setup-$version.exe"
& $csc /nologo /optimize+ /target:winexe /platform:anycpu /win32icon:"$root\assets\tk-listino.ico" `
    /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Core.dll `
    /reference:System.IO.Compression.dll /reference:System.IO.Compression.FileSystem.dll `
    /resource:"$updateZip",payload.zip /out:"$setupExe" $genSrc
if ($LASTEXITCODE -ne 0) { throw 'Compilazione installer fallita' }
Write-Host "   installer: $setupExe ($([math]::Round((Get-Item $setupExe).Length/1MB,1)) MB)"

$sha = (Get-FileHash $updateZip -Algorithm SHA256).Hash.ToLower()
Write-Host "== Creati:`n   $portZip ($([math]::Round((Get-Item $portZip).Length/1MB,1)) MB)`n   $updateZip`n   sha256 aggiornamento: $sha"
Remove-Item $stageRoot -Recurse -Force

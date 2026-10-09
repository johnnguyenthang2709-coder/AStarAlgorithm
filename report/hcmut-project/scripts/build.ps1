param([string]$TexBin = 'C:\Users\Thang\AppData\Local\Programs\MiKTeX\miktex\bin\x64')
$ErrorActionPreference = 'Stop'
$reportDir = Split-Path -Parent $PSScriptRoot
Push-Location $reportDir
try {
    $latexExe = Join-Path $TexBin 'pdflatex.exe'
    $bibExe = Join-Path $TexBin 'bibtex.exe'
    & $latexExe -interaction=nonstopmode -halt-on-error -jobname=report main.tex *> build-pass1.txt
    if ($LASTEXITCODE -ne 0) { throw 'First LaTeX pass failed; see build-pass1.txt' }
    & $bibExe report *> build-bibtex.txt
    if ($LASTEXITCODE -ne 0) { throw 'BibTeX failed; see build-bibtex.txt' }
    foreach ($pass in 2,3) {
        & $latexExe -interaction=nonstopmode -halt-on-error -jobname=report main.tex *> "build-pass$pass.txt"
        if ($LASTEXITCODE -ne 0) { throw "LaTeX pass $pass failed" }
    }
    if (Select-String report.log -Pattern 'Overfull|Underfull|undefined|LaTeX.*Warning|Package .* Warning|duplicate ignored' -Quiet) {
        throw 'Final typesetting warnings remain; inspect report.log'
    }
    Write-Output 'PASS: report.pdf built; no unresolved references or typesetting warnings.'
} finally { Pop-Location }

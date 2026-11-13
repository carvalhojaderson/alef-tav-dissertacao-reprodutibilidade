<#
    verificar_integridade.ps1

    Confere o snapshot publicado contra MANIFEST_SHA256.txt.

    Uso:
        powershell -ExecutionPolicy Bypass -File .\verificar_integridade.ps1
        powershell -ExecutionPolicy Bypass -File .\verificar_integridade.ps1 -Gerar

    -Gerar            regrava o manifesto a partir dos arquivos atuais
    -Caminho <dir>    raiz a verificar (padrao: pasta deste script)
    -Silencioso       mostra apenas o resumo

    Saida: 0 = integro; 1 = divergencia ou arquivo ausente.
#>
[CmdletBinding()]
param(
    [switch]$Gerar,
    [string]$Caminho,
    [switch]$Silencioso
)

$ErrorActionPreference = 'Stop'

# $PSScriptRoot nao esta disponivel como valor padrao no bloco param (PS 5.1)
if ([string]::IsNullOrWhiteSpace($Caminho)) {
    $Caminho = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
}
$Caminho = (Resolve-Path -LiteralPath $Caminho).Path.TrimEnd('\', '/')
$manifesto = Join-Path $Caminho 'MANIFEST_SHA256.txt'

# Itens que nao entram no manifesto (artefatos de execucao, VCS, o proprio manifesto)
$excluirDir = @('.git', '__pycache__', '.pytest_cache', '.venv', 'venv', '_palco310', '_palco310_embed')
$excluirArq = @('MANIFEST_SHA256.txt')

$arquivos = Get-ChildItem -LiteralPath $Caminho -Recurse -File -Force | Where-Object {
    $rel = $_.FullName.Substring($Caminho.Length).TrimStart('\', '/')
    $partes = $rel -split '[\\/]'
    $emDirExcluido = $false
    foreach ($p in $partes[0..([Math]::Max(0, $partes.Count - 2))]) {
        if ($excluirDir -contains $p) { $emDirExcluido = $true }
    }
    (-not $emDirExcluido) -and ($excluirArq -notcontains $_.Name)
} | Sort-Object FullName

function Get-Relativo([string]$base, [string]$full) {
    return $full.Substring($base.Length).TrimStart('\', '/').Replace('\', '/')
}

if ($Gerar) {
    $linhas = foreach ($f in $arquivos) {
        $hash = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLower()
        "{0}  {1}" -f $hash, (Get-Relativo $Caminho $f.FullName)
    }
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $texto = (($linhas -join "`n") + "`n")
    # grava em arquivo temporario e substitui (evita bloqueio/atributo somente leitura)
    $tmp = "$manifesto.tmp"
    [System.IO.File]::WriteAllText($tmp, $texto, $utf8)
    if (Test-Path -LiteralPath $manifesto) {
        $item = Get-Item -LiteralPath $manifesto -Force
        if ($item.IsReadOnly) { $item.IsReadOnly = $false }
        Remove-Item -LiteralPath $manifesto -Force
    }
    Move-Item -LiteralPath $tmp -Destination $manifesto -Force
    if (-not $Silencioso) { Write-Output ("manifesto gerado: {0} arquivos -> {1}" -f $arquivos.Count, $manifesto) }
    exit 0
}

if (-not (Test-Path -LiteralPath $manifesto)) {
    Write-Output ("ERRO: manifesto ausente: {0}" -f $manifesto)
    exit 1
}

$esperado = @{}
foreach ($linha in Get-Content -LiteralPath $manifesto -Encoding UTF8) {
    if ($linha -match '^([0-9a-fA-F]{64})\s+\*?(.+)$') {
        $esperado[$Matches[2].Replace('\', '/').Trim()] = $Matches[1].ToLower()
    }
}

$ok = 0
$divergentes = New-Object System.Collections.Generic.List[string]
$ausentes = New-Object System.Collections.Generic.List[string]

foreach ($f in $arquivos) {
    $rel = Get-Relativo $Caminho $f.FullName
    if (-not $esperado.ContainsKey($rel)) {
        $divergentes.Add(("NAO MANIFESTADO: {0}" -f $rel))
        continue
    }
    $hash = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLower()
    if ($hash -eq $esperado[$rel]) {
        $ok++
    } else {
        $divergentes.Add(("HASH DIFERENTE: {0} (manifesto {1}, atual {2})" -f $rel, $esperado[$rel], $hash))
    }
}

$presentes = @{}
foreach ($f in $arquivos) { $presentes[(Get-Relativo $Caminho $f.FullName)] = $true }
foreach ($rel in $esperado.Keys) {
    if (-not $presentes.ContainsKey($rel)) { $ausentes.Add(("AUSENTE: {0}" -f $rel)) }
}

if (-not $Silencioso) {
    foreach ($l in $divergentes) { Write-Output $l }
    foreach ($l in $ausentes) { Write-Output $l }
}

Write-Output ("arquivos no manifesto: {0} | conferem: {1} | divergentes: {2} | ausentes: {3}" -f $esperado.Count, $ok, $divergentes.Count, $ausentes.Count)

if (($divergentes.Count -eq 0) -and ($ausentes.Count -eq 0)) {
    Write-Output 'INTEGRIDADE OK'
    exit 0
}
Write-Output 'INTEGRIDADE FALHOU'
exit 1

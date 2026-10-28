# Synthetic resource-verifier regression tests, NOT native installer proof.
$ErrorActionPreference = 'Stop'
$checker = Join-Path $PSScriptRoot 'check-native.ps1'
function Get-Item {
    param([string]$LiteralPath)
    if ($LiteralPath -eq 'fixture-exe') { return [pscustomobject]@{ VersionInfo = $global:BsmmFixtureExe } }
    if ($LiteralPath -eq 'fixture-installer') { return [pscustomobject]@{ VersionInfo = $global:BsmmFixtureInstaller } }
    throw 'Unexpected resource fixture path'
}
$cases = @(
    @{ field = 'ProductVersion'; value = '1.1.2'; accepted = $true },
    @{ field = 'ProductVersion'; value = ('1.1.2' + (' ' * 100)); accepted = $true },
    @{ field = 'ProductVersion'; value = '1.1.3'; accepted = $false },
    @{ field = 'ProductVersion'; value = '1.1.2.0'; accepted = $false },
    @{ field = 'ProductVersion'; value = ' 1.1.2'; accepted = $false },
    @{ field = 'ProductVersion'; value = "1.1.2`t"; accepted = $false },
    @{ field = 'ProductVersion'; value = ('1.1.2' + [char]0); accepted = $false },
    @{ field = 'ProductVersion'; value = ''; accepted = $false },
    @{ field = 'ProductVersion'; value = '1.1. 2'; accepted = $false },
    @{ field = 'FileVersion'; value = '1.1.2.0             '; accepted = $true },
    @{ field = 'FileVersion'; value = '1.1.2.1'; accepted = $false },
    @{ field = 'ProductPrivatePart'; value = 1; accepted = $false },
    @{ field = 'FileBuildPart'; value = 3; accepted = $false },
    @{ field = 'ExeProductVersion'; value = '1.1.2 '; accepted = $false },
    @{ field = 'ExeProductVersion'; value = ('1.1.2' + [char]0); accepted = $false }
)
$caseIndex = 0
foreach ($case in $cases) {
    $caseIndex++
    # A called script has its own script scope. Keep fixture objects explicit in
    # this disposable PowerShell process so the Get-Item mock sees the same data.
    $global:BsmmFixtureExe = [pscustomobject]@{ ProductVersion = '1.1.2'; FileVersion = '1.1.2' }
    $global:BsmmFixtureInstaller = [pscustomobject]@{
        ProductVersion = ('1.1.2' + (' ' * 100)); FileVersion = '1.1.2.0             '
        ProductMajorPart = 1; ProductMinorPart = 1; ProductBuildPart = 2; ProductPrivatePart = 0
        FileMajorPart = 1; FileMinorPart = 1; FileBuildPart = 2; FilePrivatePart = 0
    }
    if ($case.field -eq 'ExeProductVersion') { $global:BsmmFixtureExe.ProductVersion = $case.value }
    else { $global:BsmmFixtureInstaller.($case.field) = $case.value }
    $global:LASTEXITCODE = 0
    $output = & $checker -Exe fixture-exe -Installer fixture-installer -Version 1.1.2
    $code = $LASTEXITCODE
    $metadata = $output | ConvertFrom-Json
    [ordered]@{ resource_fixture = $caseIndex; accepted = $case.accepted; exit = $code;
        metadata = $metadata } | ConvertTo-Json -Depth 3 -Compress | Write-Output
    if (($code -eq 0) -ne $case.accepted -or $metadata.ok -ne $case.accepted) {
        throw ('Resource regression case failed: ' + $case.field)
    }
}
Write-Output ('Resource verifier regression cases passed: ' + $cases.Count)
. (Join-Path $PSScriptRoot 'native-path.ps1')
$root = Join-Path ([System.IO.Path]::GetTempPath()) ('bsmm-path-test-' + [guid]::NewGuid().ToString('N'))
$real = Join-Path $root 'real'
$alias = Join-Path $root 'alias'
try {
    New-Item -ItemType Directory -Path $real -Force | Out-Null
    $original = Join-Path $real 'bsmm.exe'
    $other = Join-Path $real 'other.exe'
    [System.IO.File]::WriteAllText($original, 'synthetic file identity fixture')
    [System.IO.File]::WriteAllText($other, 'synthetic file identity fixture')
    New-Item -ItemType Junction -Path $alias -Target $real | Out-Null
    $expected = Get-FinalNativePath $original
    if (-not [string]::Equals($expected, (Get-FinalNativePath (Join-Path $alias 'bsmm.exe')), [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Directory-junction identity was not preserved'
    }
    if ([string]::Equals($expected, (Get-FinalNativePath $other), [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Different file with identical bytes was accepted'
    }
    $missingRejected = $false
    try { Get-FinalNativePath (Join-Path $root 'missing.exe') | Out-Null }
    catch { $missingRejected = $true }
    if (-not $missingRejected) { throw 'Missing shortcut target was accepted' }
    Write-Output 'Native path regression cases passed: junction alias, distinct copy, missing target'
} finally {
    if ([System.IO.Directory]::Exists($alias)) { [System.IO.Directory]::Delete($alias) }
    if ([System.IO.Directory]::Exists($root)) { [System.IO.Directory]::Delete($root, $true) }
}
exit 0

param(
    [Parameter(Mandatory=$true)][string]$Exe,
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][string]$Version,
    [switch]$Shortcuts
)
$ErrorActionPreference = 'Stop'
$info = (Get-Item -LiteralPath $Exe).VersionInfo
if ($info.ProductVersion -ne $Version -or $info.FileVersion -ne $Version) {
    throw 'Executable resource version differs from the package version'
}
$setupInfo = (Get-Item -LiteralPath $Installer).VersionInfo
if ($setupInfo.ProductVersion -ne $Version) { throw 'Installer product version mismatch' }
if ($Shortcuts) {
    $shell = New-Object -ComObject WScript.Shell
    $group = Join-Path $shell.SpecialFolders.Item('Programs') 'Bitcoin Solo Miner Monitor'
    foreach ($item in @(@('Start dashboard', 'start --open'), @('Stop dashboard', 'stop'))) {
        $path = Join-Path $group ($item[0] + '.lnk')
        if (-not (Test-Path -LiteralPath $path)) { throw 'Missing application shortcut' }
        $link = $shell.CreateShortcut($path)
        if ($link.TargetPath -ne $Exe -or $link.Arguments -ne $item[1]) { throw 'Shortcut points to incorrect executable or arguments' }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $group 'Agent guide.lnk'))) { throw 'Missing agent guide shortcut' }
}
Write-Output 'Native version resources and requested shortcuts verified.'

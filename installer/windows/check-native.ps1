param(
    [Parameter(Mandatory=$true)][string]$Exe,
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][string]$Version,
    [switch]$Shortcuts
)
$ErrorActionPreference = 'Stop'
# No exception text, paths, environment or arbitrary resource strings escape.
function Safe-Version($Value) {
    if ($Value -cmatch '^\d{1,5}\.\d{1,5}\.\d{1,5}(\.\d{1,5}|(a|b|rc)\d{1,5})?$' -or
        $Value -cmatch '^[0-9., \x00\r\n\t]{1,40}$') { return $Value }
    return 'withheld'
}
$diagnostic = [ordered]@{ stage = 'exe-resource'; ok = $false; shell_version = (Safe-Version $PSVersionTable.PSVersion.ToString()) }
try {
    $info = (Get-Item -LiteralPath $Exe).VersionInfo
    $diagnostic.exe_product = Safe-Version $info.ProductVersion
    $diagnostic.exe_file = Safe-Version $info.FileVersion
    if ($info.ProductVersion -ne $Version -or $info.FileVersion -ne $Version) {
        throw 'Executable resource version differs from the package version'
    }
    $diagnostic.stage = 'installer-resource'
    $setupInfo = (Get-Item -LiteralPath $Installer).VersionInfo
    $diagnostic.installer_product = Safe-Version $setupInfo.ProductVersion
    $diagnostic.installer_file = Safe-Version $setupInfo.FileVersion
    $diagnostic.installer_product_empty = [string]::IsNullOrEmpty($setupInfo.ProductVersion)
    $diagnostic.installer_file_empty = [string]::IsNullOrEmpty($setupInfo.FileVersion)
    $diagnostic.installer_fixed = Safe-Version (@($setupInfo.ProductMajorPart, $setupInfo.ProductMinorPart, $setupInfo.ProductBuildPart, $setupInfo.ProductPrivatePart) -join '.')
    $directInfo = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($Installer)
    $diagnostic.direct_product = Safe-Version $directInfo.ProductVersion
    $diagnostic.direct_file = Safe-Version $directInfo.FileVersion
    $diagnostic.direct_fixed = Safe-Version (@($directInfo.ProductMajorPart, $directInfo.ProductMinorPart, $directInfo.ProductBuildPart, $directInfo.ProductPrivatePart) -join '.')
    if ($setupInfo.ProductVersion -ne $Version) { throw 'Installer product version mismatch' }
    if ($Shortcuts) {
        $diagnostic.stage = 'shortcut-shell'
        $shell = New-Object -ComObject WScript.Shell
        $group = Join-Path $shell.SpecialFolders.Item('Programs') 'Bitcoin Solo Miner Monitor'
        foreach ($item in @(@('Start dashboard', 'start --open', 'start-shortcut'), @('Stop dashboard', 'stop', 'stop-shortcut'))) {
            $diagnostic.stage = $item[2]
            $path = Join-Path $group ($item[0] + '.lnk')
            $diagnostic.shortcut_exists = Test-Path -LiteralPath $path
            if (-not $diagnostic.shortcut_exists) { throw 'Missing application shortcut' }
            $link = $shell.CreateShortcut($path)
            $diagnostic.target_matches = $link.TargetPath -eq $Exe
            $diagnostic.arguments_match = $link.Arguments -eq $item[1]
            if (-not $diagnostic.target_matches -or -not $diagnostic.arguments_match) { throw 'Shortcut points to incorrect executable or arguments' }
        }
        $diagnostic.stage = 'guide-shortcut'
        $diagnostic.guide_exists = Test-Path -LiteralPath (Join-Path $group 'Agent guide.lnk')
        if (-not $diagnostic.guide_exists) { throw 'Missing agent guide shortcut' }
    }
    $diagnostic.stage = 'complete'
    $diagnostic.ok = $true
} catch {
    # Failure is retained by stage and nonzero exit; raw error stays private.
    $diagnostic.ok = $false
}
$diagnostic | ConvertTo-Json -Compress
if (-not $diagnostic.ok) { exit 1 }

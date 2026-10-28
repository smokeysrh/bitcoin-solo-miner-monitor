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
    if ($Version -cnotmatch '^([0-9]+)\.([0-9]+)\.([0-9]+)(?:(?:a|b|rc)[0-9]+)?$') { throw 'Unsupported canonical version' }
    $fixedVersion = @($Matches[1], $Matches[2], $Matches[3], '0') -join '.'
    $info = (Get-Item -LiteralPath $Exe).VersionInfo
    $diagnostic.exe_product = Safe-Version $info.ProductVersion
    $diagnostic.exe_file = Safe-Version $info.FileVersion
    if ($info.ProductVersion -ne $Version -or $info.FileVersion -ne $Version) {
        throw 'Executable resource version differs from the package version'
    }
    $diagnostic.stage = 'installer-resource'
    $setupInfo = (Get-Item -LiteralPath $Installer).VersionInfo
    # Inno 6.7.1 UpdateStringValue overwrites a fixed resource buffer's prefix,
    # leaving ASCII-space padding. Strip ONLY trailing ASCII spaces in Inno text;
    # executable text remains exact, and both binary tuples must also match.
    $productText = ([string]$setupInfo.ProductVersion).TrimEnd([char]' ')
    $fileText = ([string]$setupInfo.FileVersion).TrimEnd([char]' ')
    $diagnostic.installer_product = Safe-Version $productText
    $diagnostic.installer_file = Safe-Version $fileText
    $diagnostic.installer_product_space_padded = $productText -cne $setupInfo.ProductVersion
    $diagnostic.installer_file_space_padded = $fileText -cne $setupInfo.FileVersion
    $diagnostic.installer_fixed = Safe-Version (@($setupInfo.ProductMajorPart, $setupInfo.ProductMinorPart, $setupInfo.ProductBuildPart, $setupInfo.ProductPrivatePart) -join '.')
    $diagnostic.installer_file_fixed = Safe-Version (@($setupInfo.FileMajorPart, $setupInfo.FileMinorPart, $setupInfo.FileBuildPart, $setupInfo.FilePrivatePart) -join '.')
    if ($productText -cne $Version -or $fileText -cne $fixedVersion -or
        $diagnostic.installer_fixed -cne $fixedVersion -or $diagnostic.installer_file_fixed -cne $fixedVersion) {
        throw 'Installer text or fixed version mismatch'
    }
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

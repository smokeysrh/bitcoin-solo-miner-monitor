param(
    [Parameter(Mandatory=$true)][string]$Exe,
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][string]$Version,
    [switch]$Shortcuts
)
$ErrorActionPreference = 'Stop'
function Test-ExactVersion([string]$Actual, [string]$Expected) {
    # PowerShell's culture-based -ceq ignores embedded NULs even case-sensitively.
    return [string]::Equals($Actual, $Expected, [StringComparison]::Ordinal)
}
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
    if (-not (Test-ExactVersion $info.ProductVersion $Version) -or -not (Test-ExactVersion $info.FileVersion $Version)) {
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
    $diagnostic.installer_product_space_padded = -not (Test-ExactVersion $productText $setupInfo.ProductVersion)
    $diagnostic.installer_file_space_padded = -not (Test-ExactVersion $fileText $setupInfo.FileVersion)
    $diagnostic.installer_fixed = Safe-Version (@($setupInfo.ProductMajorPart, $setupInfo.ProductMinorPart, $setupInfo.ProductBuildPart, $setupInfo.ProductPrivatePart) -join '.')
    $diagnostic.installer_file_fixed = Safe-Version (@($setupInfo.FileMajorPart, $setupInfo.FileMinorPart, $setupInfo.FileBuildPart, $setupInfo.FilePrivatePart) -join '.')
    if (-not (Test-ExactVersion $productText $Version) -or -not (Test-ExactVersion $fileText $fixedVersion) -or
        -not (Test-ExactVersion $diagnostic.installer_fixed $fixedVersion) -or
        -not (Test-ExactVersion $diagnostic.installer_file_fixed $fixedVersion)) {
        throw 'Installer text or fixed version mismatch'
    }
    if ($Shortcuts) {
        $diagnostic.stage = 'shortcut-shell'
        Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
using System.Text;
public static class NativeShortcutPath {
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern uint GetLongPathName(string path, StringBuilder buffer, uint size);
}
'@
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
            $diagnostic.target_exists = Test-Path -LiteralPath $link.TargetPath -PathType Leaf
            $diagnostic.target_short_alias = $link.TargetPath.Contains('~')
            $size = [NativeShortcutPath]::GetLongPathName($link.TargetPath, $null, 0)
            if ($size -eq 0) { throw 'Cannot resolve shortcut target' }
            $buffer = New-Object System.Text.StringBuilder ([int]$size)
            $written = [NativeShortcutPath]::GetLongPathName($link.TargetPath, $buffer, $size)
            if ($written -eq 0 -or $written -ge $size) { throw 'Cannot resolve shortcut target' }
            $diagnostic.target_long_matches = [string]::Equals($buffer.ToString(), $Exe, [StringComparison]::OrdinalIgnoreCase)
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

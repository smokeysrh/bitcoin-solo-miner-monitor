# Resolve existing files through Windows handles, including directory junctions.
# Never infer identity from matching bytes, basename or a guessed path rewrite.
if (-not ('BsmmNativePath' -as [type])) {
    Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;
public static class BsmmNativePath {
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern uint GetFinalPathNameByHandle(SafeFileHandle handle, StringBuilder buffer, uint size, uint flags);
}
'@
}
function Get-FinalNativePath([string]$Path) {
    $file = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read,
                                 [System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete)
    try {
        $size = [BsmmNativePath]::GetFinalPathNameByHandle($file.SafeFileHandle, $null, 0, 0)
        if ($size -eq 0) { throw 'Cannot resolve final shortcut path' }
        $buffer = New-Object System.Text.StringBuilder ([int]$size)
        $written = [BsmmNativePath]::GetFinalPathNameByHandle($file.SafeFileHandle, $buffer, $size, 0)
        if ($written -eq 0 -or $written -ge $size) { throw 'Cannot resolve final shortcut path' }
        return $buffer.ToString()
    } finally { $file.Dispose() }
}

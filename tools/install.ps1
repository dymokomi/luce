# Install the Luce compiler on Windows.
#
#   irm https://luce.luciaos.com/install.ps1 | iex
#
# The release archive for x86-64 Windows is downloaded from the GitHub release, its
# SHA-256 checked against the published digest, its contents checked, and only then does
# it replace %LOCALAPPDATA%\luce; an interrupted run leaves the previous installation
# in place. bin\ and ~\.luce\bin are added to the user PATH and to this session's.
# Running it again installs a fresh copy of the same release. Works in Windows
# PowerShell 5.1 and PowerShell 7.
#
# Overrides, for testing and managed layouts, all absolute paths:
#   LUCE_INSTALL_DIR      where to install (default %LOCALAPPDATA%\luce)
#   LUCE_INSTALL_VERSION  the release to install (default the one below)
#   LUCE_INSTALL_URL      the directory the archives are read from; a file:/// URL works
#   LUCE_INSTALL_NO_PATH  1 leaves the user PATH alone
$ErrorActionPreference = 'Stop'
$version = '0.8.12'
$product = 'luce'

if ($env:LUCE_INSTALL_VERSION) { $version = $env:LUCE_INSTALL_VERSION }
$baseUrl = if ($env:LUCE_INSTALL_URL) { $env:LUCE_INSTALL_URL } else { "https://github.com/dymokomi/luce/releases/download/luce-$version" }
$installRoot = if ($env:LUCE_INSTALL_DIR) { $env:LUCE_INSTALL_DIR } else { Join-Path $env:LOCALAPPDATA $product }
$host_ = 'x86_64-windows'
$archiveName = "$product-$version-$host_.tar.gz"
$tree = "$product-$version"

function Fail($message) {
    Write-Error "${product}: $message"
    exit 1
}

if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    Fail 'this release is for x86-64 Windows'
}
if ([Environment]::OSVersion.Version.Major -lt 10) {
    Fail 'this release needs Windows 10 or newer'
}
# Windows' own bsdtar: Git for Windows puts a GNU tar earlier on PATH that reads
# "C:\..." as a remote host "C" and cannot open the archive.
$tar = Join-Path $env:SystemRoot 'System32\tar.exe'
if (-not (Test-Path -LiteralPath $tar -PathType Leaf)) {
    Fail 'tar.exe is required (it ships with Windows 10 1803 and newer)'
}

# The compiler drives MSYS2's UCRT64 GCC to assemble and link; without it, a successful
# install would leave a compiler that cannot build its first program.
$missing = @()
foreach ($tool in 'gcc', 'as', 'ar', 'nm') {
    if (-not (Get-Command "$tool.exe" -ErrorAction SilentlyContinue)) { $missing += $tool }
}
if ($missing.Count -gt 0) {
    Write-Host "${product}: a C toolchain is required on PATH (missing: $($missing -join ', '))"
    Write-Host "${product}: install MSYS2 from https://www.msys2.org, then in its shell run:"
    Write-Host "${product}:     pacman -S mingw-w64-ucrt-x86_64-gcc"
    Write-Host "${product}: and add C:\msys64\ucrt64\bin to your PATH, then run this command again"
    exit 1
}

# An override may not turn a user installer into a request to replace a system tree.
if (-not [System.IO.Path]::IsPathRooted($installRoot)) { Fail "LUCE_INSTALL_DIR must be an absolute path: $installRoot" }
$normalized = [System.IO.Path]::GetFullPath($installRoot).TrimEnd('\')
foreach ($protected in @($env:SystemRoot, $env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:ProgramData, $env:SystemDrive + '\')) {
    if ($protected -and ($normalized -eq $protected.TrimEnd('\') -or $normalized.StartsWith($protected.TrimEnd('\') + '\', [System.StringComparison]::OrdinalIgnoreCase)) -and -not $normalized.StartsWith($env:LOCALAPPDATA, [System.StringComparison]::OrdinalIgnoreCase)) {
        if ($protected -ne $env:SystemDrive + '\') { Fail "refusing a system directory: $installRoot" }
    }
}
if ($normalized -eq ($env:SystemDrive + '\')) { Fail "refusing the root of the system drive" }
$installRoot = $normalized

$parent = Split-Path -Parent $installRoot
New-Item -ItemType Directory -Force -Path $parent | Out-Null
$stamp = [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
$tmp = Join-Path $parent ".$product-install-$stamp"
$backup = Join-Path $parent ".$product-old-$stamp"
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    Write-Host "==> downloading $product $version for Windows x86-64"
    $archive = Join-Path $tmp $archiveName
    $client = New-Object System.Net.WebClient
    $client.DownloadFile("$baseUrl/$archiveName", $archive)
    $client.DownloadFile("$baseUrl/$archiveName.sha256", "$archive.sha256")

    $expected = ((Get-Content "$archive.sha256" -First 1) -split '\s+')[0].ToLowerInvariant()
    if ($expected -notmatch '^[0-9a-f]{64}$') { Fail 'the published checksum is not a SHA-256 digest' }
    $actual = (Get-FileHash -Algorithm SHA256 $archive).Hash.ToLowerInvariant()
    if ($actual -ne $expected) { Fail "the archive's checksum does not match the published digest" }

    # The checksum authenticates the bytes; the archive is still confined to its own
    # directory before anything is written.
    $members = & $tar -tzf $archive
    if ($LASTEXITCODE -ne 0) { Fail 'the archive cannot be listed' }
    foreach ($member in $members) {
        $path = $member.TrimEnd('/')
        if ($path -eq '' -or $path.StartsWith('/') -or $path -match '(^|/)\.\.(/|$)' -or -not ($path -eq $tree -or $path.StartsWith("$tree/"))) {
            Fail "the archive contains an unsafe member path: $member"
        }
    }
    $unpack = Join-Path $tmp 'unpack'
    New-Item -ItemType Directory -Path $unpack | Out-Null
    & $tar -xzf $archive -C $unpack
    if ($LASTEXITCODE -ne 0) { Fail 'the archive could not be unpacked' }
    $release = Join-Path $unpack $tree
    # `luce` compiles a program to Base and runs the `luce-base` beside it; both ship in the tree
    foreach ($tool in 'luce.exe', 'luce-base.exe') {
        if (-not (Test-Path (Join-Path $release "bin\$tool"))) { Fail "the archive has no bin\$tool" }
    }
    # luc, the project tool, ships beside the compilers; Base's standard library is read from
    # source under share\luce-base\std with every build, not shipped as a prebuilt library.
    if (-not (Test-Path (Join-Path $release 'bin\luc.exe'))) { Fail 'the archive has no bin\luc.exe' }
    if (-not (Test-Path (Join-Path $release 'share\luce-base\std'))) { Fail 'the archive has no share\luce-base\std' }
    $stated = (Get-Content (Join-Path $release "share\$product\VERSION") -Raw).Trim()
    if ($stated -ne $version) { Fail "the archive's VERSION is $stated, not $version" }
    $reported = (& (Join-Path $release 'bin\luce.exe') --version).Trim()
    if ($reported -ne "luce $version") { Fail "the compiler in the archive reports '$reported', not 'luce $version'" }

    # Replace only now, and put the old tree back if the move fails.
    if (Test-Path $installRoot) { Move-Item $installRoot $backup }
    try {
        Move-Item $release $installRoot
    } catch {
        if (Test-Path $backup) { Move-Item $backup $installRoot }
        Fail "could not replace $installRoot"
    }
    if (Test-Path $backup) { Remove-Item -Recurse -Force $backup }
} finally {
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
}

# The compiler's commands, and ~\.luce\bin where `luc install` links applications: on the
# user PATH for every new terminal, and on this session's PATH now, since `irm | iex` runs here.
$bin = Join-Path $installRoot 'bin'
$apps = Join-Path $env:USERPROFILE '.luce\bin'
if ($env:LUCE_INSTALL_NO_PATH -ne '1') {
    New-Item -ItemType Directory -Force -Path $apps | Out-Null
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $entries = @()
    if ($userPath) { $entries = @($userPath -split ';' | Where-Object { $_ -ne '' }) }
    $missing = @(@($bin, $apps) | Where-Object { $entries -notcontains $_ })
    if ($missing.Count -eq 0) {
        Write-Host "==> the user PATH already names $bin and $apps"
    } else {
        [Environment]::SetEnvironmentVariable('Path', ($missing + $entries) -join ';', 'User')
        Write-Host "==> added $($missing -join ' and ') to the user PATH"
    }
    foreach ($directory in @($apps, $bin)) {
        if (-not (($env:Path -split ';') -contains $directory)) { $env:Path = "$directory;$env:Path" }
    }
}

Write-Host "==> $product $version installed at $installRoot"
Write-Host '    luce --version'
Write-Host '    luc --version   # the project tool, installed with it'

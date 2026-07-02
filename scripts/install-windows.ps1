<#
.SYNOPSIS
Install the EVA Hermes skins and Windows Terminal CRT profile for the current Windows user.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1

.EXAMPLE
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1 -Theme All -Skin eva-01

.EXAMPLE
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1 -DryRun
#>

[CmdletBinding()]
param(
    [ValidateSet("AmberReadable", "Amber", "Readable", "Magi", "All")]
    [string]$Theme = "AmberReadable",

    [string]$Skin = "eva-02",

    [switch]$SkipFonts,
    [switch]$SkipHermes,
    [switch]$SkipWindowsTerminal,
    [switch]$SkipKeybindings,
    [switch]$SkipHermesConfig,

    [string]$SettingsPath,

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[awesome-hermes-eva-skins] $Message"
}

function Write-DryRun {
    param([string]$Message)
    if ($DryRun) {
        Write-Host "[dry-run] $Message"
    }
}

function Get-RepoRoot {
    if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        return (Get-Location).Path
    }

    return (Split-Path -Parent $PSScriptRoot)
}

function Get-RequiredPath {
    param(
        [string]$Path,
        [string]$Description,
        [switch]$Directory
    )

    if ($Directory) {
        if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
            throw "$Description not found: $Path"
        }
    } else {
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
            throw "$Description not found: $Path"
        }
    }

    return (Resolve-Path -LiteralPath $Path).Path
}

function Set-ObjectProperty {
    param(
        [object]$Object,
        [string]$Name,
        [object]$Value
    )

    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        Add-Member -InputObject $Object -MemberType NoteProperty -Name $Name -Value $Value
    } else {
        $property.Value = $Value
    }
}

function Get-ObjectProperty {
    param(
        [object]$Object,
        [string]$Name
    )

    if ($null -eq $Object) {
        return $null
    }

    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }

    return $property.Value
}

function Remove-JsoncSyntax {
    param([string]$Text)

    $builder = New-Object System.Text.StringBuilder
    $inString = $false
    $escaped = $false
    $i = 0

    while ($i -lt $Text.Length) {
        $char = $Text[$i]

        if ($inString) {
            [void]$builder.Append($char)

            if ($escaped) {
                $escaped = $false
            } elseif ($char -eq '\') {
                $escaped = $true
            } elseif ($char -eq '"') {
                $inString = $false
            }

            $i++
            continue
        }

        if ($char -eq '"') {
            $inString = $true
            [void]$builder.Append($char)
            $i++
            continue
        }

        if (($char -eq '/') -and (($i + 1) -lt $Text.Length) -and ($Text[$i + 1] -eq '/')) {
            while (($i -lt $Text.Length) -and ($Text[$i] -ne "`n")) {
                $i++
            }
            continue
        }

        if (($char -eq '/') -and (($i + 1) -lt $Text.Length) -and ($Text[$i + 1] -eq '*')) {
            $i += 2
            while (($i + 1) -lt $Text.Length) {
                if (($Text[$i] -eq '*') -and ($Text[$i + 1] -eq '/')) {
                    $i += 2
                    break
                }
                $i++
            }
            [void]$builder.Append(" ")
            continue
        }

        [void]$builder.Append($char)
        $i++
    }

    $withoutComments = $builder.ToString()
    $result = New-Object System.Text.StringBuilder
    $inString = $false
    $escaped = $false
    $i = 0

    while ($i -lt $withoutComments.Length) {
        $char = $withoutComments[$i]

        if ($inString) {
            [void]$result.Append($char)

            if ($escaped) {
                $escaped = $false
            } elseif ($char -eq '\') {
                $escaped = $true
            } elseif ($char -eq '"') {
                $inString = $false
            }

            $i++
            continue
        }

        if ($char -eq '"') {
            $inString = $true
            [void]$result.Append($char)
            $i++
            continue
        }

        if ($char -eq ',') {
            $j = $i + 1
            while (($j -lt $withoutComments.Length) -and ([char]::IsWhiteSpace($withoutComments[$j]))) {
                $j++
            }

            if (($j -lt $withoutComments.Length) -and (($withoutComments[$j] -eq '}') -or ($withoutComments[$j] -eq ']'))) {
                $i++
                continue
            }
        }

        [void]$result.Append($char)
        $i++
    }

    return $result.ToString()
}

function Read-JsoncFile {
    param([string]$Path)

    $raw = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
    $json = Remove-JsoncSyntax -Text $raw
    return ($json | ConvertFrom-Json)
}

function Write-JsonFile {
    param(
        [string]$Path,
        [object]$Value
    )

    $json = $Value | ConvertTo-Json -Depth 100
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $json + [Environment]::NewLine, $encoding)
}

function Convert-ToArray {
    param([object]$Value)

    if ($null -eq $Value) {
        return @()
    }

    if ($Value -is [System.Array]) {
        return @($Value)
    }

    return @($Value)
}

function Upsert-ByObjectProperty {
    param(
        [object[]]$Items,
        [string]$PropertyName,
        [string]$PropertyValue,
        [object]$Replacement
    )

    $output = New-Object System.Collections.ArrayList
    $found = $false

    foreach ($item in (Convert-ToArray -Value $Items)) {
        if (($null -ne $item) -and ((Get-ObjectProperty -Object $item -Name $PropertyName) -eq $PropertyValue)) {
            [void]$output.Add($Replacement)
            $found = $true
        } else {
            [void]$output.Add($item)
        }
    }

    if (-not $found) {
        [void]$output.Add($Replacement)
    }

    return $output.ToArray()
}

function Add-UniqueAction {
    param(
        [object[]]$Actions,
        [object]$Action
    )

    $command = Get-ObjectProperty -Object $Action -Name "command"
    $keys = Get-ObjectProperty -Object $Action -Name "keys"

    foreach ($existing in (Convert-ToArray -Value $Actions)) {
        if (($null -ne $existing) -and
            ((Get-ObjectProperty -Object $existing -Name "command") -eq $command) -and
            ((Get-ObjectProperty -Object $existing -Name "keys") -eq $keys)) {
            return (Convert-ToArray -Value $Actions)
        }
    }

    $output = New-Object System.Collections.ArrayList
    foreach ($existing in (Convert-ToArray -Value $Actions)) {
        [void]$output.Add($existing)
    }
    [void]$output.Add($Action)

    return $output.ToArray()
}

function Install-BundledFonts {
    param([string]$RepoRoot)

    $fontSource = Join-Path $RepoRoot "fonts\ark-pixel-font-12px-monospaced-ttf-v2026.05.07"
    Get-RequiredPath -Path $fontSource -Description "Bundled font directory" -Directory | Out-Null

    $fontDest = Join-Path $env:LOCALAPPDATA "Microsoft\Windows\Fonts"
    $fontReg = "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts"
    $fonts = @(
        @{ Name = "Ark Pixel 12px Mono latin (TrueType)"; File = "ark-pixel-12px-monospaced-latin.ttf" },
        @{ Name = "Ark Pixel 12px Mono zh_cn (TrueType)"; File = "ark-pixel-12px-monospaced-zh_cn.ttf" },
        @{ Name = "Ark Pixel 12px Mono ja (TrueType)"; File = "ark-pixel-12px-monospaced-ja.ttf" },
        @{ Name = "Ark Pixel 12px Mono ko (TrueType)"; File = "ark-pixel-12px-monospaced-ko.ttf" }
    )

    Write-Step "Installing bundled Ark Pixel TTF fonts for the current user."
    Write-DryRun "Would create $fontDest and update $fontReg."

    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $fontDest | Out-Null
        New-Item -Path $fontReg -Force | Out-Null
    }

    foreach ($font in $fonts) {
        $source = Join-Path $fontSource $font.File
        Get-RequiredPath -Path $source -Description "Font file" | Out-Null
        $target = Join-Path $fontDest $font.File

        if ($DryRun) {
            Write-DryRun "Would copy $source to $target and register $($font.Name)."
            continue
        }

        Copy-Item -LiteralPath $source -Destination $target -Force
        New-ItemProperty -Path $fontReg -Name $font.Name -Value $font.File -PropertyType String -Force | Out-Null
    }

    if (-not $DryRun) {
        try {
            Add-Type -Namespace Win32 -Name NativeMethods -MemberDefinition @"
[System.Runtime.InteropServices.DllImport("user32.dll", SetLastError=true, CharSet=System.Runtime.InteropServices.CharSet.Auto)]
public static extern System.IntPtr SendMessageTimeout(
        System.IntPtr hWnd,
        uint Msg,
        System.UIntPtr wParam,
        string lParam,
        uint fuFlags,
        uint uTimeout,
        out System.UIntPtr lpdwResult);
"@
            $result = [UIntPtr]::Zero
            [Win32.NativeMethods]::SendMessageTimeout([IntPtr]0xffff, 0x001D, [UIntPtr]::Zero, $null, 0x0002, 1000, [ref]$result) | Out-Null
        } catch {
            Write-Warning "Fonts were copied, but Windows font cache notification failed. Restart Windows Terminal if the font is not visible yet."
        }
    }
}

function Install-HermesSkins {
    param(
        [string]$RepoRoot,
        [string]$SkinName
    )

    $skinSourceDir = Join-Path $RepoRoot "skins"
    Get-RequiredPath -Path $skinSourceDir -Description "Hermes skin directory" -Directory | Out-Null

    $skinSource = Join-Path $skinSourceDir "$SkinName.yaml"
    Get-RequiredPath -Path $skinSource -Description "Requested Hermes skin" | Out-Null

    if ([string]::IsNullOrWhiteSpace($env:HERMES_HOME)) {
        $hermesHome = Join-Path $env:LOCALAPPDATA "hermes"
    } else {
        $hermesHome = $env:HERMES_HOME
    }

    $skinDestDir = Join-Path $hermesHome "skins"
    Write-Step "Installing Hermes YAML skins to $skinDestDir."
    Write-DryRun "Would copy all skins/*.yaml files to $skinDestDir."

    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $skinDestDir | Out-Null
    }

    foreach ($skinFile in (Get-ChildItem -LiteralPath $skinSourceDir -Filter "*.yaml")) {
        $target = Join-Path $skinDestDir $skinFile.Name
        if ($DryRun) {
            Write-DryRun "Would copy $($skinFile.FullName) to $target."
        } else {
            Copy-Item -LiteralPath $skinFile.FullName -Destination $target -Force
        }
    }

    if (-not $SkipHermesConfig) {
        $hermes = Get-Command "hermes" -ErrorAction SilentlyContinue
        if ($null -eq $hermes) {
            Write-Warning "Hermes CLI was not found on PATH. Skins were installed, but you still need to run '/skin $SkinName' inside Hermes later."
        } elseif ($DryRun) {
            Write-DryRun "Would run: hermes config set display.skin $SkinName"
        } else {
            Write-Step "Setting Hermes display.skin to $SkinName."
            & $hermes.Source config set display.skin $SkinName
        }
    }
}

function Get-WindowsTerminalSettingsPath {
    if (-not [string]::IsNullOrWhiteSpace($SettingsPath)) {
        if (-not (Test-Path -LiteralPath $SettingsPath -PathType Leaf)) {
            throw "Windows Terminal settings file not found: $SettingsPath"
        }
        return (Resolve-Path -LiteralPath $SettingsPath).Path
    }

    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json"),
        (Join-Path $env:LOCALAPPDATA "Packages\Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe\LocalState\settings.json"),
        (Join-Path $env:LOCALAPPDATA "Microsoft\Windows Terminal\settings.json")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    throw "Could not find Windows Terminal settings.json. Open Windows Terminal once, or pass -SettingsPath."
}

function Get-ThemeSpecs {
    param([string]$SelectedTheme)

    $all = @(
        @{
            Name = "Amber"
            SchemeFile = "cool-retro-amber.scheme.jsonc"
            SchemeName = "Cool Retro Amber"
            ProfileFile = "cool-retro-frame-amber.profile.jsonc"
            ProfileName = "Cool Retro Frame Amber"
            ShaderFile = "cool-retro-frame-amber.hlsl"
        },
        @{
            Name = "Readable"
            SchemeFile = "cool-retro-amber.scheme.jsonc"
            SchemeName = "Cool Retro Amber"
            ProfileFile = "cool-retro-frame-readable.profile.jsonc"
            ProfileName = "Cool Retro Frame Readable"
            ShaderFile = "cool-retro-frame-readable.hlsl"
        },
        @{
            Name = "Magi"
            SchemeFile = "eva-magi.scheme.jsonc"
            SchemeName = "EVA MAGI"
            ProfileFile = "cool-retro-frame-magi.profile.jsonc"
            ProfileName = "EVA MAGI Frame"
            ShaderFile = "cool-retro-frame-magi.hlsl"
        }
    )

    if ($SelectedTheme -eq "All") {
        return $all
    }

    if ($SelectedTheme -eq "AmberReadable") {
        return @($all | Where-Object { ($_.Name -eq "Amber") -or ($_.Name -eq "Readable") })
    }

    return @($all | Where-Object { $_.Name -eq $SelectedTheme })
}

function Install-WindowsTerminalProfile {
    param(
        [string]$RepoRoot,
        [string]$SelectedTheme
    )

    $shaderSourceDir = Join-Path $RepoRoot "shaders"
    $windowsTerminalDir = Join-Path $RepoRoot "windows-terminal"
    Get-RequiredPath -Path $shaderSourceDir -Description "Shader directory" -Directory | Out-Null
    Get-RequiredPath -Path $windowsTerminalDir -Description "Windows Terminal snippet directory" -Directory | Out-Null

    $shaderDestDir = Join-Path $env:LOCALAPPDATA "WindowsTerminalShaders"
    Write-Step "Installing Windows Terminal HLSL shaders to $shaderDestDir."
    Write-DryRun "Would copy shaders/*.hlsl to $shaderDestDir."

    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $shaderDestDir | Out-Null
    }

    foreach ($shader in (Get-ChildItem -LiteralPath $shaderSourceDir -Filter "*.hlsl")) {
        $target = Join-Path $shaderDestDir $shader.Name
        if ($DryRun) {
            Write-DryRun "Would copy $($shader.FullName) to $target."
        } else {
            Copy-Item -LiteralPath $shader.FullName -Destination $target -Force
        }
    }

    $settingsFile = Get-WindowsTerminalSettingsPath
    $backupPath = "$settingsFile.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

    Write-Step "Updating Windows Terminal settings: $settingsFile"
    Write-DryRun "Would create backup $backupPath."

    $settings = Read-JsoncFile -Path $settingsFile

    $schemes = Convert-ToArray -Value (Get-ObjectProperty -Object $settings -Name "schemes")

    $profiles = Get-ObjectProperty -Object $settings -Name "profiles"
    if ($null -eq $profiles) {
        $profiles = [pscustomobject]@{}
        Set-ObjectProperty -Object $settings -Name "profiles" -Value $profiles
    }
    $profileList = Convert-ToArray -Value (Get-ObjectProperty -Object $profiles -Name "list")

    foreach ($themeSpec in (Get-ThemeSpecs -SelectedTheme $SelectedTheme)) {
        $schemePath = Join-Path $windowsTerminalDir $themeSpec.SchemeFile
        $profilePath = Join-Path $windowsTerminalDir $themeSpec.ProfileFile
        $shaderPath = Join-Path $shaderDestDir $themeSpec.ShaderFile

        Get-RequiredPath -Path $schemePath -Description "Windows Terminal scheme snippet" | Out-Null
        Get-RequiredPath -Path $profilePath -Description "Windows Terminal profile snippet" | Out-Null

        $scheme = Read-JsoncFile -Path $schemePath
        $profile = Read-JsoncFile -Path $profilePath
        Set-ObjectProperty -Object $profile -Name "experimental.pixelShaderPath" -Value $shaderPath

        $schemes = Upsert-ByObjectProperty -Items $schemes -PropertyName "name" -PropertyValue $themeSpec.SchemeName -Replacement $scheme
        $profileList = Upsert-ByObjectProperty -Items $profileList -PropertyName "name" -PropertyValue $themeSpec.ProfileName -Replacement $profile

        Write-DryRun "Would upsert scheme '$($themeSpec.SchemeName)' and profile '$($themeSpec.ProfileName)'."
    }

    Set-ObjectProperty -Object $settings -Name "schemes" -Value $schemes
    Set-ObjectProperty -Object $profiles -Name "list" -Value $profileList

    if (-not $SkipKeybindings) {
        $keybindingsPath = Join-Path $windowsTerminalDir "keybindings.jsonc"
        Get-RequiredPath -Path $keybindingsPath -Description "Windows Terminal keybindings snippet" | Out-Null
        $keybindings = Convert-ToArray -Value (Read-JsoncFile -Path $keybindingsPath)

        $targetProperty = "actions"
        if ($null -ne (Get-ObjectProperty -Object $settings -Name "keybindings")) {
            $targetProperty = "keybindings"
        }

        $actions = Convert-ToArray -Value (Get-ObjectProperty -Object $settings -Name $targetProperty)
        foreach ($binding in $keybindings) {
            $actions = Add-UniqueAction -Actions $actions -Action $binding
        }
        Set-ObjectProperty -Object $settings -Name $targetProperty -Value $actions
        Write-DryRun "Would upsert Shift+F10 and Shift+F11 shortcuts into $targetProperty."
    }

    if ($DryRun) {
        return
    }

    Copy-Item -LiteralPath $settingsFile -Destination $backupPath -Force
    Write-JsonFile -Path $settingsFile -Value $settings
    Write-Step "Wrote settings backup: $backupPath"
}

$repoRoot = Get-RepoRoot
Get-RequiredPath -Path $repoRoot -Description "Repository root" -Directory | Out-Null

Write-Step "Repository root: $repoRoot"

if ($SkipFonts) {
    Write-Step "Skipping TTF font installation."
} else {
    Install-BundledFonts -RepoRoot $repoRoot
}

if ($SkipHermes) {
    Write-Step "Skipping Hermes YAML installation."
} else {
    Install-HermesSkins -RepoRoot $repoRoot -SkinName $Skin
}

if ($SkipWindowsTerminal) {
    Write-Step "Skipping Windows Terminal HLSL/profile installation."
} else {
    Install-WindowsTerminalProfile -RepoRoot $repoRoot -SelectedTheme $Theme
}

Write-Step "Done. Restart Windows Terminal, then open the installed profile. Default profiles: Cool Retro Frame Amber and Cool Retro Frame Readable."

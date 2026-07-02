# awesome-hermes-eva-skins

[简体中文](../README.md) | English

EVA-style skins for Hermes Agent, paired with a Windows Terminal amber CRT profile and pixel shader.

This repo intentionally ships only reusable theme assets. It does not include a full local Windows Terminal `settings.json` or a full Hermes home directory, because those files often contain machine-specific paths, profile IDs, sessions, caches, and credentials.

## What is included

- `skins/eva-00.yaml`, `skins/eva-01.yaml`, `skins/eva-02.yaml`, `skins/eva-nerv.yaml` - Hermes CLI skins.
- `tools/braille-studio.html` - browser UI for image-to-colored-braille conversion.
- `fonts/ark-pixel-font-12px-monospaced-ttf-v2026.05.07/` - Ark Pixel font files used by the terminal profile.
- `shaders/cool-retro-frame-amber.hlsl`, `shaders/cool-retro-frame-readable.hlsl`, `shaders/cool-retro-frame-magi.hlsl` - CRT pixel shaders for Windows Terminal.
- `windows-terminal/cool-retro-amber.scheme.jsonc`, `windows-terminal/eva-magi.scheme.jsonc` - Windows Terminal color scheme snippets.
- `windows-terminal/cool-retro-frame-amber.profile.jsonc`, `windows-terminal/cool-retro-frame-readable.profile.jsonc`, `windows-terminal/cool-retro-frame-magi.profile.jsonc` - Windows Terminal profile snippets.
- `windows-terminal/keybindings.jsonc` - optional shader/focus toggle keybindings.
- `scripts/install-windows.ps1` - current-user Windows installer for TTF fonts, Hermes YAML skins, HLSL shaders, and Windows Terminal profiles.

## Requirements

- Hermes Agent 0.16.0 or newer.
- Windows Terminal with `experimental.pixelShaderPath` support.
- The bundled Ark Pixel fonts installed locally. The Windows Terminal profile uses `Ark Pixel 12px Mono zh_cn`, `Ark Pixel 12px Mono ja`, `Ark Pixel 12px Mono ko`, and `Ark Pixel 12px Mono latin`.
- UTF-8 editing. Do not save the YAML files as ANSI/GBK.

## Option 1: Simple automated install

Use this path if you want the quickest setup. The installer writes only to the current user account and does not require administrator privileges. Before changing Windows Terminal `settings.json`, it creates a `.bak-timestamp` backup.

Clone the repo:

```powershell
git clone https://github.com/Chael-Chael/awesome-hermes-eva-skins.git
cd awesome-hermes-eva-skins
```

Preview the changes first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1 -DryRun
```

Run the install:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1
```

The script automatically:

1. Installs the four bundled Ark Pixel `.ttf` fonts for the current user.
2. Copies `skins/*.yaml` into the Hermes skin directory and enables `eva-02` by default.
3. Copies `shaders/*.hlsl` into `%LOCALAPPDATA%\WindowsTerminalShaders`.
4. Finds the real Windows Terminal `settings.json`, then merges the `Cool Retro Amber` color scheme, the `Cool Retro Frame Amber` and `Cool Retro Frame Readable` PowerShell profiles, and `Shift+F10`/`Shift+F11` shortcuts.

After installation:

1. Restart Windows Terminal.
2. Open `Cool Retro Frame Amber` or `Cool Retro Frame Readable` from the Windows Terminal dropdown.
3. Start Hermes. If the installer did not find the `hermes` command, run this inside Hermes:

```text
/skin eva-02
```

Common options:

```powershell
# Install Amber, Readable, and MAGI Windows Terminal profiles
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1 -Theme All

# Install only the readable Windows Terminal profile
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1 -Theme Readable

# Use eva-01 as the default Hermes skin
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1 -Skin eva-01

# Install only Hermes YAML skins, without changing fonts or Windows Terminal
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1 -SkipFonts -SkipWindowsTerminal
```

The script does not install Hermes Agent or Windows Terminal itself. If it cannot find Windows Terminal `settings.json`, open Windows Terminal once, then run the script again.

## Option 2: Manual install

Use this path if you want to inspect each change or copy files into custom locations.

### Step 1: Install TTF fonts

Install the bundled Ark Pixel fonts before importing the Windows Terminal profile. The profile expects these exact font family names:

```text
Ark Pixel 12px Mono zh_cn
Ark Pixel 12px Mono ja
Ark Pixel 12px Mono ko
Ark Pixel 12px Mono latin
```

Windows GUI method:

1. Open `fonts/ark-pixel-font-12px-monospaced-ttf-v2026.05.07/`.
2. Select the four `.ttf` files.
3. Right-click and choose `Install` or `Install for all users`.
4. Restart Windows Terminal.

PowerShell per-user install:

```powershell
$fontSource = ".\fonts\ark-pixel-font-12px-monospaced-ttf-v2026.05.07"
$fontDest = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"
$fontReg = "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts"

New-Item -ItemType Directory -Force $fontDest | Out-Null
New-Item -Path $fontReg -Force | Out-Null

$fonts = @{
  "Ark Pixel 12px Mono latin (TrueType)" = "ark-pixel-12px-monospaced-latin.ttf"
  "Ark Pixel 12px Mono zh_cn (TrueType)" = "ark-pixel-12px-monospaced-zh_cn.ttf"
  "Ark Pixel 12px Mono ja (TrueType)" = "ark-pixel-12px-monospaced-ja.ttf"
  "Ark Pixel 12px Mono ko (TrueType)" = "ark-pixel-12px-monospaced-ko.ttf"
}

foreach ($entry in $fonts.GetEnumerator()) {
  Copy-Item (Join-Path $fontSource $entry.Value) (Join-Path $fontDest $entry.Value) -Force
  New-ItemProperty -Path $fontReg -Name $entry.Key -Value $entry.Value -PropertyType String -Force | Out-Null
}
```

If the banner renders as boxes, falls back to a normal monospace font, or the ASCII art is badly misaligned, the fonts are not installed or Windows Terminal has not been restarted.

This step lets Windows Terminal find the pixel font expected by the EVA profile. Without it, the terminal can still open, but banners, CJK text, and pixel characters may render as boxes or misalign.

### Step 2: Install the Hermes YAML skin

Clone this repo, then copy the skin into your Hermes skin directory:

```powershell
git clone https://github.com/Chael-Chael/awesome-hermes-eva-skins.git
cd awesome-hermes-eva-skins

New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\hermes\skins"
Copy-Item ".\skins\eva-02.yaml" "$env:LOCALAPPDATA\hermes\skins\eva-02.yaml"
```

Start Hermes and switch skin:

```text
hermes
/skin eva-02
```

To persist the skin without using the interactive command:

```powershell
hermes config set display.skin eva-02
```

Hermes also respects `HERMES_HOME`. If you use a custom Hermes home, copy the YAML to:

```text
%HERMES_HOME%\skins\eva-02.yaml
```

This step puts the Hermes-readable skin file under the Hermes home directory. `eva-02.yaml` is the default recommendation, but you can also copy and enable `eva-00.yaml`, `eva-01.yaml`, or `eva-nerv.yaml`.

### Step 3: Install the Windows Terminal HLSL look

Copy the shader to a stable local directory:

```powershell
$shaderDir = "$env:LOCALAPPDATA\WindowsTerminalShaders"
New-Item -ItemType Directory -Force $shaderDir
Copy-Item ".\shaders\cool-retro-frame-amber.hlsl" "$shaderDir\cool-retro-frame-amber.hlsl"
Copy-Item ".\shaders\cool-retro-frame-readable.hlsl" "$shaderDir\cool-retro-frame-readable.hlsl"
```

Open Windows Terminal settings JSON:

1. Open Windows Terminal.
2. Press `Ctrl+,`.
3. Click `Open JSON file`.

Then edit three sections:

1. Add the object from `windows-terminal/cool-retro-amber.scheme.jsonc` into the top-level `schemes` array.
2. Add the objects from `windows-terminal/cool-retro-frame-amber.profile.jsonc` and `windows-terminal/cool-retro-frame-readable.profile.jsonc` into `profiles.list`.
3. In both profiles, replace `experimental.pixelShaderPath` with your real shader paths, for example:

```jsonc
"experimental.pixelShaderPath": "C:\\Users\\you\\AppData\\Local\\WindowsTerminalShaders\\cool-retro-frame-amber.hlsl"
```

```jsonc
"experimental.pixelShaderPath": "C:\\Users\\you\\AppData\\Local\\WindowsTerminalShaders\\cool-retro-frame-readable.hlsl"
```

Optional: add the entries from `windows-terminal/keybindings.jsonc` into the top-level `keybindings` or `actions` array, depending on your Windows Terminal settings schema.

This step creates two new Windows Terminal PowerShell profiles. `experimental.pixelShaderPath` points to the HLSL file for the CRT frame, scanlines, glow, and amber color remapping; `colorScheme` points to the palette; `commandline` points to Windows PowerShell. This configures Windows Terminal profiles, not the PowerShell `$PROFILE` startup script.

The Amber profile uses:

```jsonc
{
  "antialiasingMode": "aliased",
  "colorScheme": "Cool Retro Amber",
  "cursorShape": "filledBox",
  "experimental.retroTerminalEffect": false,
  "font": {
    "builtinGlyphs": true,
    "size": 16
  },
  "opacity": 100,
  "useAcrylic": false
}
```

## Generate a colored banner hero from an image

This repo includes a small converter inspired by
[`cocktailpeanut/hermes-mod`](https://github.com/cocktailpeanut/hermes-mod)'s
braille image renderer. It maps each 2x4 image pixel block into one Unicode
braille character, then wraps that character in Rich foreground color markup
sampled from the source image. The terminal can only apply one foreground color
to one braille character, so color is accurate at the 2x4 braille-cell level,
not independently for all 8 sub-dots inside the same character.

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Generate a YAML `banner_hero` block:

```powershell
python .\scripts\image_to_rich_braille.py `
  "C:\path\to\eva-head.png" `
  --width 44 `
  --format yaml `
  --output ".\screenshots\eva-head-banner-hero.yaml"
```

For GIF inputs, render a specific frame with `--frame`:

```powershell
python .\scripts\image_to_rich_braille.py `
  "C:\path\to\eva-heads.gif" `
  --frame 2 `
  --width 44 `
  --output ".\screenshots\eva-02-banner-hero.yaml"
```

For low-color pixel art with a flat background, use the pixel-art fidelity
mode. A 100 px wide source maps cleanly to `--width 50`, because each braille
character represents a 2x4 pixel block:

```powershell
python .\scripts\image_to_rich_braille.py `
  "C:\path\to\eva-pixel-art.png" `
  --dot-mode pixel-art `
  --width 50 `
  --bg-color "#14171c" `
  --bg-tolerance 28 `
  --output ".\screenshots\eva-pixel-art-banner-hero.yaml"
```

For white-background pixel art, set the background explicitly to white. White
and near-white pixels are treated as blank, while black outlines are rendered
with the terminal's default foreground:

```powershell
python .\scripts\image_to_rich_braille.py `
  "C:\path\to\eva-white-bg.png" `
  --dot-mode pixel-art `
  --width 50 `
  --bg-color "#ffffff" `
  --bg-tolerance 28 `
  --output ".\screenshots\eva-white-bg-banner-hero.yaml"
```

The default foreground mask detects transparent images automatically. For
opaque images, it treats the most common border color as the background. If the
image background is known, pass it explicitly:

```powershell
python .\scripts\image_to_rich_braille.py `
  "C:\path\to\eva-head.png" `
  --bg-color "#14171c" `
  --bg-tolerance 28 `
  --width 44
```

## Use the browser braille studio

Start a static server from the repo root:

```powershell
python -m http.server 4173 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:4173/tools/braille-studio.html
```

The page runs locally in the browser. Upload an image, tune width, contrast,
background tolerance, blank cutoff, coverage, sharpening, color strategy, and
minimum color luminance, then copy or download the generated `banner_hero`
YAML block. The `Sample` button loads a built-in test image for quick tuning.

## HLSL color mapping

`shaders/cool-retro-frame-amber.hlsl` does not preserve the original Windows Terminal RGB output directly. It first remaps the terminal frame into an amber CRT palette.

The central function is `ConvertWithChroma(sourceColor.rgb)`:

1. It calculates perceived brightness through `Luma()`:

```hlsl
dot(color, float3(0.21f, 0.72f, 0.04f))
```

Green has the largest weight, so brighter pixels with stronger green-channel contribution are treated as closer to glowing foreground text.

2. That brightness chooses the position between background and foreground:

```hlsl
return lerp(CRT_BACKGROUND_COLOR, foreground, saturate(grey));
```

Dark pixels move toward `CRT_BACKGROUND_COLOR`; bright pixels move toward `foreground`. The current background is the deep brown-orange `float3(0.150f, 0.075f, 0.012f)`, and the default phosphor text color is `CRT_FONT_COLOR = float3(1.000f, 0.620f, 0.105f)`.

3. `foreground` is not a completely fixed amber color. It keeps a small amount of the original hue:

```hlsl
float3 chromaForeground = sourceColor * CRT_FONT_COLOR / denom;
float3 foreground = lerp(CRT_FONT_COLOR, chromaForeground, CRT_CHROMA);
```

`CRT_CHROMA` is currently `0.20f`, so the result is roughly 80% unified amber and 20% original color variation. Normal text stays strongly amber, while colored banners, syntax highlighting, and UI blocks still keep some relative color separation.

The main shader pass then further processes the mapped color:

- `CRT_SCREEN_BRIGHTNESS` raises the mapped image to `1.3f`.
- `CRT_BLACK_FLOOR` sets a minimum dark level to avoid crushed black.
- `Blur()` samples nearby pixels, maps them through `ConvertWithChroma()` again, and adds glow.
- Radial red/blue edge sampling adds subtle chromatic aberration through `RGB_ABERRATION_STRENGTH`.
- The final pass adds scanlines, grain, refresh line, screen curvature, vignette, and the frame.

In short, the shader uses source luminance to place each pixel between a dark amber-brown background and an amber phosphor foreground, uses `CRT_CHROMA` to preserve a little source hue, then applies glow, black floor, aberration, and scanline effects to make it read like an amber CRT display.

## Troubleshooting

- The screen has normal colors but no CRT effect: check `experimental.pixelShaderPath`, then use `Shift+F10` if you installed the toggle keybinding.
- The banner is garbled or misaligned: install the recommended font family and make sure `skins/eva-02.yaml` was saved as UTF-8.
- Windows Terminal refuses to load settings: check for missing commas after adding objects to `schemes`, `profiles.list`, or `keybindings`.
- The shader is slow: disable the shader with `Shift+F10` or remove `experimental.pixelShaderPath` from the profile.

## Credits

This project is inspired by and intended to work well with:

- [cocktailpeanut/hermes-mod](https://github.com/cocktailpeanut/hermes-mod) - Hermes skin management and visual editing workflow.
- [Hammster/windows-terminal-shaders](https://github.com/Hammster/windows-terminal-shaders) - Windows Terminal shader effects used to achieve the retro CRT look.

See `THIRD_PARTY_NOTICES.md` for shader attribution notes.

# awesome-hermes-eva-skins

[English](../README.md) | 简体中文

面向 Hermes Agent 的 EVA 风格皮肤合集，配套 Windows Terminal 琥珀色 CRT 配置和像素着色器。

本仓库只分发可复用的主题资产，不包含完整的本机 Windows Terminal `settings.json`，也不包含完整的 Hermes home 目录。那些文件通常会包含机器相关路径、profile ID、会话、缓存和认证信息。

## 包含内容

- `skins/eva-00.yaml`、`skins/eva-01.yaml`、`skins/eva-02.yaml` - Hermes CLI 皮肤。
- `tools/braille-studio.html` - 用于图片转彩色 braille 的浏览器界面。
- `fonts/ark-pixel-font-12px-monospaced-ttf-v2026.05.07/` - Windows Terminal profile 使用的 Ark Pixel 字体文件。
- `shaders/cool-retro-frame-amber.hlsl` - Windows Terminal 琥珀色 CRT 像素着色器。
- `windows-terminal/cool-retro-amber.scheme.jsonc` - Windows Terminal 配色片段。
- `windows-terminal/cool-retro-frame-amber.profile.jsonc` - Windows Terminal profile 片段。
- `windows-terminal/keybindings.jsonc` - 可选的 shader/focus 快捷键片段。

## 环境要求

- Hermes Agent 0.16.0 或更新版本。
- 支持 `experimental.pixelShaderPath` 的 Windows Terminal。
- 本地安装仓库内置的 Ark Pixel 字体。Windows Terminal profile 使用 `Ark Pixel 12px Mono zh_cn`、`Ark Pixel 12px Mono ja`、`Ark Pixel 12px Mono ko` 和 `Ark Pixel 12px Mono latin`。
- 使用 UTF-8 编辑文件。不要把 YAML 保存为 ANSI/GBK。

## 安装字体

导入 Windows Terminal profile 前，先安装仓库内置的 Ark Pixel 字体。profile 需要以下精确字体 family 名称：

```text
Ark Pixel 12px Mono zh_cn
Ark Pixel 12px Mono ja
Ark Pixel 12px Mono ko
Ark Pixel 12px Mono latin
```

Windows 图形界面安装：

1. 打开 `fonts/ark-pixel-font-12px-monospaced-ttf-v2026.05.07/`。
2. 选中四个 `.ttf` 文件。
3. 右键选择 `Install` 或 `Install for all users`。
4. 重启 Windows Terminal。

PowerShell 当前用户安装：

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

如果 banner 显示成方块、回退成普通等宽字体，或者 ASCII art 明显错位，通常是字体未安装，或 Windows Terminal 还没有重启。

## 安装 Hermes 皮肤

克隆本仓库，然后把皮肤复制到 Hermes 皮肤目录：

```powershell
git clone https://github.com/Chael-Chael/awesome-hermes-eva-skins.git
cd awesome-hermes-eva-skins

New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\hermes\skins"
Copy-Item ".\skins\eva-02.yaml" "$env:LOCALAPPDATA\hermes\skins\eva-02.yaml"
```

启动 Hermes 并切换皮肤：

```text
hermes
/skin eva-02
```

如果不想使用交互命令，也可以直接持久化配置：

```powershell
hermes config set display.skin eva-02
```

Hermes 也支持 `HERMES_HOME`。如果你使用自定义 Hermes home，请把 YAML 复制到：

```text
%HERMES_HOME%\skins\eva-02.yaml
```

## 从图片生成彩色 banner hero

本仓库包含一个小转换器，灵感来自 [`cocktailpeanut/hermes-mod`](https://github.com/cocktailpeanut/hermes-mod) 的 braille 图片渲染器。它会把每个 2x4 图像像素块映射为一个 Unicode braille 字符，然后根据源图像采样到的颜色，把该字符包进 Rich 前景色标记。终端只能给一个 braille 字符应用一个前景色，因此颜色精度是 2x4 braille cell 级别，而不是同一个字符内 8 个子点分别独立上色。

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

生成 YAML `banner_hero` block：

```powershell
python .\scripts\image_to_rich_braille.py `
  "C:\path\to\eva-head.png" `
  --width 44 `
  --format yaml `
  --output ".\screenshots\eva-head-banner-hero.yaml"
```

对于 GIF 输入，可以用 `--frame` 渲染指定帧：

```powershell
python .\scripts\image_to_rich_braille.py `
  "C:\path\to\eva-heads.gif" `
  --frame 2 `
  --width 44 `
  --output ".\screenshots\eva-02-banner-hero.yaml"
```

对于低色彩像素画和纯色背景图，使用 pixel-art 保真模式。100 px 宽的源图可以干净映射到 `--width 50`，因为每个 braille 字符代表一个 2x4 像素块：

```powershell
python .\scripts\image_to_rich_braille.py `
  "C:\path\to\eva-pixel-art.png" `
  --dot-mode pixel-art `
  --width 50 `
  --bg-color "#14171c" `
  --bg-tolerance 28 `
  --output ".\screenshots\eva-pixel-art-banner-hero.yaml"
```

对于白底像素画，请显式把背景设为白色。白色和近白色像素会被视为空白，黑色轮廓会用终端默认前景色渲染：

```powershell
python .\scripts\image_to_rich_braille.py `
  "C:\path\to\eva-white-bg.png" `
  --dot-mode pixel-art `
  --width 50 `
  --bg-color "#ffffff" `
  --bg-tolerance 28 `
  --output ".\screenshots\eva-white-bg-banner-hero.yaml"
```

默认前景 mask 会自动检测透明图片。对于不透明图片，它会把边缘最常见颜色视为背景。如果你知道图片背景色，建议显式传入：

```powershell
python .\scripts\image_to_rich_braille.py `
  "C:\path\to\eva-head.png" `
  --bg-color "#14171c" `
  --bg-tolerance 28 `
  --width 44
```

## 使用浏览器 braille studio

从仓库根目录启动静态服务器：

```powershell
python -m http.server 4173 --bind 127.0.0.1
```

打开：

```text
http://127.0.0.1:4173/tools/braille-studio.html
```

这个页面完全在本地浏览器运行。上传图片后，可以调节宽度、对比度、背景容差、空白截断、覆盖率、锐化、颜色策略和最低颜色亮度，然后复制或下载生成的 `banner_hero` YAML block。`Sample` 按钮会加载内置测试图，方便快速调参。

## 安装 Windows Terminal 视觉效果

把 shader 复制到稳定的本地目录：

```powershell
$shaderDir = "$env:LOCALAPPDATA\WindowsTerminalShaders"
New-Item -ItemType Directory -Force $shaderDir
Copy-Item ".\shaders\cool-retro-frame-amber.hlsl" "$shaderDir\cool-retro-frame-amber.hlsl"
```

打开 Windows Terminal settings JSON：

1. 打开 Windows Terminal。
2. 按 `Ctrl+,`。
3. 点击 `Open JSON file`。

然后编辑三个部分：

1. 把 `windows-terminal/cool-retro-amber.scheme.jsonc` 中的对象加入顶层 `schemes` 数组。
2. 把 `windows-terminal/cool-retro-frame-amber.profile.jsonc` 中的对象加入 `profiles.list`。
3. 在该 profile 中，把 `experimental.pixelShaderPath` 替换为你的真实 shader 路径，例如：

```jsonc
"experimental.pixelShaderPath": "C:\\Users\\you\\AppData\\Local\\WindowsTerminalShaders\\cool-retro-frame-amber.hlsl"
```

可选：根据你的 Windows Terminal settings schema，把 `windows-terminal/keybindings.jsonc` 中的条目加入顶层 `keybindings` 或 `actions` 数组。

原始 profile 使用：

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

## 故障排查

- 屏幕颜色正常但没有 CRT 效果：检查 `experimental.pixelShaderPath`，如果安装了快捷键，也可以按 `Shift+F10` 切换 shader。
- banner 乱码或错位：安装推荐字体，并确认 `skins/eva-02.yaml` 保存为 UTF-8。
- Windows Terminal 无法加载 settings：检查向 `schemes`、`profiles.list` 或 `keybindings` 添加对象后是否缺少逗号。
- shader 太慢：按 `Shift+F10` 关闭 shader，或者从 profile 中移除 `experimental.pixelShaderPath`。

## 致谢

本项目受以下项目启发，并旨在与它们良好配合：

- [cocktailpeanut/hermes-mod](https://github.com/cocktailpeanut/hermes-mod) - Hermes 皮肤管理和视觉编辑工作流。
- [Hammster/windows-terminal-shaders](https://github.com/Hammster/windows-terminal-shaders) - 用于实现复古 CRT 视觉的 Windows Terminal shader 效果。

shader 归属说明见 `THIRD_PARTY_NOTICES.md`。

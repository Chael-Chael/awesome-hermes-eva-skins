// Based on Microsoft Terminal samples/PixelShaders/Retro.hlsl.
// Full-screen CRT glow with amber phosphor, grain, blacklevel, and a subtle frame.

Texture2D shaderTexture;
SamplerState samplerState;

cbuffer PixelShaderSettings
{
    float Time;
    float Scale;
    float2 Resolution;
    float4 Background;
};

#define SCANLINE_FACTOR 0.26f
#define SCALED_SCANLINE_PERIOD Scale
#define SCALED_GAUSSIAN_SIGMA (2.0f * Scale)
#define GLOW_STRENGTH 0.40f
#define ENABLE_GRAIN 1
#define GRAIN_INTENSITY 0.012f
#define ENABLE_BLACKLEVEL 1
#define REFRESHLINE_STRENGTH 0.028f
#define CURVE_INTENSITY 0.55f
#define RGB_SHIFT 0.42f
#define RGB_ABERRATION_STRENGTH 0.35f
#define PIXEL_SNAP 0
#define PIXEL_BLOCK_SIZE 1.0f
#define CRT_FONT_COLOR float3(1.000f, 0.620f, 0.105f)
// #define CRT_BACKGROUND_COLOR float3(0.043f, 0.030f, 0.010f)
#define CRT_BACKGROUND_COLOR float3(0.150f, 0.075f, 0.012f)
#define CRT_CHROMA 0.20f
#define CRT_SCREEN_BRIGHTNESS 1.3f
#define CRT_BLACK_FLOOR float3(0.055f, 0.038f, 0.013f)
#define OVERSCAN_PERCENTAGE 0.018f
#define FRAME_COLOR float3(0.030f, 0.026f, 0.020f)
#define BEZEL_COLOR float3(0.075f, 0.060f, 0.043f)
#define FRAME_HIGHLIGHT float3(0.24f, 0.20f, 0.15f)
#define VIGNETTE_STRENGTH 0.48f
#define PHOSPHOR_HOT_GLOW 0.18f

static const float M_PI = 3.14159265f;

float Gaussian2D(float x, float y, float sigma)
{
    return 1 / (sigma * sqrt(2 * M_PI)) * exp(-0.5f * (x * x + y * y) / sigma / sigma);
}

float4 Blur(float2 texCoord, float sigma)
{
    float width;
    float height;
    shaderTexture.GetDimensions(width, height);

    float texelWidth = 1.0f / width;
    float texelHeight = 1.0f / height;

    float4 color = float4(0, 0, 0, 0);
    const float sampleCount = 13;

    for (float x = 0; x < sampleCount; x++)
    {
        float2 samplePos = float2(0, 0);
        samplePos.x = texCoord.x + (x - sampleCount / 2.0f) * texelWidth;

        for (float y = 0; y < sampleCount; y++)
        {
            samplePos.y = texCoord.y + (y - sampleCount / 2.0f) * texelHeight;
            color += shaderTexture.Sample(samplerState, samplePos) * Gaussian2D(x - sampleCount / 2.0f, y - sampleCount / 2.0f, sigma);
        }
    }

    return color;
}

float SquareWave(float y)
{
    return 1.0f - (floor(y / SCALED_SCANLINE_PERIOD) % 2.0f) * SCANLINE_FACTOR;
}

float4 Scanline(float4 color, float4 pos)
{
    return color * SquareWave(pos.y);
}

float Hash(float2 p)
{
    return frac(sin(dot(p, float2(12.9898f, 78.233f)) + Time * 31.17f) * 43758.5453f);
}

float Luma(float3 color)
{
    return dot(color, float3(0.21f, 0.72f, 0.04f));
}

float3 ConvertWithChroma(float3 sourceColor)
{
    float grey = Luma(sourceColor);
    float denom = max(grey, 0.0001f);
    float3 chromaForeground = sourceColor * CRT_FONT_COLOR / denom;
    float3 foreground = lerp(CRT_FONT_COLOR, chromaForeground, CRT_CHROMA);
    return lerp(CRT_BACKGROUND_COLOR, foreground, saturate(grey));
}

float2 PixelSnap(float2 uv)
{
#if PIXEL_SNAP
    float2 pixel = max(Resolution.xy / PIXEL_BLOCK_SIZE, float2(1.0f, 1.0f));
    return (floor(uv * pixel) + 0.5f) / pixel;
#else
    return uv;
#endif
}

float2 Curve(float2 tex)
{
    tex -= 0.5f;
    float radius = dot(tex, tex) * CURVE_INTENSITY;
    tex *= 4.2f + radius;
    tex *= 0.25f;
    tex += 0.5f;
    return tex;
}

float4 Frame(float2 tex, float2 curvedTex, float4 color)
{
    if (curvedTex.x < -0.025f || curvedTex.y < -0.025f || curvedTex.x > 1.025f || curvedTex.y > 1.025f)
    {
        return float4(0, 0, 0, 1);
    }

    if (curvedTex.x < -0.015f || curvedTex.y < -0.015f || curvedTex.x > 1.015f || curvedTex.y > 1.015f)
    {
        float edgeLight = smoothstep(-0.025f, -0.015f, min(min(curvedTex.x, curvedTex.y), min(1.025f - curvedTex.x, 1.025f - curvedTex.y)));
        return float4(lerp(FRAME_COLOR, BEZEL_COLOR, edgeLight), 1);
    }

    if (curvedTex.x < -0.001f || curvedTex.y < -0.001f || curvedTex.x > 1.001f || curvedTex.y > 1.001f)
    {
        return float4(0, 0, 0, 1);
    }

    float edge = min(min(curvedTex.x, 1.0f - curvedTex.x), min(curvedTex.y, 1.0f - curvedTex.y));
    float innerShadow = 1.0f - smoothstep(0.000f, 0.075f, edge);
    float topShadow = 1.0f - smoothstep(0.03f, 0.18f, tex.y);
    float bottomShadow = smoothstep(0.80f, 1.0f, tex.y);
    float topLight = innerShadow * smoothstep(0.0f, 0.55f, 1.0f - tex.y);
    float2 centered = tex - 0.5f;
    float vignette = smoothstep(0.18f, 0.78f, dot(centered, centered) * 2.2f);

    color.rgb *= 1.0f - vignette * VIGNETTE_STRENGTH;
    color.rgb *= 1.0f - innerShadow * 0.34f;
    color.rgb *= 1.0f - topShadow * 0.20f;
    color.rgb *= 1.0f - bottomShadow * 0.18f;
    color.rgb += FRAME_HIGHLIGHT * topLight * 0.08f;
    return color;
}

float4 main(float4 pos : SV_POSITION, float2 tex : TEXCOORD) : SV_TARGET
{
    float2 curvedTex = Curve(tex);

    float2 sampleTex = curvedTex;
    sampleTex -= 0.5f;
    sampleTex *= 1.0f / (1.0f - OVERSCAN_PERCENTAGE);
    sampleTex += 0.5f;
    sampleTex = PixelSnap(sampleTex);

    float4 sourceColor = float4(0, 0, 0, 1);
    if (sampleTex.x >= 0.0f && sampleTex.y >= 0.0f && sampleTex.x <= 1.0f && sampleTex.y <= 1.0f)
    {
        sourceColor = shaderTexture.Sample(samplerState, sampleTex);
    }

    float4 color = float4(ConvertWithChroma(sourceColor.rgb) * CRT_SCREEN_BRIGHTNESS, 1);
    if (sampleTex.x >= 0.0f && sampleTex.y >= 0.0f && sampleTex.x <= 1.0f && sampleTex.y <= 1.0f)
    {
        float2 centerDir = normalize((tex - 0.5f) + float2(0.0001f, 0.0001f));
        float2 rgbOffset = centerDir * RGB_SHIFT / Resolution.xy;
        float3 sourceRed = shaderTexture.Sample(samplerState, saturate(sampleTex + rgbOffset)).rgb;
        float3 sourceBlue = shaderTexture.Sample(samplerState, saturate(sampleTex - rgbOffset)).rgb;
        float sourceCenterLuma = Luma(sourceColor.rgb);
        float redEdge = max(0.0f, Luma(sourceRed) - sourceCenterLuma);
        float blueEdge = max(0.0f, Luma(sourceBlue) - sourceCenterLuma);
        color.rgb += float3(redEdge, 0.0f, blueEdge) * RGB_ABERRATION_STRENGTH;
    }
#if ENABLE_BLACKLEVEL
    color.rgb = max(color.rgb, CRT_BLACK_FLOOR);
#endif

    // This is the important part from the official Retro.hlsl: blur the terminal
    // texture itself and add it back, creating text glow without any color conversion.
    if (sampleTex.x >= 0.0f && sampleTex.y >= 0.0f && sampleTex.x <= 1.0f && sampleTex.y <= 1.0f)
    {
        float4 glowSource = Blur(sampleTex, SCALED_GAUSSIAN_SIGMA);
        color.rgb += ConvertWithChroma(glowSource.rgb) * GLOW_STRENGTH * saturate(Luma(glowSource.rgb) * 1.7f);

        float hotMask = smoothstep(0.72f, 0.98f, Luma(sourceColor.rgb));
        float2 hotOffset = float2(2.0f / Resolution.x, 0.0f);
        float hotTrail = max(Luma(shaderTexture.Sample(samplerState, sampleTex - hotOffset).rgb),
                             Luma(shaderTexture.Sample(samplerState, sampleTex + hotOffset).rgb));
        color.rgb += CRT_FONT_COLOR * hotMask * hotTrail * PHOSPHOR_HOT_GLOW;
    }

    float refresh = smoothstep(0.025f, 0.0f, abs(sampleTex.y - frac(Time / 5.0f)));
    color.rgb += refresh * REFRESHLINE_STRENGTH;

#if ENABLE_GRAIN
    float grain = Hash(tex * Resolution.xy) - 0.5f;
    color.rgb += grain * GRAIN_INTENSITY;
#endif

    color = Scanline(color, pos);
    color = Frame(tex, curvedTex, color);
    color.a = 1.0f;

    return saturate(color);
}

---
name: poster-video-from-audio
slug: poster-video-from-audio
display_name: "海报口播视频 · 海报+音频合成带字幕竖屏视频"
displayName: "海报口播视频 · 海报+音频合成带字幕竖屏视频"
description: 把一张背景图/海报 + 一段音频合成为带烧录字幕的竖屏视频（1080×1920）。适用于海报已自带大标题、系列名、作者署名，只需把口播内容烧成字幕的场景（如搬运 X/Twitter 知名 IP 播客内容做成的系列短视频）。支持 8~30 分钟长音频，内置 whisper.cpp ASR、繁转简、ASR 错词批量修正、开头品牌口播裁剪、jieba 分词折行、ffmpeg 渲染与抽帧验证。触发词：背景图+音频合成视频、海报视频、烧字幕、做第 N 期、口播视频。
agent_created: true
version: 1.0.0
category: productivity
emoji: "🎬"
author: jiaxinmmhh
platforms:
  - WorkBuddy
  - QClaw
  - ima
  - Claude Code
  - Cursor
---

# Poster Video From Audio（海报 + 口播 → 烧字幕竖屏视频）

## Overview

输入一张海报（自带标题）和一段口播音频，输出可直接上传的 9:16 mp4：
字幕由 whisper.cpp 从音频识别、人工校对后烧进画面（drawtext，非软字幕），
开头品牌口播按时间戳裁掉，音频同步裁剪。

**与 `short-video-from-audio` 的分工**（别选错）：
| | 本 skill | short-video-from-audio |
|---|---|---|
| 标题 | **不叠加**，海报自带 | 用 drawtext 叠加黄色标题块 |
| 输入 | 海报 + 音频 | 图片 + 音频 + 标题文案 |
| 典型时长 | 8~30 min | 短视频 |
| 额外步骤 | ASR 校对、品牌口播裁剪 | — |

## When to use

- 「@音频 @海报 做第 N 期」这类系列化口播视频
- 海报已经排版好标题，只需要把说的内容烧上去
- 任何「单图 + 长音频 + 要字幕」的场景

## Workflow

### Step 1 — 验素材 + 转码 + ASR + 转简（脚本化）

```bash
zsh <skill>/scripts/prep.sh "/path/音频.wav" /Users/jx/Downloads/xip-epNN
```

脚本依次做：ffprobe 验时长（<60s 直接判为传输截断并停止，见坑位 1）→
复制为 `audio_full.wav` → 转 16k 单声道 → whisper ASR → 备份 `subs.raw.srt`
→ opencc 繁转简。

> 音频 >10 min 时 ASR 要几分钟，把 prep.sh 放后台跑（27min 约 4.5 分钟）。

### Step 2 — 通读字幕，确定裁剪点 SHIFT

读 `subs.srt`，找**正式内容起点**：
- 开头品牌口播要整段裁掉（典型：「欢迎收听 XX AI 播客节目」，
  有时还带一句「哈喽大家好欢迎收听我们的播客」，两截都在品牌口播内）
- SHIFT = 正式内容第一段的起始时间戳（不是品牌段的结束时间，
  这样中间的静音/片头音乐间隙也一起裁掉，正片从 0s 开始）
- 结尾水印段（「字幕by索兰娅」等）若存在，按段落过滤删除

⚠️ 品牌口播长度每期不同（已见 4.1s / 7.2s / 9.8s 三种），必须逐期看 SRT 定，
不要沿用上期数值。

### Step 3 — 整理错词到 fixes.txt

通读全文，把同音错写成 `错词=>正确词` 一行一条：

```
读哪一年=>赌哪一年
艺人公司=>一人公司
天方液弹=>天方夜谭
```

三条硬规则见坑位 3/4/5：**必须简体**、**歧义词用长串定向替换**、
**经历/精力逐条判断**。

### Step 4 — 修错词 + 裁剪（脚本化）

```bash
unset PYTHONPATH   # 必须！否则 python 被 shim 拖死（exit 137）
/Users/jx/.workbuddy/binaries/python/envs/default/bin/python \
  <skill>/scripts/srt_fix_trim.py subs.srt fixes.txt 7.100
```

原地修正 `subs.srt`，并生成 `subs_trim.srt`（时间戳 -SHIFT、丢弃品牌段）。
每条修复会打印命中次数，**未命中会 WARN** —— 看到 WARN 说明写错或已转简失效。

### Step 5~9 — 裁音频、字幕链、渲染、抽帧（脚本化）

```bash
cd /Users/jx/Downloads/xip-epNN
zsh <skill>/scripts/build.sh 7.100
```

**build.sh 必须 run_in_background**：8min 片渲染约 6 分钟、27min 片约 10+ 分钟，
前台 Bash 默认 2 分钟上限会被 SIGTERM（症状 exit 137）。
脚本末尾自动抽 `chk_early/mid/end.jpg` 三帧。

## 输出规格

- 画布 1080×1920 / 30fps / libx264 -crf 22 -preset medium / aac 192k / +faststart
- 字幕：白字 + 黑描边 + 半透明黑底，块下沿固定 `y=1500`（中下区，避开平台进度条），
  每行 ≤13 字按 jieba 分词折行，字号按行数自适应 68→48

## Resources

### scripts/

- `prep.sh` — 阶段一：验时长 → 转码 → ASR → 繁转简
- `srt_fix_trim.py` — 阶段二：批量修错词 + 按 SHIFT 裁剪时间戳（带未命中告警）
- `t2s.py` — SRT 整文件繁转简（opencc python 包）
- `build.sh` — 阶段二：修错词 → 裁音频 → 字幕链 → 渲染 → 抽帧
- `srt2drawtext.py` — SRT → 逐段 drawtext 链（jieba 折行、边界帧防叠）

### references/

- `notes.md` — 30 期实战坑位清单与已见错词表。**动手前先看第 1、3、4、5、7 条。**

# Poster Video From Audio · 海报口播视频

把**一张海报** + **一段口播音频**，合成**带烧录字幕的竖屏视频**（1080×1920）——海报已经排版好标题，AI 只负责把说的内容烧上去。

### 15 秒速览
- **这是什么**：一条「海报 + 口播 → 成片」的完整流水线，内置 ASR、繁转简、错词批量修正、片头品牌口播裁剪、字幕烧录、抽帧验证。
- **给谁用**：搬运播客 / 口播内容做系列短视频的自媒体人、一人公司；任何要把长音频配一张图发竖屏视频的场景。
- **解决什么痛点**：手动对字幕最耗时的三件事它都接管了——听写（whisper.cpp）、听写错字批量修（fixes.txt 一张表搞定）、字幕烧录（drawtext，macOS 下不出现豆腐块）。
- **实测规模**：已跑通 30 期（ep01~ep30），单期 8~28 分钟。

## 一句话介绍

**海报已经好看，剩下的是把话烧上去。**

## 安装

```bash
# WorkBuddy / QClaw / OpenClaw 用户
skillhub install poster-video-from-audio

# 或从 ClawHub
clawhub install jiaxinmmhh/poster-video-from-audio
```

## 使用方式

整条管线三步，前两步是脚本，中间一步需要人通读（这一步没法自动化）：

```bash
# ① 验时长 → 转码 → ASR → 繁转简
zsh scripts/prep.sh "/path/音频.wav" /Users/jx/Downloads/xip-epNN

# ② 人工通读 subs.srt，确定裁剪点 SHIFT，整理错词到 fixes.txt
#    fixes.txt 每行一条：错词=>正确词

# ③ 修错词+裁剪 → 裁音频 → 字幕链 → 渲染 → 抽帧（必须后台跑）
cd /Users/jx/Downloads/xip-epNN
zsh scripts/build.sh 7.100
```

产出 `output.mp4` + 三张验证帧 `chk_early/mid/end.jpg`。

## 与 short-video-from-audio 的区别

别选错：

| | 本 Skill | short-video-from-audio |
|---|---|---|
| 标题 | **不叠加**，海报自带 | 用 drawtext 叠加黄色标题块 |
| 输入 | 海报 + 音频 | 图片 + 音频 + 标题文案 |
| 典型时长 | 8~30 min | 短视频 |
| 额外步骤 | ASR 校对、品牌口播裁剪 | — |

## 目录结构

```
poster-video-from-audio/
├── SKILL.md                 # 主流程
├── README.md
├── LICENSE
├── references/notes.md      # 30 期坑位清单 + 已见错词表（动手前先读）
└── scripts/
    ├── prep.sh              # 阶段一：验时长 → 转码 → ASR → 转简
    ├── t2s.py               # SRT 繁转简（opencc python 包）
    ├── srt_fix_trim.py      # 阶段二：批量修错词 + 按 SHIFT 裁剪（带未命中告警）
    ├── build.sh             # 阶段二：裁音频 → 字幕链 → 渲染 → 抽帧
    └── srt2drawtext.py      # SRT → 逐段 drawtext 链（jieba 折行）
```

## 环境依赖

- `ffmpeg` / `ffprobe`（本机 `~/.local/bin/`，4.4）
- `whisper-cli` + `~/models/ggml-small.bin`（whisper.cpp）
- Python venv `/Users/jx/.workbuddy/binaries/python/envs/default`（含 opencc、jieba）
- 字体 `/System/Library/Fonts/STHeiti Medium.ttc`

## 坑位速记

1. 收到音频**先 ffprobe 验时长**，<60s 基本是传输截断
2. opencc 命令行已失效，用 venv 里的 python 包
3. 修错词的替换对**必须写简体**（转简之后才匹配得上）
4. 歧义词用**长串定向替换**，别全局替换（「亲戚」可能一合法一错）
5. 经历 / 精力混淆**方向不定**，逐条按句意判断
6. **渲染一律后台跑**——8 分钟片也会撞前台 2 分钟上限，症状 exit 137

完整 11 条见 `references/notes.md`。

## License

MIT

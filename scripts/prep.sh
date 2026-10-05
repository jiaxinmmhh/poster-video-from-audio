#!/bin/zsh
# 阶段一：素材校验 → 16k 转码 → whisper ASR → opencc 繁转简
# 用法: zsh prep.sh <音频文件> <项目目录>
# 例:   zsh prep.sh "/Users/jx/Downloads/xxx.wav" /Users/jx/Downloads/xip-ep31
set -e

AUDIO="$1"
DIR="$2"
PY=/Users/jx/.workbuddy/binaries/python/envs/default/bin/python

[[ -f "$AUDIO" ]] || { echo "❌ 音频不存在: $AUDIO"; exit 1; }
[[ -n "$DIR" ]] || { echo "❌ 缺项目目录参数"; exit 1; }

mkdir -p "$DIR"
cd "$DIR"

# Step 0 — 入口必做：验时长（<60s 基本是传输截断，直接退回要源文件）
DUR=$(~/.local/bin/ffprobe -v error -show_entries format=duration -of csv=p=0 "$AUDIO")
echo "时长: ${DUR}s"
if (( $(echo "$DUR < 60" | bc -l) )); then
  echo "❌ 时长 <60s，疑似传输截断，请重新获取完整音频"
  exit 1
fi

cp "$AUDIO" audio_full.wav
echo "-> audio_full.wav"

# Step 1 — 转 16k 单声道（whisper 要求）
~/.local/bin/ffmpeg -y -i audio_full.wav -ar 16000 -ac 1 audio.wav 2>&1 | tail -1
echo "-> audio.wav"

# Step 2 — ASR（长音频建议后台跑：27min 约 4.5 分钟）
~/.local/bin/whisper-cli -m ~/models/ggml-small.bin -l zh \
  --entropy-thold 1.5 --max-context 0 \
  -f audio.wav -osrt -of subs
cp subs.srt subs.raw.srt
echo "-> subs.srt (raw 备份 subs.raw.srt)"

# Step 3 — 繁转简（opencc CLI 本机已失效，必须用 venv 里的 python 包）
unset PYTHONPATH
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
$PY "$SCRIPTS/t2s.py" subs.srt

echo "=== 阶段一完成 ==="
echo "下一步：通读 subs.srt 找品牌口播裁剪点 + 整理错词到 fixes.txt，再跑 build.sh"
grep -cE '^$' subs.srt | xargs echo "字幕段数:"

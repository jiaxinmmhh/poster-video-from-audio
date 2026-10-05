#!/bin/zsh
# 阶段二：修错词+裁剪 → 字幕链 → 渲染 → 抽帧验证
# 用法: 在项目目录内执行  zsh build.sh <SHIFT> [期号标题]
# 例:   cd xip-ep31 && zsh /path/build.sh 7.100
# ⚠️ 含渲染，必须 run_in_background（8min 片约 6 分钟，27min 片约 10+ 分钟，
#    前台 Bash 默认 2 分钟上限会被 SIGTERM 掉，症状 exit 137）
set -e

SHIFT="${1:-0}"
PY=/Users/jx/.workbuddy/binaries/python/envs/default/bin/python
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"

cd "$(pwd)"

# Step 4 — 修错词 + 裁剪时间戳（fixes.txt 由人工通读后填写）
[[ -f fixes.txt ]] || { echo "❌ 缺 fixes.txt（每行: 错词=>正确词）"; exit 1; }
unset PYTHONPATH
$PY "$SCRIPTS/srt_fix_trim.py" subs.srt fixes.txt "$SHIFT"

# Step 5 — 按 SHIFT 裁音频
~/.local/bin/ffmpeg -y -ss "$SHIFT" -i audio_full.wav \
  -ar 16000 -ac 1 -c:a pcm_s16le audio_trim.wav 2>&1 | tail -1
DURATION=$(~/.local/bin/ffprobe -v error -show_entries format=duration -of csv=p=0 audio_trim.wav)
echo "-> audio_trim.wav (${DURATION}s)"

# Step 6 — SRT → drawtext 链（必用带 jieba 的 venv，否则静默回退硬切拆词）
$PY "$SCRIPTS/srt2drawtext.py" subs_trim.srt 0 > drawtext_chain.txt
grep -c 'drawtext=' drawtext_chain.txt | xargs echo "-> 字幕链条数:"

# Step 7 — 残留检查（品牌词/水印/错词不应出现在可渲染文件里）
if grep -qE '豆包|播客节目|字幕by|字幕製作|索兰娅|J Chong|貝爾' subs_trim.srt; then
  echo "⚠️ 仍有品牌词/水印残留，请检查裁剪点与过滤"
  grep -nE '豆包|播客节目|字幕by|字幕製作|索兰娅|J Chong|貝爾' subs_trim.srt
fi

# Step 8 — 渲染（纯海报模式：不叠加任何标题块，只烧口播字幕）
SUB_CHAINS=$(paste -sd ',' drawtext_chain.txt)
~/.local/bin/ffmpeg -y \
  -loop 1 -framerate 30 -i bg.png \
  -i audio_trim.wav \
  -t "$DURATION" \
  -vf "scale=1080:1920,${SUB_CHAINS}" \
  -c:v libx264 -pix_fmt yuv420p -preset medium -crf 22 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  output.mp4

echo "=== DONE ==="
ls -la output.mp4

# Step 9 — 抽 3 帧验证（开头/中段/结尾）
MID=$(echo "$DURATION / 2" | bc)
END=$(echo "$DURATION - 4" | bc)
~/.local/bin/ffmpeg -y -ss 5 -i output.mp4 -frames:v 1 -q:v 2 chk_early.jpg 2>/dev/null
~/.local/bin/ffmpeg -y -ss "$MID" -i output.mp4 -frames:v 1 -q:v 2 chk_mid.jpg 2>/dev/null
~/.local/bin/ffmpeg -y -ss "$END" -i output.mp4 -frames:v 1 -q:v 2 chk_end.jpg 2>/dev/null
echo "-> chk_early.jpg chk_mid.jpg chk_end.jpg"

#!/usr/bin/env python3
"""把 srt 转成 ffmpeg drawtext 命令链。

支持:
  - 时间偏移 argv[2] (秒)，用于裁剪开头
  - 自动换行 (每行 ≤20 字，优先按空格/中文标点断行)
  - 自适应字号: 1/2/3/4/5 行分别 46/42/38/34/32 px
  - 多行堆叠: 字幕块下沿固定 y=1500 (中下区域，避开底部 UI)，向上堆叠
"""
import re
import sys


def parse_srt(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    text = text.replace("\r\n", "\n").lstrip("\ufeff")
    pat = re.compile(
        r"(\d+)\s*\n(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n([\s\S]*?)(?=\n\s*\n|\Z)"
    )
    segs = []
    for m in pat.finditer(text):
        h, mm, rest = m.group(2).replace(",", ".").split(":")
        st = int(h) * 3600 + int(mm) * 60 + float(rest)
        h, mm, rest = m.group(3).replace(",", ".").split(":")
        et = int(h) * 3600 + int(mm) * 60 + float(rest)
        txt = " ".join(m.group(4).split())
        if not txt:
            continue
        segs.append((st, et, txt))
    return segs


# 断行优先级：空格/中文标点 > 硬切
_BREAK_CHARS = " 　，。！？、；：…"


def _is_latin(ch):
    """连续的 ASCII 字母/数字视为一个不可拆的词（如 AI、ChatGPT、300383）。"""
    return ch.isascii() and ch.isalnum()


def wrap(text, max_chars):
    """把一段文字折成多行，每行 ≤max_chars。

    优先用 jieba 分词按词边界断行（不拆中文词、不拆英文词、不拆数字）；
    jieba 不可用时回退到旧逻辑（空格/中文标点 > 拉丁词保护 > 硬切）。
    行尾标点跟随其前的词，不会落到行首。
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    try:
        import jieba
        words = [w for w in jieba.cut(text) if w.strip()]
        lines = []
        cur = ''
        for w in words:
            if not cur:
                cur = w
            elif len(cur) + len(w) <= max_chars:
                cur += w
            elif re.fullmatch(r'[，。！？、；：…,.!?;:]', w):
                cur += w  # 标点贴行尾, 允许 +1 超宽
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines
    except ImportError:
        pass
    lines = []
    rest = text
    while len(rest) > max_chars:
        cut = max_chars
        best = -1
        # 从 cut 往前找最近的优先断点
        for i in range(cut, max(cut - 10, 0), -1):
            if i < len(rest) and rest[i] in _BREAK_CHARS:
                best = i + 1
                break
        if best == -1:
            best = cut
            # 硬切点若在拉丁词中间，回退到词首（最多回退 8 步保护极端长词）
            steps = 0
            while best > 0 and steps < 8 and _is_latin(rest[best - 1]) and _is_latin(rest[best]):
                best -= 1
                steps += 1
        lines.append(rest[:best].rstrip())
        rest = rest[best:].lstrip()
    if rest:
        lines.append(rest)
    return lines


def esc(s):
    """ffmpeg drawtext text 参数的转义。"""
    out = []
    for ch in s:
        if ch == "'":
            out.append("\\'")
        elif ch == "\\":
            out.append("\\\\")
        elif ch == ":":
            out.append("\\:")
        elif ch == "%":
            out.append("\\%")
        elif ch == ",":
            out.append("\\,")
        else:
            out.append(ch)
    return "".join(out)


def main():
    srt_path = sys.argv[1] if len(sys.argv) > 1 else "subs.srt"
    shift = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    segs = parse_srt(srt_path)
    print(f"# 共 {len(segs)} 段字幕, 偏移 {shift}s", file=sys.stderr)

    FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
    MAX_CHARS = 13
    Y_BOTTOM = 1500  # 字幕块下沿上移到中下区域，避免被底部进度条/操作栏挡住

    # 行数 -> 字号 (做大: 典型 2-3 行段字号 60-64, 块高约占 1/5)
    FS_MAP = {1: 68, 2: 64, 3: 60, 4: 56, 5: 52, 6: 48}

    chains = []
    dropped = 0
    for st, et, txt in segs:
        st -= shift
        et -= shift
        if et <= 0:
            dropped += 1
            continue
        if st < 0:
            st = 0.0
        lines = wrap(txt, MAX_CHARS)
        n = len(lines)
        fs = FS_MAP.get(n, 30)
        line_h = round(fs * 1.45)
        block_h = n * line_h
        block_top = Y_BOTTOM - block_h
        for i, line in enumerate(lines):
            y = block_top + i * line_h + 4
            t = esc(line)
            chain = (
                f"drawtext=fontfile='{FONT}'"
                f":text='{t}'"
                f":fontcolor=white:fontsize={fs}"
                f":borderw=3:bordercolor=black@0.85"
                f":box=1:boxcolor=black@0.6:boxborderw=12"
                f":x=(w-text_w)/2:y={y}"
                f":enable='between(t,{st:.3f},{max(et - 0.04, st + 0.05):.3f})'"
            )
            chains.append(chain)
    print(f"# 偏移后丢弃 {dropped} 段, 共输出 {len(chains)} 条 drawtext", file=sys.stderr)
    print("\n".join(chains))


if __name__ == "__main__":
    main()
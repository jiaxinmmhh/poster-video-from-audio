#!/usr/bin/env python3
"""修正 ASR 错词 + 按 shift 裁掉开头，一步产出可渲染的 subs_trim.srt。

用法:
  python3 srt_fix_trim.py subs.srt fixes.txt SHIFT

参数:
  subs.srt   whisper 输出（必须先经 opencc t2s 转简，否则 FIX 会匹配失效）
  fixes.txt  每行一条 "错词=>正确词"；# 开头为注释，空行跳过
             ⚠️ 必须写简体（opencc 转换后的形态），写繁体原文不会命中
  SHIFT      裁掉开头的秒数（品牌口播结束点 / 正式内容起点），0 表示不裁

输出:
  subs.srt       原地写回修正后的全文（保留，便于复查）
  subs_trim.srt  时间戳整体 -SHIFT、丢弃 SHIFT 之前段落的裁剪版

校验:
  每条 FIX 都会打印命中次数；未命中会 WARN，方便立刻发现写错/已转简失效。
  脚本退出码 0 表示全部命中（有 WARN 时仍返回 0，交由调用方看输出）。
"""

import sys


def ts2sec(ts):
    """00:01:02,340 -> 62.34"""
    h, m, rest = ts.strip().split(':')
    return int(h) * 3600 + int(m) * 60 + float(rest.replace(',', '.'))


def sec2ts(t):
    """62.34 -> 00:01:02,340"""
    t = max(0.0, t)
    h = int(t // 3600)
    t -= h * 3600
    m = int(t // 60)
    t -= m * 60
    return f"{h:02d}:{m:02d}:{t:06.3f}".replace('.', ',')


def load_fixes(path):
    pairs = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=>' not in line:
                print(f"WARN 跳过无 => 的行: {line}")
                continue
            a, b = line.split('=>', 1)
            pairs.append((a.strip(), b.strip()))
    return pairs


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    srt_path, fixes_path, shift = sys.argv[1], sys.argv[2], float(sys.argv[3])
    txt = open(srt_path, encoding='utf-8').read()

    pairs = load_fixes(fixes_path)
    miss = 0
    for a, b in pairs:
        n = txt.count(a)
        if n == 0:
            print(f"WARN 未命中: {a} => {b}")
            miss += 1
        txt = txt.replace(a, b)
    print(f"applied {len(pairs)} fixes, 未命中 {miss} 条")

    open(srt_path, 'w', encoding='utf-8').write(txt)

    # 裁剪 + 平移
    out, idx = [], 0
    for blk in txt.strip().split('\n\n'):
        lines = blk.split('\n')
        tline = next((l for l in lines if '-->' in l), None)
        if not tline:
            continue
        s, e = tline.split(' --> ')
        st, en = ts2sec(s), ts2sec(e)
        if en <= shift:
            continue  # 整段在裁剪点之前（品牌口播等），丢弃
        st2 = max(0.0, st - shift)
        en2 = en - shift
        idx += 1
        text = '\n'.join(lines[lines.index(tline) + 1:])
        out.append(f"{idx}\n{sec2ts(st2)} --> {sec2ts(en2)}\n{text}")

    trim_path = srt_path.replace('.srt', '_trim.srt')
    open(trim_path, 'w', encoding='utf-8').write('\n\n'.join(out) + '\n')
    print(f"-> {trim_path}: 保留 {idx} 段, shift={shift}s")


if __name__ == '__main__':
    main()

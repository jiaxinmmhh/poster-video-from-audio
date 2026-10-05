#!/usr/bin/env python3
"""SRT 繁转简（整文件）。

用法: python3 t2s.py subs.srt

为什么需要：whisper 加 --max-context 0 后输出可能是繁体中文；
且修错词的 FIX 替换对必须用简体才匹配得上，所以必须在修错词之前转简。
本机 opencc 命令行工具已失效，改用 venv 里的 opencc python 包。
"""
import sys

import opencc


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'subs.srt'
    cc = opencc.OpenCC('t2s')
    txt = open(path, encoding='utf-8').read()
    conv = cc.convert(txt)
    open(path, 'w', encoding='utf-8').write(conv)
    print(f"-> opencc t2s done ({len(conv)} chars)")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Count lines, words and characters of files (a tiny `wc`)."""
import argparse
import sys


def count_file(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return {"file": path, "lines": text.count("\n"), "words": len(text.split()), "chars": len(text)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("files", nargs="+")
    args = p.parse_args(argv)
    rows = [count_file(f) for f in args.files]
    for r in rows:
        print(f"{r['lines']:>8} {r['words']:>8} {r['chars']:>8} {r['file']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

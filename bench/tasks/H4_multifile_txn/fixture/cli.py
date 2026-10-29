#!/usr/bin/env python3
"""inventory CLI: add / remove / adjust / list"""
import argparse
import sys
from store import Store, StoreError


def main(argv=None):
    p = argparse.ArgumentParser(prog="inv")
    p.add_argument("--db", required=True)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); a.add_argument("sku"); a.add_argument("name"); a.add_argument("qty", type=int, nargs="?", default=0)
    r = sub.add_parser("remove"); r.add_argument("sku")
    j = sub.add_parser("adjust"); j.add_argument("sku"); j.add_argument("delta", type=int)
    sub.add_parser("list")
    args = p.parse_args(argv)
    store = Store.load(args.db)
    try:
        if args.cmd == "add":
            store.add(args.sku, args.name, args.qty)
        elif args.cmd == "remove":
            store.remove(args.sku)
        elif args.cmd == "adjust":
            store.adjust(args.sku, args.delta)
        elif args.cmd == "list":
            for it in store.items():
                print(f"{it.sku}\t{it.name}\t{it.qty}")
            return 0
    except StoreError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    store.save(args.db)
    return 0


if __name__ == "__main__":
    sys.exit(main())

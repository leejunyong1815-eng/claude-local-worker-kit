"""In-memory inventory with JSON persistence."""
import json
from models import Item


class StoreError(Exception):
    pass


class InsufficientStock(StoreError):
    pass


class Store:
    def __init__(self):
        self._items = {}

    # ---- persistence ----
    @classmethod
    def load(cls, path):
        s = cls()
        try:
            with open(path, encoding="utf-8") as f:
                for d in json.load(f):
                    s._items[d["sku"]] = Item.from_dict(d)
        except FileNotFoundError:
            pass
        return s

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([i.to_dict() for i in self.items()], f, indent=1)

    # ---- operations ----
    def items(self):
        return [self._items[k] for k in sorted(self._items)]

    def get(self, sku):
        return self._items.get(sku)

    def add(self, sku, name, qty=0):
        if sku in self._items:
            raise StoreError(f"duplicate sku {sku}")
        if qty < 0:
            raise StoreError("negative qty")
        self._items[sku] = Item(sku, name, qty)

    def remove(self, sku):
        if sku not in self._items:
            raise StoreError(f"unknown sku {sku}")
        del self._items[sku]

    def adjust(self, sku, delta):
        it = self._items.get(sku)
        if it is None:
            raise StoreError(f"unknown sku {sku}")
        if it.qty + delta < 0:
            raise InsufficientStock(f"{sku}: have {it.qty}, need {-delta}")
        it.qty += delta

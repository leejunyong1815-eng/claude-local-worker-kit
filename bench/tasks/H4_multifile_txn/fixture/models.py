from dataclasses import dataclass


@dataclass
class Item:
    sku: str
    name: str
    qty: int

    def to_dict(self):
        return {"sku": self.sku, "name": self.name, "qty": self.qty}

    @classmethod
    def from_dict(cls, d):
        return cls(d["sku"], d["name"], int(d["qty"]))

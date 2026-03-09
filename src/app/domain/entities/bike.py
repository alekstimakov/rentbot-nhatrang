from dataclasses import dataclass


@dataclass(slots=True)
class Bike:
    id: int
    model_name: str
    category: str
    price_per_day: int
    is_active: bool = True

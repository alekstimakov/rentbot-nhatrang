from typing import Protocol

from app.domain.entities.bike import Bike


class BikeReadRepository(Protocol):
    async def get_available_bikes(self, *, category: str | None = None) -> list[Bike]:
        ...


class GetAvailableBikes:
    def __init__(self, bike_repository: BikeReadRepository) -> None:
        self._bike_repository = bike_repository

    async def execute(self, *, category: str | None = None) -> list[Bike]:
        return await self._bike_repository.get_available_bikes(category=category)

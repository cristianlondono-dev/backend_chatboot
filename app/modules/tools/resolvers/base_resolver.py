from abc import ABC, abstractmethod


class BaseResolver(ABC):
    """Contract for all identity resolvers."""

    @abstractmethod
    def resolve(self, identifier: str) -> dict | None:
        """
        Look up a user by identifier in an external source.
        Returns a dict with the user's data, or None if not found.
        """
        ...

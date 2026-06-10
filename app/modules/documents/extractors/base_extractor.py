from abc import ABC
from abc import abstractmethod


class BaseExtractor(ABC):

    @abstractmethod
    def extract(self, file_path: str) -> str:
        ...

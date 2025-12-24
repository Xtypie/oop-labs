from enum import Enum
from typing import Self
import types

from lab2_font7 import font7
from lab2_font5 import font5


class Color(Enum):
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    WHITE = "\033[37m"


class Printer:
    def __init__(self, color: Color, position: tuple[int, int], symbol: str, font: dict[str, list]) -> None:
        self.color = color
        self.position = position
        self.symbol = symbol
        self.font = font

    @classmethod
    def print_text(cls, text: str, color: Color, position: tuple[int, int], symbol: str, font: dict[str, list]) -> None:
        printer = cls(color, position, symbol, font)
        printer._render(text)

    def _prepare_rows(self, text_line: str) -> list[str]:
        rows = []
        for char in text_line:
            char_key = char.upper() if char.upper() in self.font else " "
            rows.append(self.font[char_key])
            rows.append(self.font[" "])

        if not rows:
            return []

        height = len(rows[0])
        output = [""] * height

        for char_rows in rows:
            for i, row in enumerate(char_rows):
                output[i] += row.replace("*", self.symbol)

        return output

    def _render(self, text: str) -> None:
        vert, horiz = self.position
        print("\n" * vert, end="")

        for line in text.split("\n"):
            if not line.strip():
                print()
                continue

            prepared = self._prepare_rows(line)
            for row in prepared:
                print(" " * horiz + self.color.value + row + Color.RESET.value)
            print()

    def print(self, text: str) -> None:
        self._render(text)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None,
                 traceback: types.TracebackType | None) -> None:
        print(Color.RESET.value, end="")


Printer.print_text("Hello", Color.BLUE, (2, 5), "9", font5)

with Printer(Color.GREEN, (1, 1), "#", font7) as p:
    p.print("Hello, \n World")
from abc import ABC, abstractmethod
from typing import Any, Callable
import json
from dataclasses import asdict, dataclass, field


class Command(ABC):
    @abstractmethod
    def execute(self) -> None:
        ...

    @abstractmethod
    def cancel(self) -> None:
        ...

    def is_printed(self) -> bool:
        return False


class Keyboard:
    def __init__(self, file_to_safe: str) -> None:
        self.state_server = KeybordStateSaver(self, file_to_safe, KeyboardSerializer())
        self.undo_stack = []
        self.redo_stack = []
        self.printed_sq = ""
        self.commands = {}

    def init_commands(self, commands: dict[str, Command]) -> None:
        self.commands = commands

    def do(self, command_key: str) -> None:
        if command_key not in self.commands:
            print(f"Command '{command_key}' not found")
            return
        cmd = self.commands[command_key]
        if cmd.is_printed():
            self.printed_sq += cmd.my_key()
            cmd.execute(self.printed_sq)
        else:
            cmd.execute()
        self.undo_stack.append(command_key)
        self.redo_stack.clear()

    def undo(self) -> None:
        if not self.undo_stack:
            print("Nothing to undo")
            return
        command_key = self.undo_stack.pop()
        cmd = self.commands[command_key]
        if cmd.is_printed():
            self.printed_sq = self.printed_sq[:-1]
            cmd.cancel(self.printed_sq)
        else:
            cmd.cancel()
        self.redo_stack.append(command_key)

    def redo(self) -> None:
        if not self.redo_stack:
            print("Nothing to redo")
            return
        command_key = self.redo_stack.pop()
        cmd = self.commands[command_key]
        if cmd.is_printed():
            self.printed_sq += cmd.my_key()
            cmd.execute(self.printed_sq)
        else:
            cmd.execute()
        self.undo_stack.append(command_key)

    def serialize(self) -> None:
        self.state_server.save()

    def deserialize(self) -> None:
        self.state_server.load()


class KeyCommand(Command):
    def __init__(self, key: str) -> None:
        self.key = key

    def my_key(self):
        return self.key

    def execute(self, sq: str) -> None:
        print(sq)

    def cancel(self, sq: str) -> None:
        print(sq)

    def is_printed(self) -> bool:
        return True


class VolumeUpCommand(Command):
    def execute(self) -> None:
        print("Звук увеличен на +20%")

    def cancel(self) -> None:
        print("Звук уменьшен на -20%")


class VolumeDownCommand(Command):
    def execute(self) -> None:
        print("Звук уменьшен на -20%")

    def cancel(self) -> None:
        print("Звук увеличен на +20%")


class MediaPlayerCommand(Command):
    def execute(self) -> None:
        print("Плейер запущен")

    def cancel(self) -> None:
        print("Плейер закрыт")


@dataclass
class CommandData:
    type: str
    args: dict[str, Any]


@dataclass
class KeyboardData:
    printed_sq: Any
    undo_stack: list
    redo_stack: list
    commands: dict[str, CommandData] = field(default_factory=dict)


class Serializer(ABC):
    @abstractmethod
    def serialize(self, obj: object) -> dict:
        ...


class KeyboardSerializer(Serializer):
    def serialize(self, obj: object) -> dict:
        return {k: v for k, v in obj.__dict__.items() if k not in ("keyboard", "action", "undo_action")}


class KeybordStateSaver:
    def __init__(self, keyboard: 'Keyboard', file_path: str,
                 serializer: Serializer) -> None:
        self.keyboard = keyboard
        self.file_path = Path(file_path)
        self.serializer = serializer

    def save(self) -> None:
        commands_data = {
            key: CommandData(
                type=cmd.__class__.__name__,
                args=self.serializer.serialize(cmd)
            )
            for key, cmd in self.keyboard.commands.items()
        }

        full_data = KeyboardData(
            printed_sq=self.keyboard.printed_sq,
            undo_stack=self.keyboard.undo_stack,
            redo_stack=self.keyboard.redo_stack,
            commands=commands_data
        )

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(full_data), f, indent=4, ensure_ascii=False)

    def load(self) -> None:
        if not self.file_path.exists():
            return

        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.keyboard.printed_sq = data.get("printed_sq", "")
        self.keyboard.undo_stack = data.get("undo_stack", [])
        self.keyboard.redo_stack = data.get("redo_stack", [])

        commands_data = data.get("commands", {})
        restored = {}

        for key, info in commands_data.items():
            cmd_type = info["type"]
            args = info["args"]

            if cmd_type == "KeyCommand":
                restored[key] = KeyCommand(args["key"], )
            elif cmd_type == "VolumeUpCommand":
                restored[key] = VolumeUpCommand()
            elif cmd_type == "VolumeDownCommand":
                restored[key] = VolumeDownCommand()
            elif cmd_type == "MediaPlayerCommand":
                restored[key] = MediaPlayerCommand()

        self.keyboard.init_commands(restored)


from pathlib import Path

TEST_FILE = "test_state.json"

k = Keyboard(TEST_FILE)

commands = {
    letter: KeyCommand(
        letter)
    for letter in "abcd"
}

commands["ctrl++"] = VolumeUpCommand()

commands["ctrl+-"] = VolumeDownCommand()

commands["ctrl+p"] = MediaPlayerCommand()

k.init_commands(commands)

print("1) Печать символов и Undo/Redo")
k.do('a')  # a
k.do('b')  # ab
k.do('c')  # abc
k.undo()  # ab
k.undo()  # a
k.redo()  # ab

print("2) Команды громкости")
k.do('ctrl++')
k.undo()
k.do('ctrl+-')
k.undo()

print("3) Команды для плейера")
k.do('ctrl+p')
k.undo()

print("4) Сохранение состояния")
k.serialize()  # сохраняем состояние

print("5) восстановление состояния")
new_k = Keyboard(TEST_FILE)
new_k.deserialize()

print(f"Restored printed_sq: {new_k.printed_sq}")
print(f"Restored undo_stack: {new_k.undo_stack}")

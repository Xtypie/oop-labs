from abc import ABC, abstractmethod
from typing import Any, List, Dict, Type
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


class Text:
    def __init__(self) -> None:
        self.content = ""

    def add(self, char: str) -> None:
        self.content += char

    def remove_last(self) -> None:
        if self.content:
            self.content = self.content[:-1]

    def get(self) -> str:
        return self.content

    def set(self, text: str) -> None:
        self.content = text


class Command(ABC):
    @abstractmethod
    def execute(self, buffer: Text) -> None:
        ...

    @abstractmethod
    def cancel(self, buffer: Text) -> None:
        ...


class KeyCommand(Command):
    def __init__(self, key: str) -> None:
        self.key = key

    def execute(self, buffer: Text) -> None:
        buffer.add(self.key)
        print(buffer.get())

    def cancel(self, buffer: Text) -> None:
        buffer.remove_last()
        print(buffer.get())


class Beep(Command):

    def execute(self, buffer: Text) -> None:
        print("Издали звук")

    def cancel(self, buffer: Text) -> None:
        pass


class VolumeUpCommand(Command):
    def execute(self, buffer: Text) -> None:
        print("Звук увеличен на +20%")

    def cancel(self, buffer: Text) -> None:
        print("Звук уменьшен на -20%")


class VolumeDownCommand(Command):
    def execute(self, buffer: Text) -> None:
        print("Звук уменьшен на -20%")

    def cancel(self, buffer: Text) -> None:
        print("Звук увеличен на +20%")


class MediaPlayerCommand(Command):
    def execute(self, buffer: Text) -> None:
        print("Плейер запущен")

    def cancel(self, buffer: Text) -> None:
        print("Плейер закрыт")


class Keyboard:
    def __init__(self, file_to_safe: str) -> None:
        self.buffer = Text()
        self.state_server = KeybordStateSaver(self, file_to_safe, KeyboardSerializer())
        self.undo_stack: List[str] = []
        self.redo_stack: List[str] = []
        self.commands: Dict[str, Command] = {}
        self._command_types: Dict[str, Type[Command]] = {}

    def register_command(self, command_type: str, cls: Type[Command]) -> None:
        self._command_types[command_type] = cls

    def init_commands(self, commands: Dict[str, Command]) -> None:
        self.commands = commands

    def do(self, command_key: str) -> None:
        if command_key not in self.commands:
            print(f"Command '{command_key}' not found")
            return
        cmd = self.commands[command_key]
        cmd.execute(self.buffer)
        self.undo_stack.append(command_key)
        self.redo_stack.clear()

    def undo(self) -> None:
        if not self.undo_stack:
            print("Nothing to undo")
            return
        command_key = self.undo_stack.pop()
        cmd = self.commands[command_key]
        cmd.cancel(self.buffer)
        self.redo_stack.append(command_key)

    def redo(self) -> None:
        if not self.redo_stack:
            print("Nothing to redo")
            return
        command_key = self.redo_stack.pop()
        cmd = self.commands[command_key]
        cmd.execute(self.buffer)
        self.undo_stack.append(command_key)

    def serialize(self) -> None:
        self.state_server.save()

    def deserialize(self) -> None:
        self.state_server.load()


@dataclass
class CommandData:
    type: str
    args: Dict[str, Any]


@dataclass
class KeyboardData:
    printed_sq: str
    undo_stack: List[str]
    redo_stack: List[str]
    commands: Dict[str, CommandData] = field(default_factory=dict)


class Serializer(ABC):
    @abstractmethod
    def serialize(self, obj: object) -> Dict[str, Any]:
        ...


class KeyboardSerializer(Serializer):
    def serialize(self, obj: object) -> Dict[str, Any]:
        return {k: v for k, v in obj.__dict__.items() if k not in ("keyboard", "action", "undo_action")}


class KeybordStateSaver:
    def __init__(self, keyboard: Keyboard, file_path: str,
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
            printed_sq=self.keyboard.buffer.get(),
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

        self.keyboard.buffer.set(data.get("printed_sq", ""))
        self.keyboard.undo_stack = data.get("undo_stack", [])
        self.keyboard.redo_stack = data.get("redo_stack", [])

        commands_data = data.get("commands", {})
        restored: Dict[str, Command] = {}

        for key, info in commands_data.items():
            cmd_type = info["type"]
            args = info["args"]

            if cmd_type in self.keyboard._command_types:
                cls = self.keyboard._command_types[cmd_type]
                restored[key] = cls(**args)

        self.keyboard.init_commands(restored)


TEST_FILE = "test_state.json"

k = Keyboard(TEST_FILE)

k.register_command("KeyCommand", KeyCommand)
k.register_command("VolumeUpCommand", VolumeUpCommand)
k.register_command("VolumeDownCommand", VolumeDownCommand)
k.register_command("MediaPlayerCommand", MediaPlayerCommand)
k.register_command("Beep", Beep)

commands: Dict[str, Command] = {
    letter: KeyCommand(letter)
    for letter in "abcd"
}

commands["ctrl++"] = VolumeUpCommand()
commands["ctrl+-"] = VolumeDownCommand()
commands["ctrl+p"] = MediaPlayerCommand()
commands["ctrl+m"] = Beep()

k.init_commands(commands)

print("1) Печать символов и Undo/Redo")
k.do('a')
k.do('b')
k.do('c')
k.undo()
k.undo()
k.redo()

print("\n2) Команды громкости")
k.do('ctrl++')
k.undo()
k.do('ctrl+-')
k.undo()
k.do('ctrl+m')
k.undo()

print("\n3) Команды для плейера")
k.do('ctrl+p')
k.undo()

print("\n4) Сохранение состояния")
k.serialize()

print("\n5) Восстановление состояния")
new_k = Keyboard(TEST_FILE)

new_k.register_command("KeyCommand", KeyCommand)
new_k.register_command("VolumeUpCommand", VolumeUpCommand)
new_k.register_command("VolumeDownCommand", VolumeDownCommand)
new_k.register_command("MediaPlayerCommand", MediaPlayerCommand)
new_k.register_command("Beep", Beep)

new_k.deserialize()

print(f"Restored buffer: {new_k.buffer.get()}")
print(f"Restored undo_stack: {new_k.undo_stack}")
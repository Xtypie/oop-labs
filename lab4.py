from typing import Any, TypeVar, Generic
from abc import ABC, abstractmethod
from dataclasses import dataclass

TEventArgs = TypeVar("TEventArgs")


class EventHandler(ABC, Generic[TEventArgs]):
    @abstractmethod
    def handle(self, sender: object, args: TEventArgs) -> None:
        ...


class EventArgs(ABC):
    ...


@dataclass
class PropertyChangedEventArgs(EventArgs):
    property_name: str


@dataclass
class PropertyChangingEventArgs(EventArgs):
    property_name: str
    old_value: Any
    new_value: Any
    can_change: bool = True


class Event(Generic[TEventArgs]):
    def __init__(self) -> None:
        self.handlers: list[EventHandler[TEventArgs]] = []

    def __iadd__(self, handler: EventHandler) -> None:
        self.handlers.append(handler)
        return self

    def __isub__(self, handler: EventHandler) -> None:
        self.handlers.remove(handler)
        return self

    def invoke(self, sender: object, args: TEventArgs) -> None:
        for handler in self.handlers:
            handler.handle(sender, args)

    __call__ = invoke


class PrintHandler(EventHandler[PropertyChangedEventArgs]):
    def handle(self, sender: object, args: PropertyChangedEventArgs) -> None:
        print(f"[{sender}] changed {args.property_name}")


class ValidationHandler(EventHandler[PropertyChangingEventArgs]):
    def handle(self, sender: object, args: PropertyChangingEventArgs) -> None:
        if args.new_value == "" or args.property_name.startswith("_"):
            args.can_change = False
        else:
            args.can_change = True


class PropertyNotifierMixin:
    def __init__(self) -> None:
        self.property_changing = Event[PropertyChangingEventArgs]()
        self.property_changed = Event[PropertyChangedEventArgs]()

    def __setattr__(self, field_name: str, new_value: Any) -> None:
        if not hasattr(self, "property_changing"):
            super().__setattr__(field_name, new_value)
            return

        old_value = getattr(self, field_name, None)

        args_before = PropertyChangingEventArgs(field_name, old_value, new_value)
        self.property_changing(self, args_before)
        if not args_before.can_change:
            return

        super().__setattr__(field_name, new_value)

        args_after = PropertyChangedEventArgs(field_name)
        self.property_changed(self, args_after)


class Person(PropertyNotifierMixin):
    def __init__(self, name: str, address: str, age: int) -> None:
        super().__init__()
        self.name = name
        self.address = address
        self._age = age


class Auto(PropertyNotifierMixin):
    def __init__(self, model: str, color: str, weight: int) -> None:
        super().__init__()
        self.model = model
        self.color = color
        self.weight = weight


p = Person("Misha", "Nevskogo 14 street", 25)

p.property_changed += PrintHandler()
p.property_changing += ValidationHandler()

p.address = "Ozerova 33 street"
p.name = "Pasha"
p._age = 30

a = Auto("Audi", "blue", 1633)

a.property_changed += PrintHandler()
a.property_changed += PrintHandler()
a.property_changing += ValidationHandler()

a.color = "red"
a.model = "Opel"
a.weight = 1602
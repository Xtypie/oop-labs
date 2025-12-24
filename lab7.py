from typing import Callable, Optional, Any
from enum import Enum
import inspect
import types


class LifeStyle(Enum):
    PerRequest = "PerRequest"
    Scoped = "Scoped"
    Singleton = "Singleton"


class Injector:
    def __init__(self) -> None:
        self.registered_interfaces = {}
        self._scope_stack = []
        self._singletone_instances = {}

    def register(self, interface: object,
                 class_or_factory: object | Callable,
                 lifestyle: Optional[LifeStyle] = None,
                 params: Optional[dict[str, Any]] = None) -> None:

        self.registered_interfaces[interface] = {
            "provider": class_or_factory,
            "lifestyle": lifestyle,
            "params": params if params else {}
        }

    def open_scope(self) -> object:
        return Scope(self)

    def _push_scope(self) -> None:
        self._scope_stack.append({})

    def _pop_scope(self) -> None:
        self._scope_stack.pop()

    def _current_scope(self) -> dict:
        return self._scope_stack[-1] if self._scope_stack else None

    def get_instance(self, interface_type: object) -> object:
        reg = self.registered_interfaces[interface_type]

        provider = reg["provider"]
        params = reg["params"]
        lifestyle = reg["lifestyle"]

        target = provider.__init__ if inspect.isclass(provider) else provider
        sig = inspect.signature(target)

        constructor_args = {}

        for name, param in sig.parameters.items():
            if name == "self":
                continue

            if name in params:
                constructor_args[name] = params[name]
            elif param.annotation in self.registered_interfaces:
                constructor_args[name] = self.get_instance(param.annotation)
            else:
                raise Exception("DI can't resolve parameter")

        if lifestyle == LifeStyle.PerRequest:
            return provider(**constructor_args)

        elif lifestyle == LifeStyle.Singleton:
            if interface_type not in self._singletone_instances:
                self._singletone_instances[interface_type] = provider(**constructor_args)
            return self._singletone_instances[interface_type]

        elif lifestyle == LifeStyle.Scoped:
            scope = self._current_scope()
            if scope is None:
                return None

            if interface_type not in scope:
                scope[interface_type] = provider(**constructor_args)

            return scope[interface_type]


class Scope:
    def __init__(self, injector: Injector) -> None:
        self.injector = injector

    def __enter__(self) -> Injector:
        self.injector._push_scope()
        return self.injector

    def __exit__(
            self,
            exc_type: type | None,
            exc_value: BaseException | None,
            traceback: types.TracebackType | None
    ) -> None:
        self.injector._pop_scope()


# ----------- Интерфейсы -----------
class I1: ...


class I2: ...


class I3: ...


# ----------- Реализации Interface 1 -----------
class C1_Debug(I1):
    def __init__(self):
        self.name = "C1_Debug"


class C1_Release(I1):
    def __init__(self):
        self.name = "C1_Release"


# ----------- Реализации Interface 2 -----------
class C2_Debug(I2):
    def __init__(self, i1: I1):
        # зависимость от интерфейса I1
        self.i1 = i1
        self.name = "C2_Debug"


class C2_Release(I2):
    def __init__(self, i1: I1):
        self.i1 = i1
        self.name = "C2_Release"


# ----------- Реализации Interface 3 -----------
class C3_Debug(I3):
    def __init__(self, i1: I1, i2: I2):
        self.i1 = i1
        self.i2 = i2
        self.name = "C3_Debug"


class C3_Release(I3):
    def __init__(self, i1: I1, i2: I2):
        self.i1 = i1
        self.i2 = i2
        self.name = "C3_Release"


# ============ ТЕСТЫ ============

def test_config_1(injector):
    print("=== CONFIG 1 ===")

    # Конфигурация 1: все DEBUG реализация
    injector.register(I1, C1_Debug, LifeStyle.PerRequest)
    injector.register(I2, C2_Debug, LifeStyle.PerRequest)
    injector.register(I3, C3_Debug, LifeStyle.PerRequest)

    obj1 = injector.get_instance(I1)
    obj2 = injector.get_instance(I2)
    obj3 = injector.get_instance(I3)

    print(obj1.name)  # C1_Debug
    print(obj2.name, obj2.i1.name)  # C2_Debug, C1_Debug
    print(obj3.name, obj3.i1.name, obj3.i2.name)
    # C3_Debug, C1_Debug, C2_Debug


def test_config_2(injector):
    print("=== CONFIG 2 ===")

    # Конфигурация 2: RELEASE реализация и разные жизненные циклы
    injector.register(I1, C1_Release, LifeStyle.Singleton)
    injector.register(I2, C2_Release, LifeStyle.Scoped)
    injector.register(I3, C3_Release, LifeStyle.PerRequest)

    # Global Singleton
    i1_a = injector.get_instance(I1)
    i1_b = injector.get_instance(I1)
    print("Singleton:", i1_a is i1_b)  # True

    # Scoped
    with injector.open_scope():
        i2_a = injector.get_instance(I2)
        i2_b = injector.get_instance(I2)
        print("Scoped:", i2_a is i2_b)  # True внутри scope

    # вне scope — новый объект
    with injector.open_scope():
        i2_c = injector.get_instance(I2)
        print("Scoped new:", i2_a is i2_c)  # False

    # PerRequest
    i3_a = injector.get_instance(I3)
    i3_b = injector.get_instance(I3)
    print("PerRequest:", i3_a is i3_b)  # False


# запуск тестов
def run_all_tests():
    # from injector import Injector  # твой класс

    inj = Injector()
    test_config_1(inj)

    inj = Injector()
    test_config_2(inj)


run_all_tests()
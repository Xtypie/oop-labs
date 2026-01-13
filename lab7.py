from typing import Callable, Optional, Any, Dict, List, Type, Union
from enum import Enum
import inspect
import types


class LifeStyle(Enum):
    PerRequest = "PerRequest"
    Scoped = "Scoped"
    Singleton = "Singleton"


class Injector:
    def __init__(self) -> None:
        self.registered_interfaces: Dict[Type[Any], Dict[str, Any]] = {}
        self._scope_stack: List[Dict[Type[Any], Any]] = []
        self._singletone_instances: Dict[Type[Any], Any] = {}

    def register(self, interface: Type[Any],
                 class_or_factory: Union[Type[Any], Callable[..., Any]],
                 lifestyle: Optional[LifeStyle] = None,
                 params: Optional[Dict[str, Any]] = None) -> None:

        if inspect.isclass(class_or_factory):
            target = class_or_factory.__init__
            sign = inspect.signature(target)

            for name, parameter in sign.parameters.items():
                if name == "self":
                    continue

                if (name not in (params or {}) and parameter.annotation != inspect.Parameter.empty and
                    parameter.annotation not in self.registered_interfaces):
                    raise Exception (f"Can`t register {class_or_factory.__name__} \n"
                                     f"Because {parameter.annotation.__name__} isn`t registered")

        self.registered_interfaces[interface] = {
            "provider": class_or_factory,
            "lifestyle": lifestyle,
            "params": params if params else {}
        }

    def open_scope(self) -> Any:
        return Scope(self)

    def _push_scope(self) -> None:
        self._scope_stack.append({})

    def _pop_scope(self) -> None:
        self._scope_stack.pop()

    def _current_scope(self) -> Optional[Dict[Type[Any], Any]]:
        return self._scope_stack[-1] if self._scope_stack else None

    def get_instance(self, interface_type: Type[Any]) -> Any:
        reg = self.registered_interfaces[interface_type]

        provider = reg["provider"]
        params = reg["params"]
        lifestyle = reg["lifestyle"]

        target = provider.__init__ if inspect.isclass(provider) else provider
        sig = inspect.signature(target)

        constructor_args: Dict[str, Any] = {}

        for name, param in sig.parameters.items():
            if name == "self":
                continue

            if name in params:
                constructor_args[name] = params[name]
            elif param.annotation in self.registered_interfaces:
                dep_lifestyle = self.registered_interfaces[param.annotation]["lifestyle"]
                if dep_lifestyle == LifeStyle.Scoped and self._current_scope() is None:
                    constructor_args[name] = self._create_scoped_instance(param.annotation)
                else:
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
                return self._create_scoped_instance(interface_type)

            if interface_type not in scope:
                scope[interface_type] = provider(**constructor_args)

            return scope[interface_type]

        raise Exception(f"Unknown lifestyle: {lifestyle}")

    def _create_scoped_instance(self, interface_type: Type[Any]) -> Any:
        temp_scope: Dict[Type[Any], Any] = {}
        self._scope_stack.append(temp_scope)

        try:
            reg = self.registered_interfaces[interface_type]
            provider = reg["provider"]
            params = reg["params"]

            target = provider.__init__ if inspect.isclass(provider) else provider
            sig = inspect.signature(target)

            constructor_args: Dict[str, Any] = {}

            for name, param in sig.parameters.items():
                if name == "self":
                    continue

                if name in params:
                    constructor_args[name] = params[name]
                elif param.annotation in self.registered_interfaces:
                    constructor_args[name] = self.get_instance(param.annotation)
                else:
                    raise Exception("DI can't resolve parameter")

            instance = provider(**constructor_args)
            temp_scope[interface_type] = instance
            return instance
        finally:
            self._scope_stack.pop()


class Scope:
    def __init__(self, injector: Injector) -> None:
        self.injector = injector

    def __enter__(self) -> 'Scope':
        self.injector._push_scope()
        return self

    def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_value: Optional[BaseException],
            traceback: Optional[types.TracebackType]) -> None:
        self.injector._pop_scope()

# интерфейсы


class I1:
    ...


class I2:
    ...


class I3:
    ...


class C1_Debug(I1):
    def __init__(self) -> None:
        self.name = "C1_Debug"


class C1_Release(I1):
    def __init__(self) -> None:
        self.name = "C1_Release"


class C2_Debug(I2):
    def __init__(self, i1: I1) -> None:
        self.i1 = i1
        self.name = "C2_Debug"


class C2_Release(I2):
    def __init__(self, i1: I1) -> None:
        self.i1 = i1
        self.name = "C2_Release"


class C3_Debug(I3):
    def __init__(self, i1: I1, i2: I2) -> None:
        self.i1 = i1
        self.i2 = i2
        self.name = "C3_Debug"


class C3_Release(I3):
    def __init__(self, i1: I1, i2: I2) -> None:
        self.i1 = i1
        self.i2 = i2
        self.name = "C3_Release"


def test_config_1(injector: Injector) -> None:

    injector.register(I1, C1_Debug, LifeStyle.PerRequest)
    injector.register(I2, C2_Debug, LifeStyle.PerRequest)
    injector.register(I3, C3_Debug, LifeStyle.PerRequest)

    obj1 = injector.get_instance(I1)
    obj2 = injector.get_instance(I2)
    obj3 = injector.get_instance(I3)

    print(obj1.name)
    print(obj2.name, obj2.i1.name)
    print(obj3.name, obj3.i1.name, obj3.i2.name)


def test_config_2(injector: Injector) -> None:
    injector.register(I1, C1_Release, LifeStyle.Singleton)
    injector.register(I2, C2_Release, LifeStyle.Scoped)
    injector.register(I3, C3_Release, LifeStyle.PerRequest)

    i1_a = injector.get_instance(I1)
    i1_b = injector.get_instance(I1)
    print("Singleton:", i1_a is i1_b)

    with injector.open_scope():
        i2_a = injector.get_instance(I2)
        i2_b = injector.get_instance(I2)
        print("Scoped:", i2_a is i2_b)

    with injector.open_scope():
        i2_c = injector.get_instance(I2)
        print("Scoped new:", i2_a is i2_c)

    i3_a = injector.get_instance(I3)
    i3_b = injector.get_instance(I3)
    print("PerRequest:", i3_a is i3_b)


def run_all_tests() -> None:
    inj = Injector()
    test_config_1(inj)

    inj = Injector()
    test_config_2(inj)


if __name__ == "__main__":
    run_all_tests()

from typing import Callable, Optional, Any, Type, Dict, List
from enum import Enum
import inspect
import types


class Lifecycle(Enum):
    TRANSIENT = "Transient"
    SCOPED = "Scoped"
    SINGLETON = "Singleton"


class DependencyInjector:
    def __init__(self) -> None:
        self._registry: Dict[Type, dict] = {}
        self._scopes: List[Dict[Type, Any]] = []
        self._singletons: Dict[Type, Any] = {}

    def register(
            self,
            abstract: Type,
            implementation: Type | Callable,
            lifecycle: Lifecycle = Lifecycle.TRANSIENT,
            **kwargs: Any
    ) -> None:
        if abstract in self._registry:
            raise ValueError(f"Тип {abstract} уже зарегистрирован")

        self._registry[abstract] = {
            'concrete': implementation,
            'lifecycle': lifecycle,
            'parameters': kwargs
        }

    def create_scope(self) -> 'DependencyScope':
        return DependencyScope(self)

    def _enter_scope(self) -> None:
        self._scopes.append({})

    def _exit_scope(self) -> None:
        if self._scopes:
            self._scopes.pop()

    def _get_current_scope(self) -> Optional[Dict[Type, Any]]:
        return self._scopes[-1] if self._scopes else None

    def resolve(self, abstract: Type) -> Any:
        if abstract not in self._registry:
            raise ValueError(f"Тип {abstract} не зарегистрирован")

        registration = self._registry[abstract]
        implementation = registration['concrete']
        lifecycle = registration['lifecycle']
        params = registration['parameters']

        if lifecycle == Lifecycle.SINGLETON:
            if abstract not in self._singletons:
                self._singletons[abstract] = self._construct_instance(implementation, params)
            return self._singletons[abstract]

        elif lifecycle == Lifecycle.SCOPED:
            scope = self._get_current_scope()
            if scope is None:
                raise RuntimeError("Нет активной области видимости")

            if abstract not in scope:
                scope[abstract] = self._construct_instance(implementation, params)
            return scope[abstract]

        elif lifecycle == Lifecycle.TRANSIENT:
            return self._construct_instance(implementation, params)

        else:
            raise ValueError(f"Неизвестный жизненный цикл: {lifecycle}")

    def _construct_instance(self, implementation: Type | Callable, extra_params: Dict[str, Any]) -> Any:
        if inspect.isclass(implementation):
            signature_target = implementation.__init__
            is_class = True
        else:
            signature_target = implementation
            is_class = False

        sig = inspect.signature(signature_target)
        constructor_args = {}

        for param_name, param in sig.parameters.items():
            if param_name == 'self' and is_class:
                continue

            if param_name in extra_params:
                constructor_args[param_name] = extra_params[param_name]

            elif param.annotation != inspect.Parameter.empty:
                if param.annotation in self._registry:
                    constructor_args[param_name] = self.resolve(param.annotation)
                elif param.default != inspect.Parameter.empty:
                    constructor_args[param_name] = param.default
                else:
                    raise RuntimeError(
                        f"Не удается разрешить параметр '{param_name}' "
                        f"типа '{param.annotation}' для {implementation}"
                    )

            elif param.default != inspect.Parameter.empty:
                constructor_args[param_name] = param.default
            else:
                raise RuntimeError(
                    f"Не удается разрешить параметр '{param_name}' без аннотации"
                )

        if is_class:
            return implementation(**constructor_args)
        else:
            return implementation(**constructor_args)


class DependencyScope:
    def __init__(self, injector: DependencyInjector) -> None:
        self.injector = injector

    def __enter__(self) -> DependencyInjector:
        self.injector._enter_scope()
        return self.injector

    def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_val: Optional[BaseException],
            exc_tb: Optional[types.TracebackType]
    ) -> None:
        self.injector._exit_scope()


class ILogger:
    pass


class IDataRepository:
    pass


class IBusinessService:
    pass


class ConsoleLogger(ILogger):
    def __init__(self, log_prefix: str = "LOG"):
        self.prefix = log_prefix
        self.name = "ConsoleLogger"

    def log(self, message: str) -> None:
        print(f"[{self.prefix}] {message}")


class FileLogger(ILogger):
    def __init__(self, filename: str = "app.log"):
        self.filename = filename
        self.name = "FileLogger"

    def log(self, message: str) -> None:
        with open(self.filename, 'a', encoding='utf-8') as f:
            f.write(f"{message}\n")


class MemoryRepository(IDataRepository):
    def __init__(self, logger: ILogger):
        self.logger = logger
        self.data = {}
        self.name = "MemoryRepository"

    def add(self, key: str, value: Any) -> None:
        self.data[key] = value
        if isinstance(self.logger, ConsoleLogger):
            self.logger.log(f"Добавлен элемент: {key} -> {value}")


class DatabaseRepository(IDataRepository):
    def __init__(self, logger: ILogger, connection_string: str):
        self.logger = logger
        self.connection_string = connection_string
        self.name = "DatabaseRepository"

    def connect(self) -> None:
        if isinstance(self.logger, ConsoleLogger):
            self.logger.log(f"Подключение к БД: {self.connection_string}")


class UserService(IBusinessService):
    def __init__(self, logger: ILogger, repository: IDataRepository):
        self.logger = logger
        self.repository = repository
        self.name = "UserService"

    def process_user(self, user_id: int) -> None:
        if isinstance(self.logger, ConsoleLogger):
            self.logger.log(f"Обработка пользователя {user_id}")
        print(f"Сервис {self.name} использует {self.repository.name}")


class OrderService(IBusinessService):
    def __init__(self, logger: ILogger, repository: IDataRepository, tax_rate: float = 0.2):
        self.logger = logger
        self.repository = repository
        self.tax_rate = tax_rate
        self.name = "OrderService"

    def calculate_total(self, amount: float) -> float:
        total = amount * (1 + self.tax_rate)
        if isinstance(self.logger, ConsoleLogger):
            self.logger.log(f"Расчет суммы: {amount} -> {total}")
        return total


def demonstrate_dependency_injection():
    print("ДЕМОНСТРАЦИЯ")

    print("\n1. Конфигурация для разработки:")

    dev_injector = DependencyInjector()

    dev_injector.register(ILogger, ConsoleLogger, Lifecycle.SINGLETON, log_prefix="DEV")
    dev_injector.register(IDataRepository, MemoryRepository, Lifecycle.TRANSIENT)
    dev_injector.register(IBusinessService, UserService, Lifecycle.SCOPED)

    print("Система логирования (Singleton):")
    logger1 = dev_injector.resolve(ILogger)
    logger2 = dev_injector.resolve(ILogger)
    print(f"  logger1 is logger2: {logger1 is logger2}")

    print("\nРепозиторий (Transient):")
    repo1 = dev_injector.resolve(IDataRepository)
    repo2 = dev_injector.resolve(IDataRepository)
    print(f"  repo1 is repo2: {repo1 is repo2}")

    print("\nСервис пользователей в области видимости (Scoped):")
    with dev_injector.create_scope():
        service1 = dev_injector.resolve(IBusinessService)
        service2 = dev_injector.resolve(IBusinessService)
        print(f"  В одной области: service1 is service2: {service1 is service2}")

    with dev_injector.create_scope():
        service3 = dev_injector.resolve(IBusinessService)

    print("\n2. Конфигурация для продакшена:")

    prod_injector = DependencyInjector()

    prod_injector.register(
        ILogger,
        FileLogger,
        Lifecycle.SINGLETON,
        filename="production.log"
    )
    prod_injector.register(
        IDataRepository,
        DatabaseRepository,
        Lifecycle.SINGLETON,
        connection_string="server=prod;database=app"
    )
    prod_injector.register(
        IBusinessService,
        OrderService,
        Lifecycle.TRANSIENT,
        tax_rate=0.18
    )

    print("Создание сервиса заказов с внедренными зависимостями:")
    order_service = prod_injector.resolve(IBusinessService)

    if isinstance(order_service, OrderService):
        print(f"  Сервис: {order_service.name}")
        print(f"  Логгер: {order_service.logger.name}")
        print(f"  Репозиторий: {order_service.repository.name}")
        print(f"  Ставка налога: {order_service.tax_rate}")

        total = order_service.calculate_total(1000)
        print(f"  Расчет суммы заказа: 1000 -> {total:.2f}")

    print("\n3. Фабричные методы:")

    def create_custom_logger(log_level: str = "INFO") -> ILogger:
        class CustomLogger(ILogger):
            def __init__(self):
                self.name = f"CustomLogger_{log_level}"
                self.level = log_level

            def log(self, message: str):
                print(f"[{self.level}] {message}")

        return CustomLogger()

    custom_injector = DependencyInjector()
    custom_injector.register(
        ILogger,
        lambda: create_custom_logger("DEBUG"),
        Lifecycle.TRANSIENT
    )

    custom_logger = custom_injector.resolve(ILogger)
    print(f"Создан кастомный логгер: {custom_logger.name}")
    custom_logger.log("Тестовое сообщение")



if __name__ == "__main__":
    demonstrate_dependency_injection()
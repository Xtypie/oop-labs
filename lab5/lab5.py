from typing import Self, Optional, TypeVar, Generic, Sequence
from dataclasses import dataclass, asdict, field
from abc import ABC, abstractmethod
import json
from pathlib import Path


@dataclass
class User:
    id: int
    name: str
    login: str
    password: str = field(repr=False)  # Пароль не показывается при выводе
    email: Optional[str] = None
    address: Optional[str] = None

    def __repr__(self) -> str:
        parts = [
            f"id: {self.id}",
            f"name: {self.name}",
            f"login: {self.login}",
        ]
        if self.email is not None:
            parts.append(f"email: {self.email}")
        if self.address is not None:
            parts.append(f"address: {self.address}")
        return "\n".join(parts)

    def __lt__(self, other: Self) -> bool:
        return self.name < other.name


T = TypeVar("T")


class IDataRepository(ABC, Generic[T]):
    """Интерфейс репозитория для операций CRUD"""

    @abstractmethod
    def get_all(self) -> Sequence[T]:
        """Получить все записи"""
        ...

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[T]:
        """Получить запись по идентификатору"""
        ...

    @abstractmethod
    def add(self, item: T) -> None:
        """Добавить новую запись"""
        ...

    @abstractmethod
    def update(self, item: T) -> None:
        """Обновить существующую запись"""
        ...

    @abstractmethod
    def delete(self, item: T) -> None:
        """Удалить запись"""
        ...


class IUserRepository(IDataRepository[User]):
    """Интерфейс репозитория для пользователей"""

    @abstractmethod
    def get_by_login(self, login: str) -> Optional[User]:
        """Получить пользователя по логину"""
        ...


class DataRepository(IDataRepository[T]):
    """Реализация репозитория с хранением данных в JSON файле"""

    def __init__(self, file_path: str, data_type: type) -> None:
        self.file_path = Path(file_path)
        self.data_type = data_type
        self._initialize_file()

    def _initialize_file(self) -> None:
        """Инициализировать файл если он не существует"""
        if not self.file_path.exists():
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=4, ensure_ascii=False)

    def get_all(self) -> Sequence[T]:
        """Получить все записи из файла"""
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [self.data_type(**item) for item in data]

    def get_by_id(self, id: int) -> Optional[T]:
        """Найти запись по идентификатору"""
        items = self.get_all()
        for item in items:
            if hasattr(item, 'id') and item.id == id:
                return item
        return None

    def add(self, item: T) -> None:
        """Добавить новую запись в файл"""
        if self.get_by_id(item.id) is not None:
            return  # Запись с таким ID уже существует
        items = self.get_all()
        items.append(item)
        self._save_all(items)

    def update(self, item: T) -> None:
        """Обновить существующую запись"""
        items = self.get_all()
        for i, existing in enumerate(items):
            if existing.id == item.id:
                items[i] = item
                self._save_all(items)
                return

    def delete(self, item: T) -> None:
        """Удалить запись из файла"""
        items = self.get_all()
        items = [i for i in items if i.id != item.id]
        self._save_all(items)

    def _save_all(self, items: Sequence[T]) -> None:
        """Сохранить все записи в файл"""
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump([asdict(i) for i in items], f, indent=4, ensure_ascii=False)


class UserRepository(DataRepository[User], IUserRepository):
    """Реализация репозитория для пользователей"""

    def __init__(self, file_path: str) -> None:
        super().__init__(file_path, User)

    def get_by_login(self, login: str) -> Optional[User]:
        """Найти пользователя по логину"""
        users = self.get_all()
        for user in users:
            if user.login == login:
                return user
        return None


class IAuthService(ABC):
    """Интерфейс сервиса авторизации"""

    @abstractmethod
    def sign_in(self, user: User) -> None:
        """Вход пользователя в систему"""
        ...

    @abstractmethod
    def sign_out(self, user: User) -> None:
        """Выход пользователя из системы"""
        ...

    @property
    @abstractmethod
    def is_authorized(self) -> bool:
        """Проверка наличия активной авторизации"""
        ...

    @property
    @abstractmethod
    def current_user(self) -> Optional[User]:
        """Получить текущего авторизованного пользователя"""
        ...


class AuthService(IAuthService):
    """Реализация сервиса авторизации с автоматическим восстановлением сессии"""

    def __init__(self, auth_file: str, user_repo: IUserRepository) -> None:
        self.user_repository = user_repo
        self.session_repository = DataRepository(auth_file, SessionData)
        self._session_data: Optional[SessionData] = None
        self._restore_session()

    def _restore_session(self) -> None:
        """Восстановить сессию пользователя из файла"""
        sessions = self.session_repository.get_all()
        if sessions:
            self._session_data = sessions[-1]  # Последняя активная сессия

    def sign_in(self, user: User) -> None:
        """Авторизовать пользователя"""
        if self.is_authorized:
            print("Ошибка: сначала выполните выход из текущей сессии")
            return

        if self.user_repository.get_by_id(user.id) is None:
            print("Ошибка: пользователь не найден")
            return

        self._session_data = SessionData(user.id)
        self.session_repository.add(self._session_data)
        print(f"Пользователь {user.login} успешно авторизован")

    def sign_out(self, user: User) -> None:
        """Завершить сессию пользователя"""
        if not self.is_authorized:
            print("Ошибка: нет активной сессии")
            return

        if self._session_data is None or self._session_data.user_id != user.id:
            print("Ошибка: неверный пользователь для выхода")
            return

        session_to_remove = SessionData(user.id)
        self.session_repository.delete(session_to_remove)
        self._session_data = None
        print(f"Пользователь {user.login} вышел из системы")

    @property
    def is_authorized(self) -> bool:
        """Проверить наличие активной авторизации"""
        return self._session_data is not None

    @property
    def current_user(self) -> Optional[User]:
        """Получить текущего авторизованного пользователя"""
        if not self.is_authorized or self._session_data is None:
            return None
        return self.user_repository.get_by_id(self._session_data.user_id)


@dataclass
class SessionData:
    """Класс для хранения данных сессии"""
    user_id: int

    @property
    def id(self) -> int:
        """Свойство для совместимости с репозиторием"""
        return self.user_id

    def __post_init__(self):
        """Для сериализации в JSON"""
        self._id = self.user_id

    def __hash__(self):
        return hash(self.user_id)

    def __eq__(self, other):
        if isinstance(other, SessionData):
            return self.user_id == other.user_id
        return False


def demonstrate_system():
    print("=" * 50)
    print("ДЕМОНСТРАЦИЯ СИСТЕМЫ АВТОРИЗАЦИИ")
    print("=" * 50)

    # Создание репозитория пользователей
    user_repo = UserRepository("users.json")
    auth_service = AuthService("session.json", user_repo)

    print("\n1. ДОБАВЛЕНИЕ ПОЛЬЗОВАТЕЛЕЙ")
    print("-" * 30)

    # Создание пользователей
    user1 = User(
        id=1,
        name="Василий Пупкин",
        login="vasyanpu",
        password="fizmat123",
        email="vasyan1337@kasha.com",
        address="Москва, ул. пушкина, колотушкина"
    )

    user2 = User(
        id=2,
        name="Владимир Ленин",
        login="vilenin",
        password="revolution17",
        email="lenin@sssr.com"
    )

    user3 = User(
        id=3,
        name="Андрей Бебуришвилкин",
        login="andryuxaxd",
        password="salewa12345"
    )

    user_repo.add(user1)
    user_repo.add(user2)
    user_repo.add(user3)

    print("Добавлены пользователи:")
    for user in user_repo.get_all():
        print(f"  - {user.name} (логин: {user.login})")

    print("\n2. СОРТИРОВКА ПОЛЬЗОВАТЕЛЕЙ ПО ИМЕНИ")
    print("-" * 30)
    sorted_users = sorted(user_repo.get_all())
    print("Отсортированные пользователи:")
    for user in sorted_users:
        print(f"  - {user.name}")

    print("\n3. РЕДАКТИРОВАНИЕ СВОЙСТВ ПОЛЬЗОВАТЕЛЯ")
    print("-" * 30)
    print(f"До редактирования: {user_repo.get_by_id(1)}")
    user1.email = "lenin@sssr.com"
    user_repo.update(user1)
    print(f"После редактирования: {user_repo.get_by_id(1)}")

    print("\n4. АВТОРИЗАЦИЯ ПОЛЬЗОВАТЕЛЯ")
    print("-" * 30)
    print(f"Есть активная сессия? {auth_service.is_authorized}")
    auth_service.sign_in(user1)
    print(f"Есть активная сессия? {auth_service.is_authorized}")
    print(f"Текущий пользователь: {auth_service.current_user}")

    print("\n5. СМЕНА ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ")
    print("-" * 30)
    auth_service.sign_out(user1)
    print(f"Текущий пользователь после выхода: {auth_service.current_user}")
    auth_service.sign_in(user2)
    print(f"Текущий пользователь после входа: {auth_service.current_user}")

    print("\n6. АВТОМАТИЧЕСКАЯ АВТОРИЗАЦИЯ")
    print("-" * 30)
    print("Симуляция перезапуска приложения...")
    new_auth_service = AuthService("session.json", user_repo)
    print(f"Сессия восстановлена автоматически: {new_auth_service.is_authorized}")
    print(f"Текущий пользователь: {new_auth_service.current_user}")

    print("\n7. ПОИСК ПОЛЬЗОВАТЕЛЕЙ")
    print("-" * 30)
    found_user = user_repo.get_by_login("vasyanpu")
    print(f"Найден пользователь по логину 'vasyanpu': {found_user.name if found_user else 'не найден'}")

    print("\n8. УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ")
    print("-" * 30)
    user_to_delete = user_repo.get_by_id(3)
    if user_to_delete:
        user_repo.delete(user_to_delete)
        print(f"Пользователь {user_to_delete.name} удален")
        print(f"Осталось пользователей: {len(user_repo.get_all())}")

    print("\n" + "=" * 50)
    print("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    print("=" * 50)


if __name__ == "__main__":
    demonstrate_system()
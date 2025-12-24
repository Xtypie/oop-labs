from typing import Self, Optional, TypeVar, Generic, Sequence
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import json
from pathlib import Path


@dataclass
class User:
    id: int
    name: str
    login: str
    password: str
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
    @abstractmethod
    def get_all(self) -> Sequence[T]:
        ...

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[T]:
        ...

    @abstractmethod
    def add(self, item: T) -> None:
        ...

    @abstractmethod
    def update(self, item: T) -> None:
        ...

    @abstractmethod
    def delete(self, item: T) -> None:
        ...


class IUserRepository(IDataRepository[User]):
    @abstractmethod
    def get_by_login(self, login: str) -> Optional[User]:
        ...


class IAuthService(ABC):
    @abstractmethod
    def sign_in(self, user: User) -> None:
        ...

    @abstractmethod
    def sign_out(self, user: User) -> None:
        ...

    @property
    @abstractmethod
    def is_authorized(self) -> bool:
        ...

    @property
    @abstractmethod
    def current_user(self) -> Optional[User]:
        ...


class FileDataRepository(Generic[T]):
    def __init__(self, file_path: str, cls_type: T) -> None:
        self.file_path = Path(file_path)
        self.cls_type = cls_type

        if not self.file_path.exists():
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=4, ensure_ascii=False)

    def get_all(self) -> Sequence[User]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [self.cls_type(**item) for item in data]

    def get_by_id(self, id: int) -> Optional[User]:
        users = self.get_all()

        for user in users:
            if user.id == id: return user

        return None

    def add(self, item: User) -> None:
        users = self.get_all()
        if self.get_by_id(item.id) is not None:
            return
        users.append(item)
        self._save_all(users)

    def update(self, item: User) -> None:
        users = self.get_all()
        user = self.get_by_id(item.id)

        user_id = users.index(user)
        users[user_id] = item
        self._save_all(users)

    def delete(self, item: User) -> None:
        users = self.get_all()
        users.remove(item)
        self._save_all(users)

    def _save_all(self, items: Sequence[T]) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump([asdict(i) for i in items], f, indent=4, ensure_ascii=False)


class FileUserRepository(FileDataRepository[User]):
    def __init__(self, file_path: str) -> None:
        super().__init__(file_path, User)

    def get_by_login(self, login: str) -> Optional[User]:
        users = self.get_all()

        for user in users:
            if user.login == login: return user

        return None


@dataclass
class CurrentUser:
    id: int


class FileSaveCurrentUser(FileDataRepository[CurrentUser]):
    def __init__(self, file_path: str) -> None:
        super().__init__(file_path, CurrentUser)


class FileAuthService(IAuthService):
    def __init__(self, auth_path: str, repo_path: str) -> None:
        self.sgn = FileSaveCurrentUser(auth_path)
        self.repo = FileUserRepository(repo_path)

    def sign_in(self, user: User) -> None:
        if self.is_authorized():
            print("Sign out before sign in")
            return
        if self.repo.get_by_id(user.id) is None:
            print("No such user")
            return

        self.sgn.add(CurrentUser(user.id))

    def sign_out(self, user: User) -> None:
        if CurrentUser(user.id) not in self.sgn.get_all():
            print("Sign in before sign out")
            return
        self.sgn.delete(CurrentUser(user.id))

    def is_authorized(self) -> bool:
        sgn_users = self.sgn.get_all()

        return len(sgn_users) > 0

    def current_user(self) -> Optional[User]:
        if not self.is_authorized():
            return None

        return self.repo.get_by_id(self.sgn.get_all()[-1].id)


def run_tests():
    repo_path = "users.json"
    auth_path = "user.json"

    # создаем репозиторий и сервис авторизации
    auth_service = FileAuthService(auth_path, repo_path)
    repo = FileUserRepository(repo_path)

    # # очистим файл для тестов
    # repo._save_all([])

    # 1. Добавление пользователей
    user1 = User(id=1, name="Alice", login="alice123", password="pass1", email="alice@mail.com")
    user2 = User(id=2, name="Bob", login="bob321", password="pass2")
    repo.add(user1)
    repo.add(user2)
    print("Все пользователи после добавления:")
    print(repo.get_all())

    # 2. Редактирование пользователя
    user1.email = "alice_new@mail.com"
    repo.update(user1)
    print("\nПосле редактирования Alice:")
    print(repo.get_by_id(1))

    # 3. Авторизация пользователя
    auth_service.sign_in(user1)
    print("\nАвторизован ли кто-то?", auth_service.is_authorized())
    print("Текущий пользователь:")
    print(auth_service.current_user())

    auth_service.sign_out(user1)
    # 4. Смена пользователя
    auth_service.sign_in(user2)
    print("\nПосле авторизации Bob:")
    print(auth_service.current_user())

    # 5. Автоавторизация (имитация перезапуска)
    auth_service2 = FileAuthService(auth_path=auth_path, repo_path=repo_path)
    print("\nПосле перезапуска программы (автоавторизация):")
    print(auth_service2.current_user())

    # 6. Удаление пользователя
    auth_service.sign_out(user2)
    print("\nПосле выхода Bob:")
    print(auth_service.current_user())


run_tests()
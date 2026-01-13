from typing import Optional, TypeVar, Generic, Sequence, List, Dict, Any
from dataclasses import dataclass, asdict, is_dataclass
from abc import ABC, abstractmethod
import json
from pathlib import Path


class HasId:
    id: int


@dataclass
class User(HasId):
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

    def __lt__(self, other: 'User') -> bool:
        return self.name < other.name


T = TypeVar("T", bound=HasId)


class IDataRepository(ABC, Generic[T]):
    @abstractmethod
    def get_all(self) -> List[T]:
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


class FileDataRepository(IDataRepository[T], Generic[T]):
    def __init__(self, file_path: str, cls_type: type[T]) -> None:
        self.file_path = Path(file_path)
        self.cls_type = cls_type

        if not self.file_path.exists():
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=4, ensure_ascii=False)

    def get_all(self) -> List[T]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [self.cls_type(**item) for item in data]

    def get_by_id(self, id: int) -> Optional[T]:
        items = self.get_all()

        for item in items:
            if item.id == id:
                return item

        return None

    def add(self, item: T) -> None:
        items = self.get_all()
        if self.get_by_id(item.id) is not None:
            return
        items.append(item)
        self._save_all(items)

    def update(self, item: T) -> None:
        items = self.get_all()
        existing_item = self.get_by_id(item.id)

        if existing_item is None:
            return

        idx = items.index(existing_item)
        items[idx] = item
        self._save_all(items)

    def delete(self, item: T) -> None:
        items = self.get_all()
        if item in items:
            items.remove(item)
            self._save_all(items)

    def _save_all(self, items: Sequence[T]) -> None:
        serialized_items: List[Dict[str, Any]] = []
        for item in items:
            if is_dataclass(item):
                serialized_items.append(asdict(item))
            else:
                raise TypeError(f"Cannot serialize non-dataclass object: {type(item)}")

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(serialized_items, f, indent=4, ensure_ascii=False)


class FileUserRepository(FileDataRepository[User], IUserRepository):
    def __init__(self, file_path: str) -> None:
        super().__init__(file_path, User)

    def get_by_login(self, login: str) -> Optional[User]:
        users = self.get_all()

        for user in users:
            if user.login == login:
                return user

        return None


@dataclass
class CurrentUser(HasId):
    id: int


class FileSaveCurrentUser(FileDataRepository[CurrentUser]):
    def __init__(self, file_path: str) -> None:
        super().__init__(file_path, CurrentUser)


class FileAuthService(IAuthService):
    def __init__(self, auth_path: str, repo_path: str) -> None:
        self.sgn = FileSaveCurrentUser(auth_path)
        self.repo = FileUserRepository(repo_path)

    def sign_in(self, user: User) -> None:
        if self.is_authorized:
            print("Sign out before sign in")
            return

        if self.repo.get_by_id(user.id) is None:
            print("No such user")
            return

        self.sgn.add(CurrentUser(user.id))

    def sign_out(self, user: User) -> None:
        current_user = CurrentUser(user.id)
        all_current = self.sgn.get_all()
        if current_user not in all_current:
            print("Sign in before sign out")
            return
        self.sgn.delete(current_user)

    @property
    def is_authorized(self) -> bool:
        sgn_users = self.sgn.get_all()
        return len(sgn_users) > 0

    @property
    def current_user(self) -> Optional[User]:
        if not self.is_authorized:
            return None

        all_current = self.sgn.get_all()
        return self.repo.get_by_id(all_current[-1].id)


def test():
    repo_path = "users.json"
    auth_path = "user.json"

    auth_service = FileAuthService(auth_path, repo_path)
    repo = FileUserRepository(repo_path)

    user1 = User(id=1, name="Василий Пупкин", login="vasyanpu", password="volodya", email="vasyan@kantiana.ru")
    user2 = User(id=2, name="Владимир Ленин", login="vilenin", password="revoludtion17",
                 address="Улица Пушкина, дом колотушкина")
    repo.add(user1)
    repo.add(user2)
    print("Все пользователи после добавления:")
    print(repo.get_all())

    user1.email = "vasyan@kantiana.ru"
    repo.update(user1)
    print("\nПосле редактирования Васи Пупкина:")
    print(repo.get_by_id(1))

    auth_service.sign_in(user1)
    print("\nАвторизован ли кто-то?", auth_service.is_authorized)
    print("Текущий пользователь:")
    print(auth_service.current_user)

    auth_service.sign_out(user1)
    auth_service.sign_in(user2)
    print("\nПосле авторизации Ленина:")
    print(auth_service.current_user)

    auth_service2 = FileAuthService(auth_path=auth_path, repo_path=repo_path)
    print("\nПосле перезапуска программы (автоавторизация):")
    print(auth_service2.current_user)

    auth_service.sign_out(user2)
    print("\nПосле выхода Ленин:")
    print(auth_service.current_user)


if __name__ == "__main__":
    test()
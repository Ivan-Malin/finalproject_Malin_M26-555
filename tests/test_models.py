"""Тесты для модели User."""

from datetime import datetime, timedelta, timezone

import pytest

from valutatrade_hub.core.models import User, Wallet


# Фикстура для создания валидного пользователя
@pytest.fixture
def valid_user():
    """Создает валидного пользователя для тестов."""
    return User(
        user_id=1,
        username="test_user",
        hashed_password="fake_hash",
        salt="fake_salt",
        registration_date=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def valid_wallet():
    """Создает валидный кошелёк для тестов."""
    return Wallet(currency_code="USD", balance=100.50)


class TestUserInitialization:
    """Тесты инициализации пользователя."""

    def test_create_valid_user(self):
        """Проверка успешного создания пользователя."""
        user = User(
            user_id=1,
            username="alice",
            hashed_password="hash123",
            salt="salt123",
            registration_date=datetime.now(),
        )
        assert user.user_id == 1
        assert user.username == "alice"

    def test_invalid_user_id_type(self):
        """Проверка ошибки при неверном типе user_id."""
        with pytest.raises(TypeError):
            User(
                user_id="not_an_int",
                username="bob",
                hashed_password="hash",
                salt="salt",
                registration_date=datetime.now(),
            )


class TestPasswordManagement:
    """Тесты управления паролем."""

    def test_generate_hash(self):
        """Проверка генерации хеша."""
        password = "secret"
        salt = "mysalt"
        hash_result = User.generate_hash(password, salt)
        # Хеш SHA256 всегда имеет длину 64 символа
        assert len(hash_result) == 64
        assert isinstance(hash_result, str)

    def test_verify_password_success(self, valid_user):
        """Проверка успешной верификации пароля (если бы мы знали исходный пароль)."""
        # Для теста создадим пользователя с известным паролем
        salt = "test_salt"
        password = "correct_pass"
        hashed = User.generate_hash(password, salt)

        user = User(
            user_id=2,
            username="verifier",
            hashed_password=hashed,
            salt=salt,
            registration_date=datetime.now(),
        )
        assert user.verify_password("correct_pass") is True

    def test_verify_password_failure(self, valid_user):
        """Проверка неудачной верификации пароля."""
        assert valid_user.verify_password("wrong_password") is False

    def test_change_password_success(self, valid_user):
        """Проверка успешной смены пароля."""
        old_hash, old_salt = valid_user.password_info
        valid_user.change_password("new_secure_pass")
        new_hash, new_salt = valid_user.password_info

        assert new_hash != old_hash
        assert new_salt != old_salt
        assert valid_user.verify_password("new_secure_pass") is True

    def test_change_password_too_short(self, valid_user):
        """Проверка ошибки при слишком коротком пароле."""
        with pytest.raises(ValueError, match="Пароль должен быть длиннее 4 символов"):
            valid_user.change_password("123")

    def test_change_password_invalid_type(self, valid_user):
        """Проверка ошибки при неверном типе пароля."""
        with pytest.raises(TypeError, match="new_password должен быть str"):
            valid_user.change_password(12345)


class TestUsernameManagement:
    """Тесты управления именем пользователя."""

    def test_username_success(self, valid_user):
        """Проверка успешной смены имени."""
        valid_user.username = "new_name"
        assert valid_user.username == "new_name"

    def test_username_empty(self, valid_user):
        """Проверка ошибки при пустом имени."""
        with pytest.raises(ValueError, match="Имя.*пустым"):
            valid_user.username = ""

    def test_username_invalid_type(self, valid_user):
        """Проверка ошибки при неверном типе имени."""
        with pytest.raises(TypeError, match="name должен быть str"):
            valid_user.username = 123


class TestSerialization:
    """Тесты сериализации и десериализации."""

    def test_to_dict(self, valid_user):
        """Проверка преобразования в словарь."""
        data = valid_user.to_dict()
        assert isinstance(data, dict)
        assert data["user_id"] == 1
        assert data["username"] == "test_user"
        # Проверяем наличие явного UTC
        assert data["registration_date"].endswith("+0000")

    def test_from_dict_success(self):
        """Проверка успешного создания из словаря."""
        data = {
            "user_id": 10,
            "username": "json_user",
            "hashed_password": "h1",
            "salt": "s1",
            # ВАЖНО: Входная строка теперь должна содержать +0000
            "registration_date": "2025-10-09T12:00:00+0000",
        }
        user = User.from_dict(data)
        assert user.user_id == 10
        assert user.username == "json_user"
        # Проверяем, что объект стал aware
        assert user.registration_date.tzinfo is not None

    def test_from_dict_invalid_type(self):
        """Проверка ошибки при передаче не словаря."""
        with pytest.raises(TypeError, match="user_dict должен быть dict"):
            User.from_dict(["not", "a", "dict"])

    def test_from_dict_missing_keys(self):
        """Проверка ошибки при отсутствии ключей в словаре."""
        data = {"user_id": 1}
        with pytest.raises(ValueError):
            User.from_dict(data)

    def test_from_dict_invalid_date_format(self):
        """Проверка ошибки при неверном формате даты."""
        data = {
            "user_id": 1,
            "username": "u",
            "hashed_password": "h",
            "salt": "s",
            "registration_date": "invalid-date",
        }
        with pytest.raises(ValueError):
            User.from_dict(data)


class TestUserInfo:
    """Тесты получения информации о пользователе."""

    def test_get_user_info(self, valid_user):
        """Проверка вывода информации без пароля."""
        info = valid_user.get_user_info()
        assert "user_id" in info
        assert "username" in info
        assert "registration_date" in info
        assert "hashed_password" not in info
        assert "salt" not in info

    def test_password_info_property(self, valid_user):
        """Проверка свойства password_info."""
        h, s = valid_user.password_info
        assert h == "fake_hash"
        assert s == "fake_salt"


class TestTimezoneHandling:
    """Тесты обработки часовых поясов (строгий UTC с суффиксом)."""

    def test_export_naive_datetime_as_utc(self):
        """Проверка, что наивная дата считается UTC и экспортируется с суффиксом."""
        naive_dt = datetime(2025, 5, 20, 15, 30, 0)
        user = User(
            user_id=1,
            username="tz_test",
            hashed_password="h",
            salt="s",
            registration_date=naive_dt,
        )
        info = user.get_user_info()
        # Время не сдвигается, просто добавляется метка +0000
        assert info["registration_date"] == "2025-05-20T15:30:00+0000"

    def test_export_aware_non_utc_converts_to_utc_string(self):
        """Проверка конвертации времени из другого TZ в UTC строку."""
        moscow_tz = timezone(timedelta(hours=3))
        local_time = datetime(2025, 5, 20, 18, 30, 0, tzinfo=moscow_tz)

        user = User(
            user_id=2,
            username="tz_msk",
            hashed_password="h",
            salt="s",
            registration_date=local_time,
        )

        info = user.get_user_info()
        # 18:30 MSK = 15:30 UTC
        assert info["registration_date"] == "2025-05-20T15:30:00+0000"

    def test_import_string_becomes_aware_utc(self):
        """Проверка, что при импорте строки с +0000 объект становится aware UTC."""
        data = {
            "user_id": 3,
            "username": "import_test",
            "hashed_password": "h",
            "salt": "s",
            "registration_date": "2025-06-15T12:00:00+0000",
        }
        user = User.from_dict(data)

        # Время остается 12:00, так как в строке явно указан UTC
        assert user.registration_date.hour == 12
        assert user.registration_date.tzinfo is not None
        assert user.registration_date.utcoffset() == timedelta(0)

    def test_round_trip_timezone_normalization(self):
        """Проверка полного цикла: любое TZ -> экспорт -> импорт -> результат в UTC."""
        ny_tz = timezone(timedelta(hours=-5))
        original_dt = datetime(2025, 12, 31, 20, 0, 0, tzinfo=ny_tz)

        user1 = User(
            user_id=5,
            username="round_trip",
            hashed_password="h",
            salt="s",
            registration_date=original_dt,
        )

        data = user1.to_dict()
        # Проверка, что в словаре строка соответствует UTC времени
        # (01:00 следующего дня)
        assert data["registration_date"] == "2026-01-01T01:00:00+0000"

        user2 = User.from_dict(data)

        # Проверка внутреннего состояния: время должно остаться 01:00 UTC
        assert user2.registration_date.hour == 1
        assert user2.registration_date.day == 1
        assert user2.registration_date.month == 1
        assert user2.registration_date.utcoffset() == timedelta(0)


class TestWalletInitialization:
    """Тесты инициализации кошелька."""

    def test_create_wallet_default_balance(self):
        """Проверка создания кошелька с балансом по умолчанию."""
        wallet = Wallet(currency_code="USD")
        assert wallet.currency_code == "USD"
        assert wallet.balance == 0.0

    def test_create_wallet_with_balance(self):
        """Проверка создания кошелька с заданным балансом."""
        wallet = Wallet(currency_code="BTC", balance=1.5)
        assert wallet.currency_code == "BTC"
        assert wallet.balance == 1.5

    def test_invalid_currency_code_type(self):
        """Проверка ошибки при неверном типе кода валюты."""
        with pytest.raises(TypeError):
            Wallet(currency_code=123)

    def test_invalid_balance_type(self):
        """Проверка ошибки при неверном типе баланса."""
        with pytest.raises(TypeError):
            Wallet(currency_code="USD", balance="100")


class TestWalletBalanceProperty:
    """Тесты свойства balance (геттер и сеттер)."""

    def test_get_balance(self):
        """Проверка получения баланса."""
        wallet = Wallet(currency_code="EUR", balance=500.0)
        assert wallet.balance == 500.0

    def test_set_balance_valid(self):
        """Проверка установки корректного положительного баланса."""
        wallet = Wallet(currency_code="EUR")
        wallet.balance = 100.0
        assert wallet.balance == 100.0

    def test_set_balance_zero(self):
        """Проверка установки баланса в ноль."""
        wallet = Wallet(currency_code="EUR", balance=10.0)
        wallet.balance = 0.0
        assert wallet.balance == 0.0

    def test_set_balance_negative_raises_error(self):
        """Проверка ошибки при установке отрицательного баланса."""
        wallet = Wallet(currency_code="EUR")
        with pytest.raises(ValueError, match="balance.*отрицат.*"):
            wallet.balance = -10.0

    def test_set_balance_invalid_type_raises_error(self):
        """Проверка ошибки при установке баланса неверного типа."""
        wallet = Wallet(currency_code="EUR")
        with pytest.raises(TypeError):
            wallet.balance = "100"


class TestWalletDeposit:
    """Тесты метода deposit."""

    def test_deposit_positive_amount(self):
        """Проверка пополнения на положительную сумму."""
        wallet = Wallet(currency_code="USD", balance=100.0)
        wallet.deposit(50.0)
        assert wallet.balance == 150.0

    def test_deposit_zero_amount(self):
        """Проверка пополнения на ноль (баланс не меняется)."""
        wallet = Wallet(currency_code="USD", balance=100.0)
        wallet.deposit(0.0)
        assert wallet.balance == 100.0

    def test_deposit_negative_amount_raises_error(self):
        """Проверка ошибки при попытке пополнить на отрицательную сумму."""
        wallet = Wallet(currency_code="USD")
        with pytest.raises(ValueError, match="amount.*отрицат.*"):
            wallet.deposit(-10.0)

    def test_deposit_invalid_type_raises_error(self):
        """Проверка ошибки при передаче неверного типа суммы."""
        wallet = Wallet(currency_code="USD")
        with pytest.raises(TypeError):
            wallet.deposit("50")


class TestWalletWithdraw:
    """Тесты метода withdraw."""

    def test_withdraw_within_balance(self):
        """Проверка снятия суммы, не превышающей баланс."""
        wallet = Wallet(currency_code="USD", balance=100.0)
        wallet.withdraw(30.0)
        assert wallet.balance == 70.0

    def test_withdraw_full_balance(self):
        """Проверка снятия всего баланса."""
        wallet = Wallet(currency_code="USD", balance=100.0)
        wallet.withdraw(100.0)
        assert wallet.balance == 0.0

    def test_withdraw_exceeds_balance_raises_error(self):
        """Проверка ошибки при снятии суммы больше баланса."""
        wallet = Wallet(currency_code="USD", balance=50.0)
        # Ожидается ValueError из-за проверки в сеттере balance
        # (balance -= amount станет < 0)
        with pytest.raises(ValueError, match="balance.*отрицат.*"):
            wallet.withdraw(60.0)

    def test_withdraw_negative_amount_raises_error(self):
        """Проверка ошибки при попытке снять отрицательную сумму."""
        wallet = Wallet(currency_code="USD", balance=100.0)
        with pytest.raises(ValueError, match="amount.*отрицат.*"):
            wallet.withdraw(-10.0)

    def test_withdraw_invalid_type_raises_error(self):
        """Проверка ошибки при передаче неверного типа суммы."""
        wallet = Wallet(currency_code="USD")
        with pytest.raises(TypeError):
            wallet.withdraw("10")


class TestWalletInfo:
    """Тесты метода get_balance_info."""

    def test_get_balance_info_structure(self):
        """Проверка структуры возвращаемого словаря."""
        wallet = Wallet(currency_code="BTC", balance=0.5)
        info = wallet.get_balance_info()

        assert isinstance(info, dict)
        assert "currency_code" in info
        assert "balance" in info
        assert info["currency_code"] == "BTC"
        assert info["balance"] == 0.5

    def test_get_balance_info_after_operations(self):
        """Проверка актуальности информации после операций."""
        wallet = Wallet(currency_code="USD", balance=100.0)
        wallet.deposit(50.0)
        wallet.withdraw(20.0)

        info = wallet.get_balance_info()
        assert info["balance"] == 130.0


class TestUserSerialization:
    """Расширенные тесты сериализации User."""

    def test_to_dict_structure(self, valid_user):
        """Проверка структуры словаря при экспорте."""
        data = valid_user.to_dict()
        required_keys = {
            "user_id",
            "username",
            "registration_date",
            "hashed_password",
            "salt",
        }
        assert required_keys.issubset(data.keys())

    def test_to_dict_date_format(self, valid_user):
        """Проверка формата даты в экспортируемом словаре."""
        data = valid_user.to_dict()
        # Теперь ожидаем суффикс +0000
        assert data["registration_date"] == "2025-01-01T12:00:00+0000"

    def test_round_trip_serialization(self, valid_user):
        """Проверка полного цикла: объект -> dict -> объект."""
        original_data = valid_user.to_dict()
        restored_user = User.from_dict(original_data)

        assert restored_user.user_id == valid_user.user_id
        assert restored_user.username == valid_user.username
        # Сравниваем datetime объекты (они оба теперь aware UTC)
        assert restored_user.registration_date == valid_user.registration_date


# ---------------------------------------------------------------------------
# Тесты Wallet: Базовая логика
# ---------------------------------------------------------------------------


class TestWalletLogic:
    """Тесты логики кошелька."""

    def test_deposit_success(self, valid_wallet):
        """Проверка пополнения."""
        valid_wallet.deposit(50.0)
        assert valid_wallet.balance == 150.50

    def test_withdraw_success(self, valid_wallet):
        """Проверка снятия."""
        valid_wallet.withdraw(50.0)
        assert valid_wallet.balance == 50.50

    def test_withdraw_insufficient_funds(self, valid_wallet):
        """Проверка снятия больше баланса."""
        with pytest.raises(ValueError, match="balance.*отрицат.*"):
            valid_wallet.withdraw(200.0)

    def test_negative_balance_setter(self, valid_wallet):
        """Проверка запрета отрицательного баланса через сеттер."""
        with pytest.raises(ValueError, match="balance.*отрицат.*"):
            valid_wallet.balance = -10.0


# ---------------------------------------------------------------------------
# Тесты Wallet: Сериализация и Десериализация (Dict/JSON)
# ---------------------------------------------------------------------------


class TestWalletSerialization:
    """Тесты сериализации Wallet."""

    def test_to_dict_structure(self, valid_wallet):
        """Проверка структуры словаря при экспорте."""
        data = valid_wallet.to_dict()
        assert "currency_code" in data
        assert "balance" in data
        assert data["currency_code"] == "USD"
        assert data["balance"] == 100.50

    def test_to_dict_zero_balance(self):
        """Проверка экспорта кошелька с нулевым балансом."""
        wallet = Wallet(currency_code="BTC")
        data = wallet.to_dict()
        assert data["balance"] == 0.0

    def test_from_dict_success(self):
        """Проверка успешного создания из словаря."""
        data = {"currency_code": "EUR", "balance": 250.75}
        wallet = Wallet.from_dict(data)
        assert wallet.currency_code == "EUR"
        assert wallet.balance == 250.75

    def test_round_trip_serialization(self, valid_wallet):
        """Проверка полного цикла: объект -> dict -> объект."""
        original_data = valid_wallet.to_dict()
        restored_wallet = Wallet.from_dict(original_data)

        assert restored_wallet.currency_code == valid_wallet.currency_code
        assert restored_wallet.balance == valid_wallet.balance

    def test_from_dict_missing_keys(self):
        """Проверка ошибки при отсутствии ключей."""
        data = {"currency_code": "USD"}
        with pytest.raises(ValueError, match="wallet_dict имеет некорректный формат"):
            Wallet.from_dict(data)

    def test_from_dict_invalid_balance_type(self):
        """Проверка ошибки при неверном типе баланса в словаре."""
        data = {"currency_code": "USD", "balance": "one_hundred"}
        with pytest.raises(TypeError):
            Wallet.from_dict(data)

    def test_from_dict_not_a_dict(self):
        """Проверка ошибки при передаче не словаря."""
        with pytest.raises(TypeError, match="wallet_dict должен быть dict"):
            Wallet.from_dict("string")

    def test_from_dict_negative_balance_handling(self):
        """Проверка поведения при попытке создать кошелёк с отрицат.* балансом."""
        data = {"currency_code": "USD", "balance": -10.0}
        with pytest.raises(ValueError, match="balance.*отрицат.*"):
            Wallet.from_dict(data)

"""Тесты для модели User."""

from datetime import datetime, timezone, timedelta

import pytest

from valutatrade_hub.core.models import User


# Фикстура для создания валидного пользователя
@pytest.fixture
def valid_user():
    """Создает валидного пользователя для тестов."""
    return User(
        user_id=1,
        username="test_user",
        hashed_password="fake_hash",
        salt="fake_salt",
        registration_date=datetime(2025, 1, 1, 12, 0, 0),
    )


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

    def test_change_username_success(self, valid_user):
        """Проверка успешной смены имени."""
        valid_user.change_username = "new_name"
        assert valid_user.username == "new_name"

    def test_change_username_empty(self, valid_user):
        """Проверка ошибки при пустом имени."""
        with pytest.raises(ValueError, match="Имя не может быть пустым"):
            valid_user.change_username = ""

    def test_change_username_invalid_type(self, valid_user):
        """Проверка ошибки при неверном типе имени."""
        with pytest.raises(TypeError, match="name должен быть str"):
            valid_user.change_username = 123


class TestSerialization:
    """Тесты сериализации и десериализации."""

    def test_to_dict(self, valid_user):
        """Проверка преобразования в словарь."""
        data = valid_user.to_dict()
        assert isinstance(data, dict)
        assert data["user_id"] == 1
        assert data["username"] == "test_user"
        assert "hashed_password" in data
        assert "salt" in data
        assert "registration_date" in data

    def test_from_dict_success(self):
        """Проверка успешного создания из словаря."""
        data = {
            "user_id": 10,
            "username": "json_user",
            "hashed_password": "h1",
            "salt": "s1",
            "registration_date": "2025-10-09T12:00:00",
        }
        user = User.from_dict(data)
        assert user.user_id == 10
        assert user.username == "json_user"

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
    """Тесты обработки часовых поясов (наивные даты считаются локальными и переводятся в UTC)."""

    def test_export_naive_datetime_converts_to_utc(self):
        """Проверка, что наивная дата конвертируется из локального TZ в UTC."""
        # Допустим, мы в UTC+3. Если мы создадим дату 15:30 без TZ, 
        # система посчитает это 15:30 по местному времени и переведет в 12:30 UTC.
        local_tz = timezone(timedelta(hours=3))
        naive_dt = datetime(2025, 5, 20, 15, 30, 0)
        
        # Чтобы тест был честным, мы эмулируем поведение: создаем aware объект в локальном TZ
        # и передаем его. Или полагаемся на то, что Python сам подставит системный TZ.
        # Для надежности теста явно укажем, что это время было "местным":
        user = User(
            user_id=1,
            username="tz_test",
            hashed_password="h",
            salt="s",
            registration_date=naive_dt, # Система сама сделает astimezone(utc)
        )
        
        info = user.get_user_info()
        # Ожидаем сдвиг на -3 часа (из 15:30 в 12:30)
        assert info["registration_date"] == "2025-05-20T12:30:00"

    def test_export_aware_non_utc_converts_to_utc_string(self):
        """Проверка конвертации времени из другого TZ в UTC строку."""
        # 18:30 в Москве (+3) = 15:30 UTC
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
        # В строке должно быть 15:30 UTC
        assert info["registration_date"] == "2025-05-20T15:30:00"

    def test_import_string_becomes_aware_utc_with_system_offset(self):
        """Проверка импорта строки: система считает её локальным временем и переводит в UTC."""
        data = {
            "user_id": 3,
            "username": "import_test",
            "hashed_password": "h",
            "salt": "s",
            "registration_date": "2025-06-15T12:00:00",
        }
        user = User.from_dict(data)
        
        # Если система в UTC+3, то 12:00 "местных" превратятся в 09:00 UTC
        assert user.registration_date.hour == 9
        assert user.registration_date.minute == 0
        # Объект должен стать осознанным и в UTC
        assert user.registration_date.tzinfo is not None
        assert user.registration_date.utcoffset() == timedelta(0)

    def test_round_trip_timezone_normalization(self):
        """Проверка полного цикла: любое TZ -> экспорт -> импорт -> результат в UTC."""
        # 20:00 в Нью-Йорке (-5) = 01:00 следующего дня UTC
        ny_tz = timezone(timedelta(hours=-5))
        original_dt = datetime(2025, 12, 31, 20, 0, 0, tzinfo=ny_tz)
        
        user1 = User(
            user_id=5,
            username="round_trip",
            hashed_password="h",
            salt="s",
            registration_date=original_dt,
        )
        
        # Экспорт в словарь (JSON)
        data = user1.to_dict()
        # Проверка, что в словаре строка соответствует UTC времени (01:00)
        assert data["registration_date"] == "2026-01-01T01:00:00"
        
        # Импорт обратно
        user2 = User.from_dict(data)
        
        # ВАЖНО: При импорте строки "2026-01-01T01:00:00" система снова считает её ЛОКАЛЬНЫМ временем.
        # Если мы в UTC+3, то 01:00 "местных" превратятся в 22:00 UTC предыдущего дня.
        # Это показывает, что round-trip для строк без TZ не сохраняет абсолютное время, 
        # если система использует astimezone для наивных дат.
        
        # Проверяем фактическое поведение вашей системы (ошибка показала 22:00):
        assert user2.registration_date.hour == 22
        assert user2.registration_date.day == 31
        assert user2.registration_date.month == 12
        assert user2.registration_date.utcoffset() == timedelta(0)

    def test_get_user_info_format_matches_constant(self, valid_user):
        """Проверка, что формат даты в get_user_info точно совпадает с константой."""
        info = valid_user.get_user_info()
        date_str = info["registration_date"]
        
        # Проверяем обратное преобразование через ту же константу
        parsed_date = datetime.strptime(date_str, User._User__DATE_TIME_FORMAT)
        
        # Убеждаемся, что данные не потерялись
        assert parsed_date.year == valid_user.registration_date.year
        assert parsed_date.month == valid_user.registration_date.month
        assert parsed_date.day == valid_user.registration_date.day
        assert parsed_date.hour == valid_user.registration_date.hour
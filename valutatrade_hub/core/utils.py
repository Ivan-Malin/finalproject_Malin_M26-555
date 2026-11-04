"""Содержит вспомогательные функции."""

from typing import Any


# Грязный хак питона
def get_var_name(var: Any) -> str:
    """Возвращает имя переменной в формате str."""
    return f"{var=}".split("=")[0]


def assert_var_isinstance_of_type(var: Any, var_type: type) -> None:
    """Проверяет на соответствие типа.

    Вызывает ошибку в случае несоответствия.
    Проверка идёт через наследование (isinstance).

    Args:
        var (Any): проверяемая переменная.
        var_type (type): требуемый тип переменной.

    Raises:
        TypeError: вызывается в случае несоответствия

    """
    var_name = get_var_name(var)
    var_real_type_name = type(var).__name__
    type_name = var_type.__name__

    # Частный случай, т.к. тут ещё bool отсеить нужно
    if var_type is int:
        if not isinstance(var, int) or isinstance(var, bool):
            msg = f"{var_name} должен быть int, а не {var_real_type_name}"
            raise TypeError(msg)
    elif not isinstance(var, var_type):
        msg = f"{var_name} должен быть {type_name}, а не {var_real_type_name}"
        raise TypeError(msg)

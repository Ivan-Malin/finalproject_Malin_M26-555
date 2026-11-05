"""Содержит вспомогательные функции."""

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, get_type_hints

P = ParamSpec("P")
R = TypeVar("R")


def assert_isinstance(var: Any, var_name: str, var_type: type) -> None:
    """Проверяет на соответствие типа.

    Вызывает ошибку в случае несоответствия.
    Проверка идёт через наследование (isinstance).

    Args:
        var (Any): проверяемая переменная.
        var_name (str): имя переменной.
        var_type (type): требуемый тип переменной.

    Raises:
        TypeError: вызывается в случае несоответствия

    """
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


def assert_non_negative(var: Any, var_name: str) -> None:
    """Проверяет на соответствие типа.

    Вызывает ошибку в случае отрицательности переменной.

    Args:
        var (Any): проверяемая переменная.
        var_name (str): имя переменной.

    Raises:
        ValueError: вызывается в случае отрицательного значения
        TypeError: вызывается если тип не поддерживает операцию сравнения

    """
    try:
        if var < 0:
            msg = f"{var_name} должен быть неотрицательным."
            raise ValueError(msg)
    except TypeError as e:
        msg = f"{var_name} не поддерживает операцию сравнения."
        raise TypeError(msg) from e


# god bless typing и inspect
def strict_arg_types[**P, R](func: Callable[P, R]) -> Callable[P, R | None]:
    """Декоратор для строгой проверки типов аргументов.

    Usage:
        @strict_arg_types
        def foo(arg: type, ...): ...

    Замечания:
        - Строго указывайте аргументы в объявлении функции
        - Не умеет работать с parameterized generic (т.е.
        dict[...], list[...], tuple[...] и прочие).
        Вместо этого либо используйте просто dict, list,
        tuple без [...], либо создавайте отдельнй класс обёртку.
        - Этот декоратор не спасает от комплексных случаев структур
        dict, list и прочих. Все эти случаи зависят от предметной
        области и неописуемы в пределах типов аргументов. Используйте
        дополнительные проверки для этих случаев.

    Raises:
        TypeError:
        - в случае если тип *arg* не соответствует заявленому *type*
        - в случае, если *type* является parameterized generic

    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # 1. Получаем словарь со всеми аннотированными именами
        type_hints = get_type_hints(func)

        # 2. Связываем переданные аргументы с их именами
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()  # Заполняет дефолтные значения, если их не передали

        # Словарь, где ключ — имя переменной, а значение — то, что передали
        actual_values = bound_args.arguments

        # 3. Перебираем имена, которые мы нашли в get_type_hints
        for param_name in type_hints:
            # Исключаем возвращаемое значение функции
            # (оно тоже есть в get_type_hints под ключом 'return')
            if param_name == "return":
                continue

            # Достаем значение аргумента по его имени
            param_value = actual_values.get(param_name)
            param_type = type_hints[param_name]

            assert_isinstance(param_value, param_name, param_type)

        return func(*args, **kwargs)

    return wrapper

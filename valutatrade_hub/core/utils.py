"""Содержит вспомогательные функции."""

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, get_args, get_origin, get_type_hints

P = ParamSpec("P")
R = TypeVar("R")


def assert_isinstance(var: Any, var_name: str, var_type: type) -> None:
    """Проверяет на соответствие типа.

    Вызывает ошибку в случае несоответствия.
    Проверка идёт через наследование (isinstance).

    Замечания:
        - Умеет работать с parameterized generic типа
        dict[...], list[...] и tuple[...]
        - Не умеет работать с прочими parameterized generic.

    Args:
        var (Any): проверяемая переменная.
        var_name (str): имя переменной.
        var_type (type): требуемый тип переменной.

    Raises:
        TypeError: вызывается в случае несоответствия

    """
    var_real_type_name = type(var).__name__

    # Извлекаем origin (базовый класс) и args (аргументы дженерика)
    origin = get_origin(var_type)
    args = get_args(var_type)

    # Если это parameterized generic, базовым типом для проверки становится origin
    base_type = origin if origin is not None else var_type
    type_name = getattr(base_type, "__name__", str(base_type))

    # 1. Проверяем базовый тип
    if base_type is int:
        # Частный случай, т.к. тут ещё bool отсеить нужно
        if not isinstance(var, int) or isinstance(var, bool):
            msg = f"{var_name} должен быть int, а не {var_real_type_name}"
            raise TypeError(msg)
    elif not isinstance(var, base_type):
        msg = f"{var_name} должен быть {type_name}, а не {var_real_type_name}"
        raise TypeError(msg)

    # 2. Проверяем аргументы generic типа
    __assert_generic_args_isinstance(
        var=var,
        var_name=var_name,
        origin=origin,
        args=args,
    )


def __assert_generic_args_isinstance(
    var: Any,
    var_name: str,
    origin: Any,
    args: list,
) -> None:
    """Проверяет аргументы объекта var типа parametrized generic на соответствие типа.

    Вызывает ошибку в случае несоответствия.
    Проверка идёт через наследование (isinstance).

    Args:
        var (Any): проверяемая переменная.
        var_name (str): имя переменной.
        origin (type): базовый тип parametrized generic объекта.
        args (type): аргументы parametrized generic объекта.

    Raises:
        TypeError: вызывается в случае несоответствия типов.

    """
    if origin is not None and args:
        # Случай dict: dict[key, value]
        if origin is dict:
            key_type, val_type = args[0], args[1]
            for key, val in var.items():
                assert_isinstance(key, f"Ключ {var_name}[{key!r}]", key_type)
                assert_isinstance(val, f"Значение {var_name}[{key!r}]", val_type)

        # Случай tuple/list: tuple/list[T, ...] или tuple/list[T1, T2, T3]
        elif origin is tuple or origin is list:
            # Проверяем на tuple[T, ...] (переменная длина)
            if len(args) == len(["T", "..."]) and args[1] is Ellipsis:
                item_type = args[0]
                for i, item in enumerate(var):
                    assert_isinstance(item, f"{var_name}[{i}]", item_type)
            else:
                # Фиксированная длина tuple[int, str]
                if len(var) != len(args):
                    msg = (
                        f"Длина кортежа {var_name} ({len(var)}) не совпадает "
                        "с ожидаемой длиной аннотации ({len(args)})"
                    )
                    raise TypeError(msg)
                for i, (item, item_type) in enumerate(zip(var, args, strict=False)):
                    assert_isinstance(item, f"{var_name}[{i}]", item_type)


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
        - Умеет работать с parameterized generic типа
        dict[...], list[...] и tuple[...]
        - Не умеет работать с прочими parameterized generic.
        - Этот декоратор не спасает от комплексных случаев структур
        dict, list и прочих. Все эти случаи зависят от предметной
        области и неописуемы в пределах типов аргументов. Используйте
        дополнительные проверки для этих случаев.

    Raises:
        TypeError:
        - в случае если тип *arg* не соответствует заявленому *type*
        - в случае, если *type* является parameterized generic и
        не один из dict[...], list[...] или tuple[...]

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

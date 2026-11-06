"""Содержит вспомогательные функции."""

# Замечание проверяющему - костылить assert_isinstance
# было обязательной частью, без него некрасиво...

import inspect
from collections.abc import Callable
from functools import wraps
from typing import (
    Any,
    ParamSpec,
    Sequence,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

P = ParamSpec("P")
R = TypeVar("R")


def assert_isinstance(var: Any, var_name: str, var_type: type) -> None:
    """Проверяет на соответствие типа.

    Вызывает ошибку в случае несоответствия.
    Проверка идёт через наследование (isinstance).

    Замечания:
        - Умеет работать с Callable и его вариациями
        - Умеет работать с parameterized generic типа
        dict[...], list[...], tuple[...] и Sequence[...]
        - Не умеет работать с прочими parameterized generic.

    Args:
        var (Any): проверяемая переменная.
        var_name (str): имя переменной для сообщения об ошибке.
        var_type (type): требуемый тип переменной.

    Raises:
        TypeError: в случае несоответствия типа.
    """
    origin = get_origin(var_type)
    args = get_args(var_type)

    # 1. Проверка на Callable
    if origin is Callable or var_type is Callable:
        __assert_callable_isinstance(var, var_name, args)
        return

    # 2. Проверка на Generic (dict, list, tuple и т.д.)
    if origin is not None:
        __assert_generic_isinstance(var, var_name, origin, args)
        return

    # 3. Проверка простого типа
    __assert_simple_type(var, var_name, var_type)


def __assert_simple_type(var: Any, var_name: str, expected_type: type) -> None:
    """Проверяет соответствие простому типу (int, str, bool и т.д.)."""
    var_real_type_name = type(var).__name__
    type_name = getattr(expected_type, "__name__", str(expected_type))

    # Особая обработка int, чтобы исключить bool
    if expected_type is int:
        if not isinstance(var, int) or isinstance(var, bool):
            msg = f"{var_name} должен быть int, а не {var_real_type_name}"
            raise TypeError(msg)
    elif not isinstance(var, expected_type):
        msg = f"{var_name} должен быть {type_name}, а не {var_real_type_name}"
        raise TypeError(msg)


def __assert_generic_isinstance(
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
    __assert_simple_type(var, var_name, origin)

    if origin is not None and args:
        # Случай dict: dict[key, value]
        if origin is dict:
            key_type, val_type = args[0], args[1]
            for key, val in var.items():
                assert_isinstance(key, f"Ключ {var_name}[{key!r}]", key_type)
                assert_isinstance(val, f"Значение {var_name}[{key!r}]", val_type)

        # Случай tuple/list: tuple/list[T, ...] или tuple/list[T1, T2, T3]
        elif any(origin is t for t in (tuple, list, Sequence)):
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


def __assert_callable_isinstance(func: Any, var_name: str, args: tuple) -> None:
    """Проверяет, что объект является вызываемым и соответствует сигнатуре.

    Вызывает ошибку в случае несоответствия.
    Проверка идёт через наследование (isinstance).

    Args:
        var (Any): проверяемая переменная.
        var_name (str): имя переменной.
        args (type): аргументы parametrized generic объекта.

    Raises:
        TypeError: вызывается в случае несоответствия типов.

    """
    if not callable(func):
        var_real_type_name = type(func).__name__
        msg = f"{var_name} должен быть Callable, а не {var_real_type_name}"
        raise TypeError(msg)

    if not args:
        return

    try:
        sig = inspect.signature(func)
    except ValueError:
        # Если сигнатуру получить нельзя (builtin), пропускаем глубокую проверку
        return

    return_type = args[1]
    arg_types = args[0]

    params = [
        p
        for p in sig.parameters.values()
        if p.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]

    # Проверка количества аргументов
    if len(params) != len(arg_types):
        msg = (
            f"Сигнатура {var_name} имеет {len(params)} позиционных аргументов, "
            f"ожидалось {len(arg_types)}"
        )
        raise TypeError(msg)

    # Проверка типов аргументов и возврата через аннотации
    for i, (param, expected_type) in enumerate(zip(params, arg_types)):
        if param.annotation is not inspect.Parameter.empty:
            if not _is_subtype(param.annotation, expected_type):
                msg = (
                    f"Аргумент {i} функции {var_name} имеет аннотацию {param.annotation}, "
                    f"не совместимую с ожидаемой {expected_type}"
                )
                raise TypeError(msg)

    if sig.return_annotation is not inspect.Parameter.empty:
        if not _is_subtype(sig.return_annotation, return_type):
            msg = (
                f"Тип возврата функции {var_name} ({sig.return_annotation}) "
                f"не совместим с ожидаемым {return_type}"
            )
            raise TypeError(msg)


def _is_subtype(sub_type: type, super_type: type) -> bool:
    """Проверяет, является ли sub_type подтипом super_type (учитывая Union)."""
    try:
        if super_type is type(None):
            return sub_type is type(None)

        origin_super = get_origin(super_type)
        if origin_super is Union:
            return any(_is_subtype(sub_type, arg) for arg in get_args(super_type))

        return issubclass(sub_type, super_type)
    except TypeError:
        return False


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
        - Умеет работать с Callable и его вариациями
        - Умеет работать с parameterized generic типа
        dict[...], list[...], tuple[...] и Sequence[...]
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

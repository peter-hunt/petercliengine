from re import fullmatch
from types import GenericAlias, UnionType
from typing import Any, Callable, get_args


__all__ = [
    "catch_interrupt",
    "catch_interrupt_with_api",
    "catch_interrupt_silent",
    "TypeLike",
    "istype",
]


def catch_interrupt(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (EOFError, KeyboardInterrupt):
            print("\nProcess interrupted.")
    wrapper.__doc__ = func.__doc__
    wrapper.__annotations__ = func.__annotations__
    return wrapper


def catch_interrupt_with_api(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (EOFError, KeyboardInterrupt):
            print("\nProcess interrupted.")
            return {"type": "interrupted"}
    wrapper.__doc__ = func.__doc__
    wrapper.__annotations__ = func.__annotations__
    return wrapper


def catch_interrupt_silent(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (EOFError, KeyboardInterrupt) as error:
            return
    return wrapper


# tuple support is only to work on top of isinstance()
type TypeLike = (
    None | type | tuple[type | UnionType | GenericAlias, ...]
    | UnionType | GenericAlias
)


def istype(obj: object, type_: TypeLike, /) -> bool:
    if type_ is any or type_ is Any:
        return True
    elif type_ is None:
        return obj is None
    elif isinstance(type_, type):
        return isinstance(obj, type_)
    elif isinstance(type_, tuple):
        return any(istype(obj, subtype) for subtype in type_)
    elif isinstance(type_, UnionType):
        return any(istype(obj, subtype) for subtype in get_args(type_))
    elif isinstance(type_, GenericAlias):
        if not isinstance(obj, type_.__origin__):
            return False
        args = get_args(type_)
        if type_.__origin__ is tuple:
            if any(type_arg is Ellipsis for i, type_arg in enumerate(args) if i != 1):
                raise ValueError("\"...\" is allowed only as the"
                                 " second of two arguments")
            elif Ellipsis in args and len(args) != 2:
                raise ValueError("\"...\" is allowed only as the"
                                 " second of two arguments")
            if len(args) == 1 and args[0] == ():
                return obj == ()
            if len(args) == 2:
                if args[1] is Ellipsis:
                    return all(istype(item, args[0]) for item in type_)
            return len(obj) == len(args) and all(
                istype(item, subtype)
                for item, subtype in zip(obj, args)
            )
        elif type_.__origin__ is list:
            return all(istype(item, args)
                       for item in obj)
        elif type_.__origin__ is set:
            return all(istype(item, args)
                       for item in obj)
        elif type_.__origin__ is dict:
            return all(istype(key, args[0]) and istype(value, args[1])
                       for key, value in obj.items())
        else:
            raise TypeError(
                f"unrecognized generic alias origin:"
                f" {type_.__origin__.__name__}"
            )
    else:
        raise TypeError(
            f"istype() arg 2 must be a type_, a tuple of types,"
            f" a union, or a generic alias, not {type(type_).__name__}"
        )


@catch_interrupt
def match_input(pattern: str, /, strip: bool = False) -> str:
    while True:
        string = input(":> ")
        if strip:
            string = string.strip()
        if fullmatch(pattern, string):
            return string
        print("Invalid format, try again.")

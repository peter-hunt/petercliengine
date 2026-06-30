from re import fullmatch
from types import GenericAlias, UnionType
from typing import Any, Callable, ParamSpec, TypeVar, cast, get_args

_P = ParamSpec("_P")
_T = TypeVar("_T")


__all__ = [
    "catch_interrupt",
    "catch_interrupt_with_api",
    "catch_interrupt_silent",
    "TypeLike",
    "istype",
    "match_input",
]


def catch_interrupt(func: Callable[_P, _T]) -> Callable[_P, _T | None]:
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T | None:
        try:
            return func(*args, **kwargs)
        except (EOFError, KeyboardInterrupt):
            print("\nProcess interrupted.")
            return None
    wrapper.__doc__ = func.__doc__
    wrapper.__annotations__ = func.__annotations__
    return wrapper


def catch_interrupt_with_api(func: Callable[_P, Any]) -> Callable[_P, Any]:
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except (EOFError, KeyboardInterrupt):
            print("\nProcess interrupted.")
            return {"type": "interrupted"}
    wrapper.__doc__ = func.__doc__
    wrapper.__annotations__ = func.__annotations__
    return wrapper


def catch_interrupt_silent(func: Callable[_P, _T]) -> Callable[_P, _T | None]:
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T | None:
        try:
            return func(*args, **kwargs)
        except (EOFError, KeyboardInterrupt):
            return None
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
        if not isinstance(obj, type_.__origin__):  # type: ignore[arg-type]
            return False
        args = get_args(type_)
        if type_.__origin__ is tuple:
            obj_tuple = cast("tuple[Any, ...]", obj)
            if any(type_arg is Ellipsis for i, type_arg in enumerate(args) if i != 1):
                raise ValueError("\"...\" is allowed only as the"
                                 " second of two arguments")
            elif Ellipsis in args and len(args) != 2:
                raise ValueError("\"...\" is allowed only as the"
                                 " second of two arguments")
            if len(args) == 1 and args[0] == ():
                return obj_tuple == ()
            if len(args) == 2:
                if args[1] is Ellipsis:
                    return all(istype(item, args[0]) for item in obj_tuple)
            return len(obj_tuple) == len(args) and all(
                istype(item, subtype)
                for item, subtype in zip(obj_tuple, args)
            )
        elif type_.__origin__ is list:
            return all(istype(item, args[0])
                       for item in cast("list[Any]", obj))
        elif type_.__origin__ is set:
            return all(istype(item, args[0])
                       for item in cast("set[Any]", obj))
        elif type_.__origin__ is dict:
            return all(istype(key, args[0]) and istype(value, args[1])
                       for key, value in cast("dict[Any, Any]", obj).items())
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


def main() -> None:
    print("--- istype ---")
    print(istype("hello", str))                  # True
    print(istype(42, int | str))                 # True
    print(istype(["a", "b"], list[str]))         # True
    print(istype({1, 2}, set[int]))              # True
    print(istype({"x": True}, dict[str, bool]))  # True
    print(istype(42, str))                       # False
    print(istype(["a", 1], list[str]))           # False

    print("\n--- catch_interrupt_with_api ---")

    @catch_interrupt_with_api
    def risky() -> None:
        raise KeyboardInterrupt

    print(risky())  # {'type': 'interrupted'}

    print("\n--- catch_interrupt_silent ---")

    @catch_interrupt_silent
    def quiet() -> None:
        raise KeyboardInterrupt

    print(quiet())  # None


if __name__ == "__main__":
    main()

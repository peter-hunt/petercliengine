from collections.abc import Callable
from io import TextIOWrapper
from re import fullmatch
from typing import Any

from myjson import load as json_load, dump as json_dump
from str_convert import to_snake_case
from utils import TypeLike, istype


__all__ = [
    "Variable", "get_var",
    "DataType",
]


Immutable = int | float | complex | bool | str | tuple | bytes | range | frozenset


class Variable:
    name: str
    type: TypeLike
    default: Any | None
    default_factory: Callable[[], Any] | None
    validator: Callable[[Any], bool] | None
    loader: Callable[[Any], dict] | None
    dumper: Callable[[Any], dict] | None

    def __init__(self, name: str, type: TypeLike,
                 default: Any | None = None, default_factory: Callable | None = None,
                 validator: Callable[[Any], bool] | None = None,
                 loader: Callable[[Any], dict] | None = None,
                 dumper: Callable[[Any], dict] | None = None):
        if not fullmatch(r"[A-Za-z_]\w*", name):
            raise NameError(
                f"variable name must be contain only letters,"
                f" non-leading digits, and underscores, not {name!r}")
        if name in DataType.__annotations__:
            raise NameError(
                f"cannot override DataType class attribute: {name}")
        if name == "type":
            raise NameError("variable 'type' is reserved for JSON dumping")
        if name == "datatype_id":
            raise NameError(
                "variable 'datatype_id' is reserved for DataType identification")
        if name == "variables":
            raise NameError(
                "variable 'variable' is reserved for DataType variables storing")
        if name == "DUMP_DEFAULTS":
            raise NameError(
                "variable 'DUMP_DEFAULTS' is reserved for DataType dumping")
        self.name = name
        self.type = type
        if default is not None and default_factory is not None:
            raise ValueError(
                "both default and default_factory are given, conflict")
        self.default = default
        self.default_factory = default_factory
        self.optional = self.default is not None or self.default_factory is not None
        self.validator = validator
        self.loader = loader
        self.dumper = dumper

    @property
    def default_value(self):
        if self.default is not None:
            return self.default
        elif self.default_factory is not None:
            return self.default_factory()
        else:
            raise ValueError(f"default value not provided"
                             f" for variable {self.name!r}")

    def load(self, value: any, /):
        return value if self.loader is None else self.loader(value)

    def dump(self, value: any, /):
        return value if self.dumper is None else self.dumper(value)

    def validate(self, value: any, /):
        return True if self.validator is None else self.validator(value)


def get_var(variables: list[Variable], name: str, /) -> Variable | None:
    """
    Find and return the first variable that has the given name.
    Returns None if no variable with the given name is found.

    :param variables: The list of variables.
    :type variables: list[Variable]
    :param name: The name of the target variable.
    :type name: str
    :return: The target variable, if found, otherwise, None.
    :rtype: Variable | None
    """
    for var in variables:
        if var.name == name:
            return var


class DataType:
    datatype_id: str
    variables: list[Variable]
    DUMP_DEFAULTS: bool = False

    def __init_subclass__(cls):
        if "datatype_id" not in cls.__dict__:
            cls.datatype_id = to_snake_case(cls.__name__)
        if "variables" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must define class attribute 'variables'")
        variables = cls.variables
        for var in variables:
            if not isinstance(var, Variable):
                raise TypeError(
                    f"{cls.__name__}.variables must only contain"
                    f" Variable instances, not {type(var).__name__}: {var}")
            if var.name in DataType.__annotations__:
                raise NameError(
                    f"variable {var.name!r} is reserved for DataType"
                    f" class attribute: cannot be used")
        used_names = {*()}
        seen_optional = False
        for var in variables:
            if var.name in used_names:
                raise TypeError(f"{cls.__name__} contains multiple variables"
                                f" of the same name: {var.name}")
            used_names.add(var.name)
            if seen_optional and not var.optional:
                raise TypeError(f"variable without a default follows"
                                f" variable with a default: {var.name}")
            elif var.optional:
                seen_optional = True
            if var.default is not None and not isinstance(var.default, Immutable):
                raise ValueError(
                    f"for mutable default values, use getter functions with"
                    f" default_factory instead of default: {var.name}")

    def __init__(self, *args, **kwargs):
        if len(args) + len(kwargs) > len(self.variables):
            raise TypeError(f"{self.__class__.__name__}() takes at most"
                            f" {len(self.variables)} arguments"
                            f" ({len(args) + len(kwargs)} given)")

        used_names = {*()}
        for i, value in enumerate(args):
            var = self.variables[i]
            used_names.add(var.name)
            if not istype(value, var.type):
                raise TypeError(
                    f"expected {var.type} for variable"
                    f" {var.name!r}, got {value} ({type(value).__name__})")
            if not istype(value, var.type):
                raise TypeError(
                    f"variable {var.name!r} obtained value {value!r},"
                    f" which is not of type {var.type}")
            if var.validator is not None:
                if not var.validator(value):
                    raise ValueError(
                        f"invalid value for variable {var.name!r}: {value!r}")
            setattr(self, var.name, value)

        for key, value in kwargs.items():
            var = get_var(self.variables, key)
            if var is None:
                raise TypeError(
                    f"{self.__class__.__name__}() got an unexpected"
                    f" keyword argument {key!r}")
            if key in used_names:
                raise TypeError(
                    f"{self.__class__.__name__}() got multiple"
                    f" values for argument {var.name!r}")
            if not istype(value, var.type):
                raise TypeError(f"variable {var.name!r} obtained value {value!r},"
                                f" which is not of type {var.type}")
            if var.validator is not None:
                if not var.validator(value):
                    raise ValueError(
                        f"invalid value for variable {var.name!r}: {value!r}")
            used_names.add(var.name)
            setattr(self, key, value)

        for pos, var in enumerate(self.variables, 1):
            if var.optional:
                break
            elif var.name not in used_names:
                raise TypeError(
                    f"{self.__class__.__name__}() missing required"
                    f" argument {var.name!r} (pos {pos})")
        for var in self.variables:
            if var.optional and not hasattr(self, var.name):
                setattr(self, var.name, var.default_value)

    def __repr__(self):
        result = f"{self.__class__.__name__}("
        result += ", ".join(
            f"{var.name}={getattr(self, var.name)!r}"
            for var in self.variables
        )
        return result + ')'

    def __str__(self):
        result = f"{self.__class__.__name__}("
        result += ", ".join(
            f"{getattr(self, var.name)!r}"
            for var in self.variables
        )
        return result + ')'

    def dumps(self):
        result = {}
        for var in self.variables:
            if not self.DUMP_DEFAULTS and var.optional:
                if getattr(self, var.name) == var.default_value:
                    continue
            result[var.name] = var.dump(getattr(self, var.name))
        result["type"] = self.datatype_id
        return result

    def dump(self, file: TextIOWrapper, /):
        json_dump(self.dumps(), file)

    @classmethod
    def loads(cls, obj: dict[str, any], /):
        if "type" not in obj:
            raise TypeError(f"type tag missing from data.")
        elif obj["type"] != cls.datatype_id:
            raise TypeError(f"expected type tag {cls.datatype_id!r},"
                            f" got {obj['type']}")
        values = []
        for var in cls.variables:
            if var.name in obj:
                values.append(var.load(obj[var.name]))
            elif var.optional:
                values.append(var.default_value)
            else:
                raise NameError(f"variable {var.name!r} not found from data.")
        return cls(*values)

    @classmethod
    def load(cls, file: TextIOWrapper, /):
        return cls.loads(json_load(file))

    @classmethod
    def is_valid(cls, obj: dict[str, any]):
        if not istype(obj, dict[str, any]):
            return False
        if "type" not in obj or obj["type"] != cls.datatype_id:
            return False
        for var in cls.variables:
            if var.name not in obj and not var.optional:
                return False
        for var in cls.variables:
            if var.name not in obj:
                continue
            value = obj[var.name]
            try:
                loaded_value = var.load(value)
            except:
                return False
            if not istype(loaded_value, var.type):
                return False
            if not var.validate(loaded_value):
                return False
        return True


def main():
    class Sword(DataType):
        variables = [
            Variable("name", str),
            Variable("damage", int),
            Variable("knockback", int, 0),
            Variable("lores", list[str], default_factory=lambda: []),
        ]

    a = Sword("Errata", 133)
    b = Sword("Byakko", 100)
    print(a)
    print(b)
    a.lores.append("It was worth the wait.")
    b.lores.append("Spent most of the time collecting dust on Wakako's desk.")
    b.lores.append("Except for the occasional heated negotiation.")
    print(a)
    print(b)


if __name__ == "__main__":
    main()

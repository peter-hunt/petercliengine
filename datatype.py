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
    """Represents a typed, named variable definition for use in DataType subclasses.

    Attributes:
        name (str): The identifier name of the variable.
        type (TypeLike): The expected type of the variable's value.
        default (Any | None): A static default value, or None if not set.
        default_factory (Callable[[], Any] | None): A callable that produces a
            default value, or None if not set.
        validator (Callable[[Any], bool] | None): An optional callable that
            validates a given value, or None to skip validation.
        loader (Callable[[Any], dict] | None): An optional callable to transform
            a value on load, or None to use the raw value.
        dumper (Callable[[Any], dict] | None): An optional callable to transform
            a value on dump, or None to use the raw value.
    """

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
        """Initializes a Variable with the given name, type, and optional fields.

        Args:
            name (str): The identifier name of the variable. Must match
                ``[A-Za-z_]\\w*`` and must not conflict with reserved names.
            type (TypeLike): The expected type for values assigned to this variable.
            default (Any | None): A static default value. Mutually exclusive with
                ``default_factory``. Must be an immutable type if provided.
            default_factory (Callable | None): A zero-argument callable that produces
                a default value. Mutually exclusive with ``default``.
            validator (Callable[[Any], bool] | None): An optional callable that
                returns True if the value is valid, False otherwise.
            loader (Callable[[Any], dict] | None): An optional callable to transform
                incoming values during loading.
            dumper (Callable[[Any], dict] | None): An optional callable to transform
                values during dumping.

        Raises:
            NameError: If ``name`` is not a valid Python identifier, conflicts with
                a reserved ``DataType`` attribute, or is one of the reserved names
                ``'type'``, ``'datatype_id'``, ``'variables'``, or
                ``'DUMP_DEFAULTS'``.
            ValueError: If both ``default`` and ``default_factory`` are provided.
        """
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
        """The resolved default value for this variable.

        Returns the static ``default`` if set, otherwise calls ``default_factory``
        to produce the value.

        Returns:
            Any: The default value.

        Raises:
            ValueError: If neither ``default`` nor ``default_factory`` is set.
        """
        if self.default is not None:
            return self.default
        elif self.default_factory is not None:
            return self.default_factory()
        else:
            raise ValueError(f"default value not provided"
                             f" for variable {self.name!r}")

    def load(self, value: Any, /):
        """Transforms a raw value using the loader, if one is defined.

        Args:
            value: The raw value to load.

        Returns:
            Any: The transformed value, or the original value if no loader is set.
        """
        return value if self.loader is None else self.loader(value)

    def dump(self, value: Any, /):
        """Transforms a value using the dumper, if one is defined.

        Args:
            value: The value to dump.

        Returns:
            Any: The transformed value, or the original value if no dumper is set.
        """
        return value if self.dumper is None else self.dumper(value)

    def validate(self, value: Any, /):
        """Validates a value using the validator, if one is defined.

        Args:
            value: The value to validate.

        Returns:
            bool: True if the value is valid or no validator is set, otherwise
                the result of calling the validator.
        """
        return True if self.validator is None else self.validator(value)


def get_var(variables: list[Variable], name: str, /) -> Variable | None:
    """Finds and returns the first variable in a list with the given name.

    Args:
        variables (list[Variable]): The list of variables to search.
        name (str): The name of the target variable.

    Returns:
        Variable | None: The matching variable, or None if not found.
    """
    for var in variables:
        if var.name == name:
            return var


class DataType:
    """Base class for defining structured data types with typed, named variables.

    Subclasses must define a ``variables`` class attribute as a list of
    ``Variable`` instances. A ``datatype_id`` class attribute is auto-generated
    from the subclass name in snake_case if not explicitly provided.

    Attributes:
        datatype_id (str): A unique string identifier, defaulting to the
            snake_case form of the class name.
        variables (list[Variable]): The ordered list of ``Variable`` definitions
            for this data type.
        DUMP_DEFAULTS (bool): Whether to include default values when dumping.
            Defaults to False.
    """

    datatype_id: str
    variables: list[Variable]
    DUMP_DEFAULTS: bool = False

    def __init_subclass__(cls):
        """Validates and configures a DataType subclass when it is defined.

        Automatically assigns ``datatype_id`` from the class name if not explicitly
        defined. Validates that ``variables`` is declared and contains only valid,
        uniquely named ``Variable`` instances, and that required variables do not
        follow optional ones.

        Raises:
            TypeError: If ``variables`` is not defined, contains non-Variable items,
                if a required variable follows an optional variable, or if duplicate
                variable names are found.
            NameError: If a variable name conflicts with a reserved DataType
                class attribute.
            ValueError: If a variable with a mutable default value uses ``default``
                instead of ``default_factory``.
        """
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
        """Instantiates a DataType with positional and/or keyword argument values.

        Validates argument count, types, and constraints against the defined
        ``variables``, then sets each value as an instance attribute. Missing
        optional variables are set to their default values.

        Args:
            *args: Positional values corresponding to the declared variables
                in order.
            **kwargs: Keyword values for declared variables by name.

        Raises:
            TypeError: If too many arguments are provided, an unexpected keyword
                argument is given, an argument is supplied more than once, a
                required variable is missing, or a value is of the wrong type.
            ValueError: If a value fails its variable's validator.
        """
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
        """Returns a string representation of the DataType instance.

        Returns:
            str: A string in the form ``ClassName(var1=val1, var2=val2, ...)``.
        """
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
    def loads(cls, obj: dict[str, Any], /):
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
    def is_valid(cls, obj: dict[str, Any]):
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

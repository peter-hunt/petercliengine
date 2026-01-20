from re import sub


__all__ = [
    "to_snake_case",
]


def to_snake_case(name):
    s1 = sub(r"[- ]", '_', name)
    s2 = sub(r"([^_])([A-Z][a-z]+)", r"\1_\2", s1)
    s3 = sub(r"([a-z0-9])([A-Z])", r"\1_\2", s2).lower()
    return s3.lower()


def main():
    print(to_snake_case("camelCaseString"))
    print(to_snake_case("PascalCase"))
    print(to_snake_case("some mixed_string"))
    print(to_snake_case("HTTPRequest"))


if __name__ == "__main__":
    main()

from re import sub


__all__ = [
    "to_snake_case",
    "to_camel_case",
    "to_pascal_case",
    "to_title_case",
    "to_kebab_case",
]


def to_snake_case(name: str) -> str:
    s1 = sub(r"[- ]", '_', name)
    s2 = sub(r"([^_])([A-Z][a-z]+)", r"\1_\2", s1)
    s3 = sub(r"([a-z0-9])([A-Z])", r"\1_\2", s2).lower()
    return s3.lower()


def to_camel_case(name: str) -> str:
    words = to_snake_case(name).split('_')
    return words[0] + ''.join(w.capitalize() for w in words[1:])


def to_pascal_case(name: str) -> str:
    return ''.join(w.capitalize() for w in to_snake_case(name).split('_'))


def to_title_case(name: str) -> str:
    return ' '.join(w.capitalize() for w in to_snake_case(name).split('_'))


def to_kebab_case(name: str) -> str:
    return to_snake_case(name).replace('_', '-')


def main():
    samples = [
        "camelCaseString",
        "PascalCase",
        "some mixed_string",
        "HTTPRequest",
    ]
    for s in samples:
        print(f"{s!r:30} -> snake={to_snake_case(s)!r:25}"
              f" camel={to_camel_case(s)!r:25}"
              f" pascal={to_pascal_case(s)!r:25}"
              f" title={to_title_case(s)!r:25}"
              f" kebab={to_kebab_case(s)!r}")


if __name__ == "__main__":
    main()

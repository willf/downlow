#!/usr/bin/env python3


def foo(bar: str) -> str:
    """Summary line.

    Extended description of function.

    Args:
        bar: Description of input argument.

    Returns:
        Description of return value
    """

    return bar


def main() -> None:
    """Main function."""
    print(foo("Hello, World!"))


if __name__ == "__main__":  # pragma: no cover
    main()

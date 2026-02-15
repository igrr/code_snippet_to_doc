import sys


def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"


def main():
    if len(sys.argv) > 1:
        print(greet(sys.argv[1]))
    else:
        print(greet("World"))


if __name__ == "__main__":
    main()

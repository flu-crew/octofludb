from termcolor import colored


def good(text: str) -> str:
    """
    Color text green for UNIX terminal using ANSI escape codes
    """
    coloredText = colored(text, "green", attrs=["bold"])
    return coloredText


def bad(text: str) -> str:
    """
    Color text red for UNIX terminal using ANSI escape codes
    """
    coloredText = colored(text, "red", attrs=["bold"])
    return coloredText

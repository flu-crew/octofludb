from termcolor import colored


def good(text):
    coloredText = colored(text, "green", attrs=["bold"])
    return coloredText


def bad(text):
    coloredText = colored(text, "red", attrs=["bold"])
    return coloredText

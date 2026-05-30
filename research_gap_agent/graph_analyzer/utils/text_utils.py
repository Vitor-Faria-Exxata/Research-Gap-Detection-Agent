import re


def normalize(text):
    text = text.lower().strip()

    text = re.sub(r"\s+", " ", text)

    text = text.replace("-", " ")

    return text
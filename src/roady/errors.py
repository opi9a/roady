"""
Use try/except to catch specific errors - eg:
    >>> x = 5 / 0
    ZeroDivisionError     Traceback (most recent call last)
    line 1
    ----> 1 5 / 0
    ZeroDivisionError: division by zero


    >>> try:
            x = 5 / 0
        except ZeroDivisionError as e:
            print(e)
    division by zero

while
    >>> try:
            x = 5 / 0
        except TypeError as e:
            print(e)
    division by zero
"""


class DownloadError(Exception):
    pass

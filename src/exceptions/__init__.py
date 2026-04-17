import sys
import time
from functools import wraps
from typing import Type, Container

from classeviva.eccezioni import ErroreHTTP404, ErroreHTTP
AppException = Type[BaseException | ErroreHTTP | ErroreHTTP404]

# decorator to flag API calls that might result in errors, and re-making them in case
def retry_on(
    exceptions: Type[AppException] | Container[AppException],
    *,
    max_attempts: int = 5,
    delay: float = 0.5,
    backoff: float = 1.5
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            wait = delay
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    attempts += 1
                    if attempts >= max_attempts: raise
                    time.sleep(wait)
                    wait *= backoff
        return wrapper
    return decorator


def format_exception(exc_type, exc_value, exc_traceback):
    import traceback
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    return ''.join(tb_lines)

def custom_excepthook(exc_type, exc_value, exc_traceback):
    if exc_type is KeyboardInterrupt:
        return

    from src.gui import PopupMaster
    PopupMaster().showErrorPopup(
        message=f"{exc_type.__name__}: {exc_value}",
        tb=format_exception(exc_type, exc_value, exc_traceback)
    ).show_modal()

sys.excepthook = custom_excepthook
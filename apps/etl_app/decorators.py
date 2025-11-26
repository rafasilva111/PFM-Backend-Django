from peewee import OperationalError
import time

def retry_on_db_lock(func, retries=5, delay=0.1, backoff=2):
    def wrapped(*args, **kwargs):
        current_delay = delay

        for attempt in range(1, retries + 1):
            try:
                return func(*args, **kwargs)

            except OperationalError as e:
                if "database is locked" not in str(e):
                    raise  # some other error

                if attempt == retries:
                    raise  # out of retries

                time.sleep(current_delay)
                current_delay *= backoff  # increase delay

        # should never reach here
    return wrapped

import json
import logging


class OrderError(Exception):
    """Base exception for the orders domain."""


class ConfigError(OrderError):
    """Configuration loading or parsing error."""

    def __init__(self, message, path=None):
        super().__init__(message)
        self.path = path


class PaymentError(OrderError):
    """Payment processing error."""

    def __init__(self, message, transaction_id=None):
        super().__init__(message)
        self.transaction_id = transaction_id


class ParseOrdersError(OrderError):
    """Error during order parsing; carries partial results and error count."""

    def __init__(self, message, partial_result=None, error_count=0):
        super().__init__(message)
        self.partial_result = partial_result
        self.error_count = error_count


def load_config(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise ConfigError(f"Configuration file not found: {path}", path=path) from e
    except PermissionError as e:
        raise ConfigError(
            f"Permission denied reading configuration: {path}", path=path
        ) from e
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"Invalid JSON in configuration: {path}", path=path
        ) from e


def charge(order, gateway):
    try:
        return gateway.charge(order.total)
    except (ConnectionError, TimeoutError) as e:
        logging.error("charge failed: %s", e)
        raise PaymentError(f"Payment failed for order") from e


def parse_orders(lines):
    result = []
    errors = 0
    for line in lines:
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError as e:
            errors += 1
            logging.warning("skipping malformed line: %s", e)
            continue
    if errors:
        raise ParseOrdersError(
            f"parse_orders: {errors} malformed line(s) skipped",
            partial_result=result,
            error_count=errors,
        )
    return result


def read_amount(raw):
    try:
        return float(raw)
    except ValueError as e:
        raise RuntimeError("bad amount") from e

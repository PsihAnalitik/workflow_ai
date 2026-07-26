import json
import logging

def load_config(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}

def charge(order, gateway):
    try:
        return gateway.charge(order.total)
    except Exception as e:
        logging.error("charge failed: %s", e)

def parse_orders(lines):
    result = []
    for line in lines:
        try:
            result.append(json.loads(line))
        except ValueError:
            continue
    return result

def read_amount(raw):
    try:
        return float(raw)
    except ValueError as e:
        raise RuntimeError("bad amount")

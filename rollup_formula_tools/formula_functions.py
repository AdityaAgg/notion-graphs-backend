import math
from re import search, sub
from datetime import datetime, timezone
from notion.collection import NotionDate
from notion.user import User


def pre_check_for_nulls(function_to_call, args):
    for index, arg in enumerate(args):
        if arg is None:
            return None
        if type(arg) == NotionDate:
            args[index] = convert_notion_date_to_datetime(arg)
    return function_to_call(*args)


def convert_notion_date_to_datetime(notion_date):
    if not notion_date.start:
        return None
    datetime_timezone = notion_date.timezone
    converted_date = datetime.combine(notion_date.start, datetime.min.time())
    if datetime_timezone:  # there is a bug in timezone in notion-py parsing thus this has no effect
        converted_date.replace(tzinfo=datetime_timezone).astimezone(tz=timezone.utc)
    return converted_date


def pre_check_for_zero(arg1, arg2, function_to_call):
    if arg2 == 0:
        return False
    return function_to_call(arg1, arg2)


def pre_check_for_nulls_only_arg0(function_to_call, args):
    if args[0] is None:
        return None
    return function_to_call(*args)


def pre_check_convert_null_to_empty_string(function_to_call, args):
    for i in range(len(args)):
        if type(args) == list and len(args[i]) > 0 and type(args[i][0]) == User:
            args[i] = [notion_user.full_name for notion_user in args[i]]
        if args[i] is None:
            args[i] = ""
        elif type(args[i]) != str:
            new_arg = str(args[i])
            if type(args[i]) == list:
                new_arg = new_arg[1:(len(new_arg)-1)]
            args[i] = new_arg
    return function_to_call(*args)


def check_for_complex(result):
    if isinstance(result, complex):
        return None
    else:
        return result


def to_number(arg1):
    if type(arg1) == datetime:
        return arg1.timestamp() * 1000
    else:
        return float(arg1)


def sign(arg1):
    if arg1 > 0:
        return 1
    if arg1 == 0:
        return 0
    if arg1 < 0:
        return -1
    return None


def custom_precheck_for_slice(function_to_call, args):
    for index, arg in enumerate(args):
        if index == 0 and arg is None:
            return ""
        elif arg is None:
            return None
        elif index == 0 and type(arg) != str:
            args[index] = str(arg)
        elif type(arg) == float:
            args[index] = int(arg)
    return function_to_call(*args)


identifier_to_function_map = {
    # handle nulls appropriately
    "add": lambda args: pre_check_for_nulls(lambda arg1, arg2: arg1 + arg2, args),
    "multiply": lambda args: pre_check_for_nulls(lambda arg1, arg2: arg1 * arg2, args),
    "subtract": lambda args: pre_check_for_nulls(lambda arg1, arg2: arg1 - arg2, args),
    "divide": lambda args: pre_check_for_nulls(
        lambda arg1, arg2: pre_check_for_zero(arg1, arg2, lambda arga, argb: arga / argb),
        args),
    "mod": lambda args: pre_check_for_nulls(
        lambda arg1, arg2: pre_check_for_zero(arg1, arg2, lambda arga, argb: arga % argb),
        args),
    "pow": lambda args: pre_check_for_nulls(lambda arg1, arg2: check_for_complex(arg1 ** arg2), args),
    "unaryMinus": lambda args: pre_check_for_nulls(lambda arg1: -1 * arg1, args),
    "unaryPlus": lambda args: pre_check_for_nulls(lambda arg1: arg1, args),
    "not": lambda args: not args[0],
    "and": lambda args: args[0] and args[1],
    "or": lambda args: args[0] or args[1],
    "equal": lambda args: args[0] == args[1],
    "unequal": lambda args: args[0] != args[1],
    "larger": lambda args: pre_check_for_nulls(lambda arg1, arg2: arg1 > arg2, args),
    "largerEq": lambda args: pre_check_for_nulls(lambda arg1, arg2: arg1 >= arg2, args),
    "smaller": lambda args: pre_check_for_nulls(lambda arg1, arg2: arg1 < arg2, args),
    "smallerEq": lambda args: pre_check_for_nulls(lambda arg1, arg2: arg1 <= arg2, args),
    "if": lambda args:
    pre_check_for_nulls_only_arg0(
        lambda condition, true_arg, false_arg: true_arg if condition else false_arg,
        args),
    "concat": lambda args: pre_check_convert_null_to_empty_string(lambda arg1, arg2: arg1 + arg2, args),
    "length": lambda args: pre_check_convert_null_to_empty_string(lambda arg1: len(arg1), args),
    "abs": lambda args: pre_check_for_nulls(lambda arg1: abs(arg1), args),
    "cbrt": lambda args: pre_check_for_nulls(lambda arg1: check_for_complex(arg1 ** (1 / 3)), args),
    "sqrt": lambda args: pre_check_for_nulls(lambda arg1: check_for_complex(arg1 ** (1 / 2)), args),
    "ceil": lambda args: pre_check_for_nulls(lambda arg1: math.ceil(arg1), args),
    "floor": lambda args: pre_check_for_nulls(lambda arg1: math.floor(arg1), args),
    "round": lambda args: pre_check_for_nulls(lambda arg1: round(arg1), args),
    "exp": lambda args: pre_check_for_nulls(lambda arg1: check_for_complex(math.e ** arg1), args),
    "ln": lambda args: pre_check_for_nulls(lambda arg1: check_for_complex(math.log(arg1)), args),
    "log2": lambda args: pre_check_for_nulls(lambda arg1: check_for_complex(math.log(arg1, 2)), args),
    "log10": lambda args: pre_check_for_nulls(lambda arg1: check_for_complex(math.log(arg1, 10)), args),
    "max": lambda args: pre_check_for_nulls(lambda *args_inner: max(args_inner), args),
    "min": lambda args: pre_check_for_nulls(lambda *args_inner: min(args_inner), args),
    "sign": lambda args: pre_check_for_nulls(lambda arg1: sign(arg1), args),
    "replace": lambda args: pre_check_convert_null_to_empty_string(
        lambda arg1, arg2, arg3: sub(arg2, arg3, arg1, 1), args),
    "replaceAll": lambda args: pre_check_convert_null_to_empty_string(
        lambda arg1, arg2, arg3: sub(arg2, arg3, arg1), args),
    "contains": lambda args: pre_check_convert_null_to_empty_string(
        lambda arg1, arg2: arg2 in arg1, args),
    "empty": lambda args: args[0] is None or args[0] == "",
    "format": lambda args: pre_check_convert_null_to_empty_string(lambda arg1: str(arg1), args),
    "slice": lambda args: custom_precheck_for_slice(lambda arg1, arg2, arg3=None: arg1[arg2:arg3], args),
    "join": lambda args: pre_check_convert_null_to_empty_string(lambda joiner, *strings: joiner.join(strings), args),
    "test": lambda args: pre_check_convert_null_to_empty_string(
        lambda test_string, pattern: search(pattern, str(test_string)) is not None, args),
    "toNumber": lambda args: pre_check_for_nulls(to_number, args),
    "e": lambda args: math.e,
    "pi": lambda args: math.pi,
    "true": lambda args: True,
    "false": lambda args: False,
    "now": lambda args: datetime.now()
    # TODO: date functions
}

identifier_to_function_params_map = {
    "symbol": [],
    "conditional": ["condition", "true", "false"],
    "function": []
}


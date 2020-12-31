from statistics import median


def pre_filter_remove_nulls_aggregation(function_to_call, arr, is_numeric_aggregation=False):
    filtered_list = list(filter(lambda element: element is not None, arr))
    if len(filtered_list) == 0 and is_numeric_aggregation:
        return None
    return function_to_call(filtered_list)


def pre_filter_only_nulls_aggregation(function_to_call, arr):
    return function_to_call(list(filter(lambda element: element is None, arr)))


def invalid_if_prefiltered_empty(function_to_call, arr):
    if len(arr) == 0:
        return None
    return function_to_call(arr)


def flatten(arr):
    if len(arr) == 0 or type(arr[0]) != list:
        return arr
    return [element for inner_arr in arr for element in inner_arr]


identifier_to_rollup_map = {
    "sum": lambda pre_arr: pre_filter_remove_nulls_aggregation(lambda arr: sum(arr), pre_arr, True),
    "average": lambda pre_arr: pre_filter_remove_nulls_aggregation(lambda arr: sum(arr)/len(arr), pre_arr, True),
    "median": lambda pre_arr: pre_filter_remove_nulls_aggregation(lambda arr: median(arr), pre_arr, True),
    "min": lambda pre_arr: pre_filter_remove_nulls_aggregation(lambda arr: min(arr), pre_arr, True),
    "max": lambda pre_arr: pre_filter_remove_nulls_aggregation(lambda arr: max(arr), pre_arr, True),
    "range": lambda pre_arr: pre_filter_remove_nulls_aggregation(lambda arr: max(arr) - min(arr), pre_arr, True),
    "count": lambda arr: len(arr),
    "empty": lambda pre_arr: pre_filter_only_nulls_aggregation(lambda arr: len(arr), pre_arr),
    "percent_empty": lambda pre_arr_optional: invalid_if_prefiltered_empty(
        lambda pre_arr: pre_filter_only_nulls_aggregation(lambda arr: len(arr), pre_arr)/len(pre_arr),
        pre_arr_optional),
    "not_empty": lambda pre_arr: pre_filter_remove_nulls_aggregation(lambda arr: len(arr), pre_arr),
    "percent_not_empty": lambda pre_arr_optional: invalid_if_prefiltered_empty(
        lambda pre_arr: pre_filter_remove_nulls_aggregation(lambda arr: len(arr), pre_arr)/len(pre_arr),
        pre_arr_optional),
    "count_values": lambda pre_arr: pre_filter_remove_nulls_aggregation(lambda arr: len(flatten(arr)), pre_arr),
    "unique": lambda pre_arr: pre_filter_remove_nulls_aggregation(
        lambda arr: len(set(flatten(arr))), pre_arr),
    "show_unique": lambda pre_arr: pre_filter_remove_nulls_aggregation(
        lambda arr: list(set(flatten(arr))), pre_arr),
    None: lambda pre_arr: pre_filter_remove_nulls_aggregation(flatten, pre_arr)
}



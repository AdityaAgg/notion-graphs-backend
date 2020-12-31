from .rollup_functions import identifier_to_rollup_map
from exceptions import InvalidUsage
from .formula_functions import identifier_to_function_map, identifier_to_function_params_map


def is_rollup_or_formula(property_to_check):
    return type(property_to_check) == dict and \
           (property_to_check.get("type") == "rollup" or property_to_check.get("type") == "formula")


def calculate_rollup_or_formula(equation, item):
    if equation.get("type") == "rollup":
        return calculate_rollup(equation, item)
    else:
        return calculate_formula(equation, item)


def calculate_rollup(rollup, item):
    rollup_function = identifier_to_rollup_map[rollup.get('aggregation')]
    if not rollup_function:
        raise InvalidUsage("this type of rollup is not supported")  # we'll want to throw an exception in this case
    relation_data = item.get_property(rollup.get('relation_property'))
    target_property = rollup.get('target_property')
    relation_data_processed = []

    if relation_data and len(relation_data) > 0:
        if not is_rollup_or_formula(relation_data[0].collection.get_schema_property(target_property)):
            relation_data_processed = [
                relation_item.get_property(target_property) for relation_item in relation_data]
        else:
            relation_calculated_field = relation_data[0].collection.get_schema_property(target_property)
            relation_data_processed = [calculate_rollup_or_formula(
                relation_calculated_field, relation_item)
                for relation_item in relation_data]
    return rollup_function(relation_data_processed)


def fetch_data_for_arg(arg, item):
    if arg.get("id"):
        return fetch_data_for_arg_helper(arg.get("id"), item)
    elif type(arg) == dict and arg.get("type"):
        return calculate_rollup_or_formula({"formula": arg}, item)


def fetch_data_for_arg_helper(arg_id, item):
    if is_rollup_or_formula(item.collection.get_schema_property(arg_id)):
        return calculate_rollup_or_formula(item.collection.get_schema_property(arg_id), item)
    else:
        return item.get_property(arg_id)


def calculate_formula(formula, item):
    formula = formula.get("formula")

    if formula is None:
        raise InvalidUsage("you are using a notion type that is not yet supported")

    function_type = formula.get("type")
    function_name = formula.get("name")
    if function_name is None:
        if function_type == "constant":
            value = formula.get("value")
            if formula.get("value_type") == "number":
                value = float(value)
            return value
        else:
            print("failed formula: ", formula)
            raise InvalidUsage("you are using a formula which is not yet supported")
    function_to_call = identifier_to_function_map.get(function_name)
    if function_to_call is None:
        print("failed formula: ", formula)
        raise InvalidUsage("you are using a formula which is not yet supported")

    # process args
    if formula.get("args"):
        # if function_name == "<function name here>":
            # print([fetch_data_for_arg(arg, item) for arg in formula.get("args")])
            # print(function_to_call([fetch_data_for_arg(arg, item) for arg in formula.get("args")]))
        return function_to_call([fetch_data_for_arg(arg, item) for arg in formula.get("args")])

    params = identifier_to_function_params_map.get(function_type)
    return function_to_call([fetch_data_for_arg(formula.get(param), item) for param in params])


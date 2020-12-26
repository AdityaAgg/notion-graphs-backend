from .rollup_functions import identifier_to_rollup_map
from exceptions import InvalidUsage


def is_rollup_or_formula(property_to_check):
    return type(property_to_check) == dict and \
           (property_to_check.get("type") == "rollup" or property_to_check.get("type") == "formula")


def calculate_formula(formula, item):
    raise InvalidUsage("you are either using a formula or rollup based on a formula which is not yet supported")


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


from notion.client import NotionClient
import json
from flask import Flask, jsonify, make_response
from flask import request
from exceptions import *
from flask_cors import CORS
import datetime
from notion.collection import NotionDate
from notion_graphs_types import XAxisType
import rollup_formula_tools.utils as rollup_formula_utils
import resource
import contextlib

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["https://notion-graphs.com", "http://localhost:3000", "http://localhost:5000"],
     allow_headers=["Accept", "Cache", "Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key",
                    "X-Amz-Security-Token"])


# helpers


def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError


@contextlib.contextmanager
def limit(limit_qty, resource_type=resource.RLIMIT_AS):
    soft_limit, hard_limit = resource.getrlimit(resource_type)
    resource.setrlimit(resource_type, (limit_qty, hard_limit)) # set soft limit
    try:
        yield
    except MemoryError:
        raise InvalidUsage("you a graph on a collection that is too large for us to process")
    finally:
        resource.setrlimit(resource_type, (soft_limit, hard_limit)) # restore


def schema_validation(notion_data_points, x_property, y_property, size_property, title_property, series_property):
    set_size = set_title = set_series = False
    is_x_time = XAxisType.NOT_TIME
    rollup_or_formula_x = rollup_or_formula_y = rollup_or_formula_size = None
    if len(notion_data_points) > 0:
        set_size = set_title = set_series = True
        notion_data_point = notion_data_points[0]
        properties = set([prop["name"] for prop in notion_data_point.schema])
        try:
            if isinstance(notion_data_point.get_property(x_property), datetime.date):
                is_x_time = XAxisType.TIMESTAMP
            elif isinstance(notion_data_point.get_property(x_property), NotionDate):
                start_time = notion_data_point.get_property(x_property).start
                if isinstance(start_time, datetime.datetime):
                    is_x_time = XAxisType.DATETIME_DATE
                elif isinstance(start_time, datetime.date):
                    is_x_time = XAxisType.DATE
                elif not start_time:
                    raise InvalidUsage("x property is a Date type that Notion Graphs does not support")

            if x_property not in properties:
                rollup_or_formula_x = notion_data_point.collection.get_schema_property(x_property)
                if type(rollup_formula_utils.calculate_rollup_or_formula(rollup_or_formula_x, notion_data_point))\
                        == list:
                    raise InvalidUsage("x property must be numeric")

        except (AttributeError, TypeError):
            raise InvalidUsage("x property does not exist in notion table")

        try:
            notion_data_point.get_property(y_property)
            is_y_time = (isinstance(
                notion_data_point.get_property(y_property), datetime.date) or
                isinstance(notion_data_point.get_property(y_property), NotionDate))
            if is_y_time:
                raise InvalidUsage(
                    "y property uses time which is not supported. Time is supported only for x axis.")
            if y_property not in properties:
                rollup_or_formula_y = notion_data_point.collection.get_schema_property(y_property)
                if type(rollup_formula_utils.calculate_rollup_or_formula(rollup_or_formula_y, notion_data_point)) \
                        == list:
                    raise InvalidUsage("y property must be numeric")

        except (AttributeError, TypeError):
            raise InvalidUsage("y property does not exist in notion table")

        if size_property not in properties:
            try:
                notion_data_point.get_property(size_property)
                rollup_or_formula_size = notion_data_point.collection.get_schema_property(size_property)
                set_size = type(rollup_formula_utils.calculate_rollup_or_formula(
                    rollup_or_formula_size, notion_data_point)) == list
            except(AttributeError, TypeError):
                set_size = False

        if title_property not in properties:
            set_title = False

        if series_property not in properties:
            set_series = False

    return {"set_size": set_size,
            "set_title": set_title,
            "set_series": set_series,
            "is_x_time": is_x_time,
            "rollup_or_formula_x": rollup_or_formula_x,
            "rollup_or_formula_y": rollup_or_formula_y,
            "rollup_or_formula_size": rollup_or_formula_size
            }


def get_data_points(cv, x_property, y_property, size_property, title_property, series_property):
    notion_data_points = cv.collection.get_rows()

    # schema validation
    schema_information = schema_validation(notion_data_points, x_property, y_property, size_property, title_property, series_property)

    data_points = []
    invalid_data_points = []
    all_series = {}

    # empty defaults
    size = 1
    series = []

    set_size = schema_information.get("set_size")
    set_title = schema_information.get("set_title")
    set_series = schema_information.get("set_series")
    is_x_time = schema_information.get("is_x_time")
    rollup_or_formula_x = schema_information.get("rollup_or_formula_x")
    rollup_or_formula_y = schema_information.get("rollup_or_formula_y")
    rollup_or_formula_size = schema_information.get("rollup_or_formula_size")

    for notion_data_point in notion_data_points:
        if set_size:
            if rollup_or_formula_size:
                size = rollup_formula_utils.calculate_rollup_or_formula(rollup_or_formula_size, notion_data_point)
            else:
                size = notion_data_point.get_property(size_property)

        title = notion_data_point.get_property(
            title_property) if set_title else notion_data_point.title
        if set_series:
            series = []
            notion_series = notion_data_point.get_property(series_property)
            for notion_domain in notion_series:
                series.append(notion_domain.title)

        x_value = rollup_formula_utils.calculate_rollup_or_formula(rollup_or_formula_x, notion_data_point) \
            if rollup_or_formula_x else notion_data_point.get_property(x_property)

        # time handling
        if is_x_time == XAxisType.TIMESTAMP:
            if x_value:
                x_value = x_value.timestamp() * 1000
        elif is_x_time == XAxisType.DATETIME_DATE:
            if x_value and x_value.start:
                if x_value.timezone:  # there is a bug in timezone in notion-py parsing thus this has no effect
                    x_value.start.replace(tzinfo=x_value.timezone).astimezone(tz=datetime.timezone.utc)
                x_value = x_value.start.timestamp() * 1000
            else:
                x_value = None
        elif is_x_time == XAxisType.DATE:
            if x_value and x_value.start:
                timezone = x_value.timezone
                x_value = datetime.datetime.combine(x_value.start,
                                                    datetime.datetime.min.time())
                if timezone:  # there is a bug in timezone in notion-py parsing thus this has no effect
                    x_value.replace(tzinfo=timezone).astimezone(tz=datetime.timezone.utc)
                x_value = x_value.timestamp() * 1000
            else:
                x_value = None

        y_value = rollup_formula_utils.calculate_rollup_or_formula(rollup_or_formula_y, notion_data_point) \
            if rollup_or_formula_y else notion_data_point.get_property(y_property)

        data_point = {
            "x": x_value,
            "y": y_value,
            "size": size,
            "title": title,
            "series": series
        }
        if not x_value or not y_value or (
                set_size and not size):
            invalid_data_points.append(data_point)
        else:
            data_points.append(data_point)

    data_points.sort(key=lambda data_pt: data_pt["x"])

    for index, data_point in enumerate(data_points):
        data_point["index"] = index
        if set_series:
            for series_title in data_point["series"]:
                if series_title in all_series:
                    all_series[series_title].append(index)
                else:
                    all_series[series_title] = [index]

    return {"data_points": data_points, "series": all_series, "is_x_time": not (is_x_time == XAxisType.NOT_TIME),
            "invalid_data_points": invalid_data_points}


# routes
@app.route('/line_graph')
def get_all_events_route():
    app.logger.info("line graph notion graphs request")
    notion_client = None
    notion_cookie = request.cookies.get("token_v2")
    if notion_cookie is not None:
        try:
            notion_client = NotionClient(token_v2=notion_cookie)
        except:
            raise InvalidUsage("are you sure your notion token is correct?")
    else:
        raise InvalidUsage("will not work without notion cookie")

    # required properties
    notion_url = request.args.get('url')
    if notion_url is None:
        raise InvalidUsage("API requires you specify notion url")

    x_property = request.args.get('x')
    if x_property is None:
        raise InvalidUsage("API requires you specify x axis property")

    y_property = request.args.get('y')
    if y_property is None:
        raise InvalidUsage("API requires you specify y axis property")

    # optional properties
    size_property = request.args.get('size')
    series_property = request.args.get('series')
    title_property = request.args.get('title')
    title_property = title_property if title_property is not None else 'title'

    # generate data
    try:
        cv = notion_client.get_collection_view(notion_url)
    except:
        raise InvalidUsage(
            "Notion Graphs seems to have trouble finding your notion page. Are you sure it is the right one?")
    with limit(5 * 10**7):  # setting a memory limit on fetching notion data to prevent brown out
        return json.dumps(get_data_points(cv, x_property, y_property, size_property,
                                          title_property, series_property),
                          default=set_default)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route('/logout')
def logout():
    res = make_response(jsonify({"message": "Cookie Removed"}))
    is_local = request.host == 'localhost'
    if not is_local:
        res.set_cookie('cookies_set', '', max_age=0,
                       domain='notion-graphs.com')
        res.set_cookie('cookies_set', '', max_age=0,
                       domain='.notion-graphs.com')
        res.set_cookie('token_v2', '', max_age=0, domain='.notion-graphs.com')
    else:
        res.set_cookie('cookies_set', '', max_age=0)
        res.set_cookie('token_v2', '', max_age=0)
    return res


@app.route('/set_http_only')
def set_http_only():
    res = make_response(jsonify({"message": "Cookie Secured"}))
    if request.host != 'localhost':  # http only doesn't make sense for localhost
        # as it is not supported for the domain on most browsers
        notion_cookie = request.cookies.get('token_v2')
        res.set_cookie('token_v2', value=notion_cookie, expires=datetime.datetime(2052, 7, 17),
                       domain='.notion-graphs.com',
                       secure=True, httponly=True)
    return res


@app.route('/')
def healthy_route():
    return "hello! try /line_graph to start using :)"


# start app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

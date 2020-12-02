from notion.client import NotionClient
import json
from flask import Flask, jsonify, make_response
from flask import request
from exceptions import *
from flask_cors import CORS
import datetime

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["https://notion-graphs.com", "http://localhost:3000"],
     allow_headers=["Accept", "Cache", "Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key",
                    "X-Amz-Security-Token"])


# helpers

def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError


def schema_validation(notion_data_point, x_property, y_property, size_property, title_property, series_property):
    set_size = set_title = set_series = True
    is_x_time = False
    properties = set([prop["name"] for prop in notion_data_point.schema])
    try:
        if isinstance(notion_data_point.get_property(x_property), datetime.date):
            is_x_time = True
        if x_property not in properties:
            raise InvalidUsage("x property uses rollup or formula which not supported")
    except (AttributeError, TypeError):
        raise InvalidUsage("x property does not exist in notion table")

    try:
        notion_data_point.get_property(y_property)
        is_y_time = isinstance(notion_data_point.get_property(y_property), datetime.date)
        if is_y_time:
            raise InvalidUsage("y property uses time which is not supported. Time is supported only for x axis.")
        if y_property not in properties:
            raise InvalidUsage("y property uses rollup or formula which not supported")
    except (AttributeError, TypeError):
        raise InvalidUsage("y property does not exist in notion table")

    if size_property not in properties:
        set_size = False

    if title_property not in properties:
        set_title = False

    if series_property not in properties:
        set_series = False

    return set_size, set_title, set_series, is_x_time


def get_data_points(cv, x_property, y_property, size_property, title_property, series_property):
    notion_data_points = cv.collection.get_rows()

    # schema validation
    set_size = set_title = set_series = is_x_time = False
    if len(notion_data_points) > 0:
        set_size, set_title, set_series, is_x_time = schema_validation(
            notion_data_points[0], x_property, y_property, size_property, title_property, series_property)

    data_points = []
    invalid_data_points = []
    all_series = {}

    # empty defaults
    size = 1
    series = []
    for notion_data_point in notion_data_points:
        size = notion_data_point.get_property(
            size_property) if set_size else size
        title = notion_data_point.get_property(
            title_property) if set_title else notion_data_point.title
        if set_series:
            series = []
            notion_series = notion_data_point.get_property(series_property)
            for notion_domain in notion_series:
                series.append(notion_domain.title)

        x_value = notion_data_point.get_property(x_property)
        if is_x_time:
            x_value = x_value.timestamp() * 1000
        data_point = {
            "x": x_value,
            "y": notion_data_point.get_property(y_property),
            "size": size,
            "title": title,
            "series": series
        }
        if not x_value or not notion_data_point.get_property(y_property) or (
            set_size and not notion_data_point.get_property(size_property)):
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

    return {"data_points": data_points, "series": all_series, "is_x_time": is_x_time,
            "invalid_data_points": invalid_data_points}


# routes

@app.route('/line_graph')
def get_all_events_route():
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
    is_local = request.host != 'localhost'
    if is_local:
        res.set_cookie('cookies_set', '', max_age=0, domain='notion-graphs.com')
        res.set_cookie('token_v2', '', max_age=0, domain='.notion-graphs.com')
    else:
        res.set_cookie('cookies_set', '', max_age=0)
        res.set_cookie('token_v2', '', max_age=0)
    return res


@app.route('/set_http_only')
def set_http_only():
    res = make_response(jsonify({"message": "Cookie Secured"}))
    if request.host != 'localhost':
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

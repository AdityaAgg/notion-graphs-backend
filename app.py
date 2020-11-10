from notion.client import NotionClient
import json
from flask import Flask, jsonify
from flask import request
from exceptions import *
from flask_cors import CORS
import datetime

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["https://adityaagg.github.io","http://localhost:3000"],
     allow_headers=["Accept","Cache","Content-Type","X-Amz-Date","Authorization","X-Api-Key","X-Amz-Security-Token"])


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
            raise InvalidUsage("x property uses rollup and formula which not supported")
    except (AttributeError, TypeError):
        raise InvalidUsage("x property does not exist in notion table")

    try:
        notion_data_point.get_property(y_property)
        if y_property not in properties:
            raise InvalidUsage("y property uses rollup and formula which not supported")
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
    all_series = {}

    # empty defaults
    size = 1
    series = []

    for index, notion_data_point in enumerate(notion_data_points):
        size = notion_data_point.get_property(
            size_property) if set_size else size
        title = notion_data_point.get_property(
            title_property) if set_title else notion_data_point.title
        if set_series:
            series = []
            notion_series = notion_data_point.get_property(series_property)
            for notion_domain in notion_series:
                series.append(notion_domain.title)
                if(notion_data_point.get_property(x_property) and notion_data_point.get_property(y_property)
                   and (not set_size or notion_data_point.get_property(size_property))):
                    if notion_domain.title in all_series:
                        all_series[notion_domain.title].append(index)
                    else:
                        all_series[notion_domain.title] = [index]

        x_value = notion_data_point.get_property(x_property)
        if is_x_time:
            x_value = x_value.timestamp()
        data_point = {
            "id": index,
            "x": x_value,
            "y": notion_data_point.get_property(y_property),
            "size": size,
            "title": title,
            "series": series
        }

        data_points.append(data_point)

    return {"data_points": data_points, "series": all_series, "is_x_time": is_x_time}


# routes

@app.route('/line_graph')
def get_all_events_route():
    notion_client = None
    notion_cookie = request.cookies.get("token_v2")
    if notion_cookie is not None:
        notion_client = NotionClient(token_v2=notion_cookie)
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
    cv = notion_client.get_collection_view(notion_url)
    return json.dumps(get_data_points(cv, x_property, y_property, size_property,
                                      title_property, series_property),
                      default=set_default)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route('/')
def healthy_route():
    return "hello! try /line_graph to start using :)"


# start app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

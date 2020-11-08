from notion.client import NotionClient
import json
from flask import Flask, jsonify
from flask import request
from exceptions import *
from flask_cors import CORS
app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["https://adityaagg.github.io","localhost"],
     allow_headers="Accept,Cache,Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token")


# helpers

def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError


def schema_validation(notion_data_point, x_property, y_property, size_property, title_property, series_property):
    set_size = set_title = set_series = True
    try:
        notion_data_point.get_property(x_property)
    except (AttributeError, TypeError):
        raise InvalidUsage("x property does not exist in notion table")

    try:
        notion_data_point.get_property(y_property)
    except (AttributeError, TypeError):
        raise InvalidUsage("y property does not exist in notion table")

    try:
        notion_data_point.get_property(size_property)
    except (AttributeError, TypeError):
        set_size = False

    try:
        notion_data_point.get_property(title_property)
    except (AttributeError, TypeError):
        set_title = False

    try:
        notion_data_point.get_property(series_property)
    except (AttributeError, TypeError):
        set_series = False

    return set_size, set_title, set_series


def get_data_points(cv, x_property, y_property, size_property, title_property, series_property):
    notion_data_points = cv.collection.get_rows()

    # schema validation
    set_size = set_title = set_series = False
    if len(notion_data_points) > 0:
        set_size, set_title, set_series = schema_validation(
            notion_data_points[0], x_property, y_property, size_property, title_property, series_property)

    data_points = []
    all_series = set()

    # empty defaults
    size = 1
    title = ''
    series = []

    for index, notion_data_point in enumerate(notion_data_points):
        size = notion_data_point.get_property(
            size_property) if set_size else size
        title = notion_data_point.get_property(
            title_property) if set_title else title

        if set_series:
            notion_series = notion_data_point.get_property(series_property)
            new_series = set(
                [notion_domain.title for notion_domain in notion_series])
            all_series = all_series.union(new_series)
            series = list(new_series)

        data_point = {
            "id": index,
            "x": notion_data_point.get_property(x_property),
            "y": notion_data_point.get_property(y_property),
            "size": size,
            "title": title,
            "series": series
        }

        data_points.append(data_point)

    return {"data_points": data_points, "series": all_series}


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

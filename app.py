from notion.client import NotionClient
import json
from create_graph import *
from flask import Flask
from flask import request
from flask_cors import CORS
notion_client = None
app = Flask(__name__)


#helpers
def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError


def get_all_events(cv, timestamp):
    notion_events = filter(lambda x: x.Status == 'Done 🙌', cv.collection.get_rows())
    events = []
    event_hiearchy = {}
    visited_set = set()
    all_domains = set()
    for index, notion_event in enumerate(notion_events):
        event = {}
        event["id"] = index
        event["title"] = notion_event.title
        event["size"] = notion_event.get_property("Points")
        if event["size"] == None:
            event["size"] = 0.5
        notion_value = notion_event.get_property("quality_of_execution_5_highest")
        event["value"] = 3 if (notion_value == None) else ord(notion_value) - ord('0')

        notion_domains = notion_event.get_property("Goals")
        new_domains = set([notion_domain.title for notion_domain in notion_domains])
        all_domains = all_domains.union(new_domains)
        event["domains"] = list(new_domains)
        events.append(event)
        populate_event_hiearchy_task(notion_event, event_hiearchy, visited_set, set(), index)
    return {"events": events, "hiearchy": event_hiearchy, "domains": all_domains}


#routes
@app.route('/get_all_events')
@cross_origin()
def get_all_events_route():
    global notion_client
    if notion_client == None:
        notion_cookie = request.cookies.get("token_v2")
        notion_client = NotionClient(token_v2=notion_cookie)
    notion_url = "https://www.notion.so/5813e381992d4ae9bdbca0b84593d18f?v=8cea9a8178b94159bdbe9a1512432047"
    cv = notion_client.get_collection_view(notion_url)
    return json.dumps(get_all_events(cv, None), default=set_default)

@app.route('/')
def healthy_route():
    return ""

#start app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

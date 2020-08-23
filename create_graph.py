class InvalidNotionDatabaseStateException(Exception):
    pass

# to switch to events and event groups being the same object -- just switch to this function
# from the one with the same name suffixed with task
# another issue to consider with this choice -- should event groups have the same metadata as events
def populate_event_hiearchy(notion_event, event_hiearchy, visited_set, predecessors):
    event = notion_event.title
    # invalid case
    if event in predecessors:
        raise InvalidNotionDatabaseStateException("there is a cycle in the notion database")

    # base case
    if event_hiearchy.get(event) == None:
        event_hiearchy[event] = set()
    elif event in visited_set:
        return

    # recurrence
    predecessors.add(event)
    for parent in notion_event.get_property("Parent"):
        event_hiearchy[notion_event.title].add(parent.title)
        populate_event_hiearchy(parent, event_hiearchy, visited_set, predecessors)
    predecessors.remove(event)
    visited_set.add(event)

def populate_event_hiearchy_task(notion_event, event_hiearchy, visited_set, predecessors, index):
    index_as_string = str(index)
    stories = notion_event.get_property("Stories")
    event_hiearchy[index_as_string] = set()
    for story in stories:
        event_hiearchy[index_as_string].add(story.title)
        populate_event_hiearchy(story, event_hiearchy, visited_set, predecessors)


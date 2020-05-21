import os

from flask import Blueprint, request, jsonify
from flask_security import login_required, current_user
from slugify import slugify
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint("api", __name__)

SETTINGS_FILE_PATH = os.path.join(os.path.dirname(__file__), "../settings.ini")


@bp.route("/api/get-slug")
@login_required
def get_slug():
    value = request.args.get("value", "")

    return jsonify({"value": value, "slug": slugify(str(value))})


@bp.route("/api/topic-exists/<map_identifier>")
@login_required
def topic_exists(map_identifier):
    result = False
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)

    topic_identifier = slugify(str(request.args.get("q").lower()))
    generated_topic_name = " ".join([
        word.capitalize()
        for word in topic_identifier.split("-")
    ])
    result = topic_store.topic_exists(map_identifier, topic_identifier)
    return jsonify({"status": result,
                    "topicIdentifier": topic_identifier,
                    "generatedTopicName": generated_topic_name})


@bp.route("/api/create-topic/<map_identifier>", methods=['POST'])
@login_required
def create_topic(map_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)

    # TODO: Implement missing logic.


@bp.route("/api/get-identifiers/<map_identifier>")
@login_required
def get_identifiers(map_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # TODO: Missing logic?

    query_term = request.args.get("q").lower()

    return jsonify(topic_store.get_topic_identifiers(
        map_identifier, query_term, limit=10))


@bp.route("/api/get-network/<map_identifier>/<topic_identifier>")
def get_network(map_identifier, topic_identifier):
    topic_store = get_topic_store()

    if current_user.is_authenticated:  # User is logged in
        is_map_owner = topic_store.is_topic_map_owner(
            map_identifier, current_user.id)
        if is_map_owner:
            topic_map = topic_store.get_topic_map(
                map_identifier, current_user.id)
        else:
            topic_map = topic_store.get_topic_map(map_identifier)
        if topic_map is None:
            abort(404)
    else:  # User is not logged in
        topic_map = topic_store.get_topic_map(map_identifier)
        if topic_map is None:
            abort(404)
        if not topic_map.published:  # User is not logged in and the map is not published
            abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier)

    scope_identifier = request.args.get("context", type=str)
    scope_filtered = request.args.get("filter", type=int)
    if not scope_filtered:
        scope_identifier = None

    def build_network(inner_identifier):
        base_name = tree[inner_identifier].payload.first_base_name.name
        instance_of = tree[inner_identifier].payload.instance_of
        children = tree[inner_identifier].children

        # group = instance_of
        group = "topic"
        if inner_identifier == topic_identifier:
            group = "active"
        node = {
            "id": inner_identifier,
            "label": base_name + " [" + instance_of + "]",
            "group": group,
            "instanceOf": instance_of,
        }

        result[nodes].append(node)

        for child in children:
            # child_type_topic = topic_store.get_topic(map_identifier, child.type)
            edge = {
                "from": inner_identifier,
                "to": child.pointer,
                "label": child.type,
                "font": {"align": "horizontal"},
                "arrows": "to, from",
                "color": {"color": "#666", "opacity": 0.5},
            }
            result[edges].append(edge)
            build_network(child.pointer)  # Recursive call

    if topic:
        tree = topic_store.get_topics_network(
            map_identifier, topic_identifier, scope=scope_identifier)
        if len(tree) > 1:
            nodes = 0
            edges = 1
            result = (
                [],
                [],
            )  # The result is a tuple containing two lists of dictionaries
            build_network(topic_identifier)
            return jsonify(result)
        else:
            return jsonify({"status": "error", "code": 404,
                            "message": "No network data"})
    else:
        return jsonify({"status": "error", "code": 404,
                        "message": "Topic not found"})

from flask import Blueprint, current_app, jsonify, request

from backend.services.openalex import ResearchError


research_bp = Blueprint("research", __name__, url_prefix="/api/research")


@research_bp.get("/search")
def search_papers():
    query = request.args.get("q", "")
    try:
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        return jsonify({"error": "offset must be an integer."}), 400
    if offset < 0:
        return jsonify({"error": "offset must be zero or greater."}), 400

    try:
        result = current_app.extensions["research_client"].search(query, offset=offset)
    except ResearchError as error:
        return jsonify({"error": error.message}), error.status_code
    return jsonify(result)

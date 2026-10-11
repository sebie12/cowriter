from flask import Blueprint, jsonify

from backend.database import AuthMethod

auth_methods_bp = Blueprint(
    "auth_methods",
    __name__,
    url_prefix="/api/auth-methods",
)

def serialize_auth_method(auth_method):
    return {
        "id": auth_method.method_name.lower(),
        "name": auth_method.method_name,
        "description": auth_method.description,
    }

@auth_methods_bp.get("/")
def get_auth_methods():
    auth_methods = AuthMethod.query.all()
    return jsonify([
        serialize_auth_method(auth_method)
        for auth_method in auth_methods
    ])

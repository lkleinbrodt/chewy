from flask import Blueprint, jsonify

# Define the base blueprints
base_bp = Blueprint("base", __name__)
api_bp = Blueprint("api", __name__, url_prefix="/api")

from backend.routes.calendar import calendar_bp
from backend.routes.recurring import recurring_bp

# Import the specific blueprints from the Chewbacca project
from backend.routes.tasks import schedule_bp, settings_bp, task_bp

# Register all blueprints under the /api prefix
api_bp.register_blueprint(task_bp)
api_bp.register_blueprint(schedule_bp)
api_bp.register_blueprint(settings_bp)
api_bp.register_blueprint(calendar_bp)
api_bp.register_blueprint(recurring_bp)


@base_bp.route("/")
def index():
    """Base root, returns basic status."""
    return jsonify(
        {"status": "healthy", "message": "This page intentionally left blank."}
    )


@api_bp.route("/")
def api_index():
    """API root, returns basic status."""
    return jsonify({"status": "healthy", "message": "Welcome to the Chewy API!"})

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.auth_utils import registered_required
from app.services.scenarios import create_scenario, delete_scenario, list_scenarios
from app.services.scenarios import editor as scenario_editor

bp = Blueprint("scenarios", __name__, url_prefix="/scenarios")


def _json_error(message, status=400):
    return jsonify({"ok": False, "error": message}), status


def _scenario_payload(row):
    return {
        "scenario_id": row.scenario_id,
        "title": row.title,
    }


@bp.route("/")
@registered_required
def index():
    scenarios = list_scenarios(session["user_id"])
    return render_template(
        "scenarios.html",
        scenarios=scenarios,
        api={
            "create": url_for("scenarios.api_create"),
            "rename": url_for("scenarios.api_rename", scenario_id=0).replace(
                "/0/", "/{id}/"
            ),
            "delete": url_for("scenarios.api_delete", scenario_id=0).replace(
                "/0/", "/{id}/"
            ),
            "edit": url_for("scenarios.edit", scenario_id=0).replace("/0/", "/{id}/"),
        },
    )


@bp.route("/api/create", methods=["POST"])
@registered_required
def api_create():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()

    result = create_scenario(session["user_id"], title=title)
    if not result:
        return _json_error(result.error or "create_failed", 500)

    row, _doc = result.value
    return jsonify(
        {
            "ok": True,
            "scenario": _scenario_payload(row),
            "edit_url": url_for("scenarios.edit", scenario_id=row.scenario_id),
        }
    )


@bp.route("/<int:scenario_id>/api/delete", methods=["POST"])
@registered_required
def api_delete(scenario_id):
    result = delete_scenario(scenario_id, session["user_id"])
    if not result:
        status = 404 if result.error == "not_found" else 500
        return _json_error(result.error or "delete_failed", status)
    return jsonify({"ok": True})


@bp.route("/<int:scenario_id>/api/title", methods=["POST"])
@registered_required
def api_rename(scenario_id):
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return _json_error("empty_title")

    user_id = session["user_id"]
    opened = scenario_editor.open_scenario(scenario_id, user_id)
    if not opened:
        return _json_error(opened.error or "not_found", 404)

    _row, doc = opened.value
    titled = scenario_editor.set_title(doc, title)
    if not titled:
        return _json_error(titled.error or "title_failed", 400)

    saved = scenario_editor.save_scenario(scenario_id, user_id, titled.value)
    if not saved:
        return _json_error(saved.error or "save_failed", 500)

    row, _doc = saved.value
    return jsonify({"ok": True, "title": row.title})


@bp.route("/<int:scenario_id>/edit")
@registered_required
def edit(scenario_id):
    result = scenario_editor.open_scenario(scenario_id, session["user_id"])
    if not result:
        flash("Сценарий не найден", "error")
        return redirect(url_for("scenarios.index"))

    row, document = result.value
    return render_template(
        "scenario_editor.html",
        scenario=row,
        document=document,
        api={
            "save": url_for("scenarios.api_save", scenario_id=scenario_id),
            "list": url_for("scenarios.index"),
        },
    )


@bp.route("/<int:scenario_id>/api/save", methods=["POST"])
@registered_required
def api_save(scenario_id):
    if (
        request.content_length is not None
        and request.content_length > current_app.config["MAX_SCENARIO_BYTES"]
    ):
        return _json_error("scenario_too_large", 413)
    data = request.get_json(silent=True) or {}
    document = data.get("document")
    if not isinstance(document, dict):
        return _json_error("invalid_document")

    result = scenario_editor.save_scenario(
        scenario_id, session["user_id"], document
    )
    if not result:
        status = 404 if result.error == "not_found" else 400
        return _json_error(result.error or "save_failed", status)

    row, doc = result.value
    return jsonify(
        {
            "ok": True,
            "scenario": _scenario_payload(row),
            "updated_at": (doc.get("meta") or {}).get("updatedAt"),
        }
    )

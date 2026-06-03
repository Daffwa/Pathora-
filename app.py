import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import RequestEntityTooLarge

APP_ROOT = Path(__file__).resolve().parent
load_dotenv(APP_ROOT / ".env")

from config import Config
from controllers import (
    admin_controller,
    ai_controller,
    application_controller,
    auth_controller,
    chat_controller,
    dashboard_controller,
    document_controller,
    help_controller,
    opportunity_controller,
    profile_controller,
    public_controller,
    recruiter_controller,
)
from extensions import db, migrate
from services.ai_service import log_google_client_init_error
from services.csrf_service import register_csrf
from services.database_service import (
    DatabaseAccessError,
    configure_database_paths,
    initialize_application_storage,
    register_database_teardown,
)
from services.security_headers_service import register_security_headers
from services.template_context_service import inject_template_options
from services.trusted_host_service import register_trusted_hosts


def register_routes(app):
    app.register_blueprint(public_controller.bp)
    app.register_blueprint(auth_controller.bp)
    app.register_blueprint(dashboard_controller.bp)
    app.register_blueprint(opportunity_controller.bp)
    app.register_blueprint(application_controller.bp)
    app.register_blueprint(document_controller.bp)
    app.register_blueprint(profile_controller.bp)
    app.register_blueprint(chat_controller.bp)
    app.register_blueprint(recruiter_controller.bp)
    app.register_blueprint(admin_controller.bp)
    app.register_blueprint(ai_controller.bp)
    app.register_blueprint(help_controller.bp)
    register_legacy_endpoint_aliases(app)


def register_legacy_endpoint_aliases(app):
    for rule in list(app.url_map.iter_rules()):
        if "." not in rule.endpoint or rule.endpoint == "static":
            continue

        legacy_endpoint = rule.endpoint.rsplit(".", 1)[1]
        if any(
            existing.endpoint == legacy_endpoint and existing.rule == rule.rule
            for existing in app.url_map.iter_rules()
        ):
            continue

        methods = sorted(rule.methods - {"HEAD", "OPTIONS"})
        app.add_url_rule(
            rule.rule,
            endpoint=legacy_endpoint,
            view_func=app.view_functions[rule.endpoint],
            methods=methods,
            defaults=rule.defaults,
        )


def register_context_processors(app):
    app.context_processor(inject_template_options)


def register_error_handlers(app):
    @app.errorhandler(DatabaseAccessError)
    def database_access_error(error):
        app.logger.exception("Database startup or access failed: %s", error)
        return (
            "Database sedang tidak bisa diakses. Periksa konfigurasi DATABASE_URL, "
            "status server database, dan hasil migration.",
            503,
        )

    @app.errorhandler(SQLAlchemyError)
    def sqlalchemy_error(error):
        app.logger.exception("SQLAlchemy operation failed: %s", error)
        return (
            "Database sedang tidak bisa diakses. Silakan coba lagi setelah koneksi "
            "database diperiksa.",
            503,
        )

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html"), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("403.html"), 403

    @app.errorhandler(RequestEntityTooLarge)
    def file_too_large(error):
        if request.path == "/chat/messages":
            return jsonify({"error": "Ukuran gambar maksimal 5 MB."}), 413
        flash("Ukuran file terlalu besar. Maksimal file adalah 5 MB.")
        if request.path.startswith("/profile"):
            return redirect(url_for("edit_profile"))
        return redirect(url_for("documents"))


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    configure_database_paths(app, APP_ROOT)
    db.init_app(app)
    migrate.init_app(app, db)
    register_database_teardown(app)
    register_trusted_hosts(app)
    register_csrf(app)
    register_security_headers(app)
    register_context_processors(app)
    register_routes(app)
    register_error_handlers(app)
    log_google_client_init_error(app)
    initialize_application_storage(app)
    return app


app = create_app()


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug_mode, use_reloader=False)

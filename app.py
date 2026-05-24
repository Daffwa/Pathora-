import os
from pathlib import Path
import sqlite3

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge

APP_ROOT = Path(__file__).resolve().parent
load_dotenv(APP_ROOT / ".env")

from config import Config
from routes import (
    admin_routes,
    ai_routes,
    application_routes,
    auth_routes,
    chat_routes,
    dashboard_routes,
    document_routes,
    help_routes,
    opportunity_routes,
    profile_routes,
    public_routes,
    recruiter_routes,
)
from services.ai_service import log_google_client_init_error
from services.csrf_service import register_csrf
from services.database_service import (
    DatabaseAccessError,
    build_database_error_message,
    configure_database_paths,
    initialize_application_storage,
    register_database_teardown,
)
from services.security_headers_service import register_security_headers
from services.template_context_service import inject_template_options


def register_routes(app):
    public_routes.register(app)
    auth_routes.register(app)
    profile_routes.register(app)
    ai_routes.register(app)
    dashboard_routes.register(app)
    help_routes.register(app)
    opportunity_routes.register(app)
    chat_routes.register(app)
    application_routes.register(app)
    document_routes.register(app)
    recruiter_routes.register(app)
    admin_routes.register(app)


def register_context_processors(app):
    app.context_processor(inject_template_options)


def register_error_handlers(app):
    @app.errorhandler(DatabaseAccessError)
    def database_access_error(error):
        app.logger.exception("SQLite database access failed: %s", error)
        return (
            "Database sedang tidak bisa diakses. Pastikan file database sudah dibackup, "
            "lalu cek path database dan file journal SQLite sebelum menjalankan "
            "recovery atau integrity check.",
            503,
        )

    @app.errorhandler(sqlite3.Error)
    def sqlite_error(error):
        app.logger.exception("SQLite operation failed: %s", error)
        return (
            "Database sedang tidak bisa diakses. Pastikan file database sudah dibackup, "
            "lalu cek path database dan file journal SQLite sebelum menjalankan "
            "recovery atau integrity check.",
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
    register_database_teardown(app)
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

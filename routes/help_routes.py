from flask import render_template, request, session

from services.auth_service import normalize_role
from services.help_service import (
    get_help_categories,
    get_help_contexts,
    get_popular_articles,
    search_help_articles,
)


def _current_role():
    return normalize_role(session.get("user_role")) if "user_id" in session else None


def register(app):
    @app.route("/help")
    def help():
        query = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()
        context = request.args.get("context", "").strip().lower()
        categories = get_help_categories()
        contexts = get_help_contexts()
        role = _current_role()

        if category not in categories:
            category = ""
        if context not in contexts:
            context = ""

        articles = search_help_articles(
            query=query,
            category=category or None,
            context=context or None,
            role=role,
        )
        context_articles = []
        if context:
            context_articles = [
                article
                for article in search_help_articles(context=context, role=role)
                if context in article["contexts"]
            ][:3]

        return render_template(
            "help.html",
            articles=articles,
            categories=categories,
            contexts=contexts,
            context_articles=context_articles,
            popular_articles=get_popular_articles(role=role),
            selected_category=category,
            selected_context=context,
            selected_context_label=contexts.get(context, ""),
            query=query,
            current_role=role,
        )

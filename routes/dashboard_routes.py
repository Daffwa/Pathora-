from flask import render_template, session

from services.auth_service import jobseeker_required_decorator
from services.opportunity_service import (
    get_dashboard_summary,
    get_recent_applications,
    get_recent_saved_opportunities,
    get_top_priority_opportunity,
    get_urgent_deadlines,
)


def register(app):
    @app.route("/dashboard")
    @jobseeker_required_decorator
    def dashboard():
        user_id = session["user_id"]
        summary = get_dashboard_summary(user_id)
        progress_percent = 0
        if summary["total_documents"]:
            progress_percent = round(
                (summary["completed_documents"] / summary["total_documents"]) * 100
            )

        urgent_deadlines = get_urgent_deadlines(user_id)
        top_priority = get_top_priority_opportunity()
        summary["total_urgent"] = len(urgent_deadlines)

        return render_template(
            "dashboard.html",
            user_name=session["user_name"],
            summary=summary,
            progress_percent=progress_percent,
            recent_saved=get_recent_saved_opportunities(user_id),
            recent_applications=get_recent_applications(user_id),
            urgent_deadlines=urgent_deadlines,
            top_priority=top_priority,
        )

from datetime import date, datetime


def calculate_days_left(deadline):
    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None

    return (deadline_date - date.today()).days


def calculate_deadline_score(days_left):
    if days_left is None or days_left < 0:
        return 0
    if days_left <= 7:
        return 100
    if days_left <= 14:
        return 80
    if days_left <= 30:
        return 60
    return 40


def _split_skills(skills):
    if not skills:
        return set()

    return {
        skill.strip().lower()
        for skill in skills.split(",")
        if skill.strip()
    }


def calculate_skill_match_score(user_skills, required_skills):
    user_skill_set = _split_skills(user_skills)
    required_skill_set = _split_skills(required_skills)

    if not required_skill_set:
        return 50

    matched_count = len(user_skill_set.intersection(required_skill_set))
    return round((matched_count / len(required_skill_set)) * 100)


def calculate_document_score(completed_documents, total_documents):
    if not completed_documents or not total_documents:
        return 0

    return round((completed_documents / total_documents) * 100)


def calculate_priority_score(deadline_score, skill_score, document_score):
    return round(
        (deadline_score * 0.40)
        + (skill_score * 0.35)
        + (document_score * 0.25)
    )


def get_priority_label(priority_score, is_closed):
    if is_closed:
        return "Closed"
    if priority_score >= 80:
        return "High Priority"
    if priority_score >= 60:
        return "Medium Priority"
    return "Low Priority"

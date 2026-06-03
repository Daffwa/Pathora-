from dataclasses import dataclass


@dataclass
class Opportunity:
    id: int | None
    title: str
    provider: str
    type: str
    description: str
    requirements: str
    required_skills: str
    location: str
    deadline: str
    official_link: str = ""
    created_by: int | None = None
    company_name: str = ""
    days_left: int | None = None
    deadline_status: str = "Open"
    deadline_score: int | None = None
    skill_match_score: int | None = None
    document_score: int | None = None
    priority_score: int | None = None
    priority_label: str | None = None

    @classmethod
    def from_row(cls, row):
        row_keys = row.keys()
        return cls(
            id=row["id"],
            title=row["title"],
            provider=row["provider"],
            type=row["type"],
            description=row["description"],
            requirements=row["requirements"],
            official_link=row["official_link"] or "",
            required_skills=row["required_skills"],
            location=row["location"],
            deadline=row["deadline"],
            created_by=row["created_by"] if "created_by" in row_keys else None,
            company_name=row["company_name"] if "company_name" in row_keys else "",
        )

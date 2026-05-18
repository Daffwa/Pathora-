from dataclasses import dataclass


@dataclass
class User:
    id: int | None
    name: str
    email: str
    password_hash: str
    role: str = "jobseeker"
    skills: str = ""
    company_name: str = ""
    company_position: str = ""
    nickname: str = ""
    phone: str = ""
    birth_date: str = ""
    gender: str = ""
    domicile: str = ""
    bio: str = ""
    university: str = ""
    faculty: str = ""
    major: str = ""
    degree: str = ""
    semester: str = ""
    gpa: str = ""
    entry_year: str = ""
    desired_positions: str = ""
    preferred_program: str = ""
    preferred_locations: str = ""
    work_arrangement: str = ""
    interests: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio_url: str = ""
    avatar_path: str = ""
    updated_at: str = ""

    @classmethod
    def from_row(cls, row):
        row_keys = row.keys()
        return cls(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            password_hash=row["password_hash"],
            role=row["role"],
            skills=row["skills"] or "",
            company_name=row["company_name"] if "company_name" in row_keys else "",
            company_position=row["company_position"] if "company_position" in row_keys else "",
            nickname=row["nickname"] if "nickname" in row_keys else "",
            phone=row["phone"] if "phone" in row_keys else "",
            birth_date=row["birth_date"] if "birth_date" in row_keys else "",
            gender=row["gender"] if "gender" in row_keys else "",
            domicile=row["domicile"] if "domicile" in row_keys else "",
            bio=row["bio"] if "bio" in row_keys else "",
            university=row["university"] if "university" in row_keys else "",
            faculty=row["faculty"] if "faculty" in row_keys else "",
            major=row["major"] if "major" in row_keys else "",
            degree=row["degree"] if "degree" in row_keys else "",
            semester=row["semester"] if "semester" in row_keys else "",
            gpa=row["gpa"] if "gpa" in row_keys else "",
            entry_year=row["entry_year"] if "entry_year" in row_keys else "",
            desired_positions=row["desired_positions"] if "desired_positions" in row_keys else "",
            preferred_program=row["preferred_program"] if "preferred_program" in row_keys else "",
            preferred_locations=row["preferred_locations"] if "preferred_locations" in row_keys else "",
            work_arrangement=row["work_arrangement"] if "work_arrangement" in row_keys else "",
            interests=row["interests"] if "interests" in row_keys else "",
            linkedin=row["linkedin"] if "linkedin" in row_keys else "",
            github=row["github"] if "github" in row_keys else "",
            portfolio_url=row["portfolio_url"] if "portfolio_url" in row_keys else "",
            avatar_path=row["avatar_path"] if "avatar_path" in row_keys else "",
            updated_at=row["updated_at"] if "updated_at" in row_keys else "",
        )

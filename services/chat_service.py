import sqlite3
from datetime import datetime, timezone

from flask import url_for

from services.application_service import application_status_label
from services.auth_service import normalize_role
from services.constants import JAKARTA_TZ
from services.database_service import get_db


def chat_pair(user_id, contact_id):
    return tuple(sorted((int(user_id), int(contact_id))))


def chat_avatar_initials(name):
    words = [word for word in (name or "").strip().split() if word]
    if not words:
        return "U"
    return "".join(word[:1] for word in words[:2]).upper()


def now_utc():
    return datetime.now(timezone.utc)


def parse_chat_timestamp(timestamp):
    if not timestamp:
        return None

    if isinstance(timestamp, datetime):
        parsed_timestamp = timestamp
    else:
        text = str(timestamp).strip()
        if not text:
            return None

        try:
            parsed_timestamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            for date_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                try:
                    parsed_timestamp = datetime.strptime(text, date_format)
                    break
                except ValueError:
                    parsed_timestamp = None
            if parsed_timestamp is None:
                return None

    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)

    return parsed_timestamp.astimezone(timezone.utc)


def chat_timestamp_iso(timestamp):
    parsed_timestamp = parse_chat_timestamp(timestamp)
    if parsed_timestamp is None:
        return ""

    return parsed_timestamp.isoformat(timespec="seconds")


def to_jakarta(timestamp):
    parsed_timestamp = parse_chat_timestamp(timestamp)
    if parsed_timestamp is None:
        return None

    return parsed_timestamp.astimezone(JAKARTA_TZ)


def format_jakarta_clock(timestamp):
    jakarta_timestamp = to_jakarta(timestamp)
    if jakarta_timestamp is None:
        return ""

    return jakarta_timestamp.strftime("%H:%M")


def format_chat_contact_time(timestamp):
    jakarta_timestamp = to_jakarta(timestamp)
    if jakarta_timestamp is None:
        return ""

    today = datetime.now(JAKARTA_TZ).date()
    message_date = jakarta_timestamp.date()
    days_difference = (today - message_date).days

    if days_difference == 0:
        return jakarta_timestamp.strftime("%H:%M")
    if days_difference == 1:
        return "Kemarin"

    month_labels = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "Mei",
        6: "Jun",
        7: "Jul",
        8: "Agu",
        9: "Sep",
        10: "Okt",
        11: "Nov",
        12: "Des",
    }
    return f"{jakarta_timestamp.day:02d} {month_labels[jakarta_timestamp.month]}"


def format_chat_time(timestamp):
    return format_jakarta_clock(timestamp)


def get_chat_thread_id(user_id, contact_id):
    participant_one_id, participant_two_id = chat_pair(user_id, contact_id)
    row = get_db().execute(
        """
        SELECT id
        FROM chat_threads
        WHERE participant_one_id = ? AND participant_two_id = ?
        """,
        (participant_one_id, participant_two_id),
    ).fetchone()
    return row["id"] if row else None


def get_or_create_chat_thread_id(user_id, contact_id):
    thread_id = get_chat_thread_id(user_id, contact_id)
    if thread_id is not None:
        return thread_id

    participant_one_id, participant_two_id = chat_pair(user_id, contact_id)
    try:
        cursor = get_db().execute(
            """
            INSERT INTO chat_threads (participant_one_id, participant_two_id)
            VALUES (?, ?)
            """,
            (participant_one_id, participant_two_id),
        )
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return get_chat_thread_id(user_id, contact_id)


def chat_message_preview(message_payload):
    if message_payload.get("text"):
        return message_payload["text"]
    if message_payload.get("imageUrl"):
        return "Mengirim gambar"
    return "Belum ada pesan"


def chat_message_payload(message, current_user_id):
    created_at = chat_timestamp_iso(message["created_at"])
    attachment_path = message["attachment_path"] or ""
    attachment_type = message["attachment_type"] or ""
    image_url = ""
    if attachment_path and attachment_type == "image":
        image_url = url_for("chat_attachment_file", filename=attachment_path)

    return {
        "id": message["id"],
        "sender": "user" if message["sender_id"] == current_user_id else "contact",
        "type": "image" if image_url else "text",
        "text": message["body"] or "",
        "imageUrl": image_url,
        "imageName": message["attachment_name"] or "Gambar",
        "attachmentType": attachment_type,
        "createdAt": created_at,
        "time": format_chat_time(message["created_at"]),
        "contactTime": format_chat_contact_time(message["created_at"]),
    }


def get_chat_messages(thread_id, current_user_id):
    if thread_id is None:
        return []

    rows = get_db().execute(
        """
        SELECT
            id,
            sender_id,
            body,
            attachment_path,
            attachment_type,
            attachment_name,
            created_at
        FROM chat_messages
        WHERE thread_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        (thread_id,),
    ).fetchall()
    return [chat_message_payload(row, current_user_id) for row in rows]


def get_recruiter_chat_relation(recruiter_id, applicant_id):
    return get_db().execute(
        """
        SELECT
            applications.status,
            applications.updated_at,
            opportunities.title AS opportunity_title,
            opportunities.provider AS opportunity_provider
        FROM applications
        JOIN opportunities ON opportunities.id = applications.opportunity_id
        WHERE applications.user_id = ?
          AND opportunities.created_by = ?
        ORDER BY applications.updated_at DESC, applications.id DESC
        LIMIT 1
        """,
        (applicant_id, recruiter_id),
    ).fetchone()


def get_jobseeker_chat_relation(jobseeker_id, recruiter_id):
    return get_db().execute(
        """
        SELECT
            applications.status,
            applications.updated_at,
            opportunities.title AS opportunity_title,
            opportunities.provider AS opportunity_provider
        FROM applications
        JOIN opportunities ON opportunities.id = applications.opportunity_id
        WHERE applications.user_id = ?
          AND opportunities.created_by = ?
        ORDER BY applications.updated_at DESC, applications.id DESC
        LIMIT 1
        """,
        (jobseeker_id, recruiter_id),
    ).fetchone()


def build_chat_contact_payload(contact, relation, current_role, thread_id, messages):
    if current_role == "recruiter":
        role_text = f"Pelamar untuk {relation['opportunity_title']}"
        status_text = application_status_label(relation["status"])
        empty_text = "Belum ada pesan. Mulai percakapan dengan pelamar ini."
    else:
        company_name = (
            contact["company_name"]
            or relation["opportunity_provider"]
            or "Perusahaan"
        )
        role_text = f"Recruiter at {company_name}"
        status_text = contact["company_position"] or "Recruiter"
        empty_text = "Belum ada pesan. Mulai percakapan dengan recruiter ini."

    last_message = chat_message_preview(messages[-1]) if messages else "Belum ada pesan"
    last_time = messages[-1]["contactTime"] if messages else ""
    sort_time = messages[-1]["createdAt"] if messages else chat_timestamp_iso(relation["updated_at"])

    return {
        "id": str(contact["id"]),
        "contactId": contact["id"],
        "threadId": thread_id,
        "name": contact["name"],
        "role": role_text,
        "status": status_text,
        "avatar": chat_avatar_initials(contact["name"]),
        "lastMessage": last_message,
        "time": last_time,
        "sortTime": sort_time,
        "emptyText": empty_text,
        "messages": messages,
    }


def get_chat_contact_payload(current_user_id, current_role, contact_id):
    if contact_id == current_user_id:
        return None

    contact = get_db().execute(
        """
        SELECT id, name, email, role, company_name, company_position
        FROM users
        WHERE id = ?
        """,
        (contact_id,),
    ).fetchone()
    if contact is None:
        return None

    relation = None
    if current_role == "recruiter" and normalize_role(contact["role"]) == "jobseeker":
        relation = get_recruiter_chat_relation(current_user_id, contact_id)
    elif current_role == "jobseeker" and normalize_role(contact["role"]) == "recruiter":
        relation = get_jobseeker_chat_relation(current_user_id, contact_id)

    if relation is None:
        return None

    thread_id = get_chat_thread_id(current_user_id, contact_id)
    messages = get_chat_messages(thread_id, current_user_id)
    return build_chat_contact_payload(
        contact,
        relation,
        current_role,
        thread_id,
        messages,
    )


def get_chat_relation_rows(current_user_id, current_role):
    if current_role == "recruiter":
        return get_db().execute(
            """
            SELECT
                users.id,
                users.name,
                users.email,
                users.role,
                users.company_name,
                users.company_position,
                applications.status,
                applications.updated_at,
                opportunities.title AS opportunity_title,
                opportunities.provider AS opportunity_provider
            FROM applications
            JOIN opportunities ON opportunities.id = applications.opportunity_id
            JOIN users ON users.id = applications.user_id
            WHERE opportunities.created_by = ?
            ORDER BY applications.updated_at DESC, applications.id DESC
            """,
            (current_user_id,),
        ).fetchall()

    if current_role == "jobseeker":
        return get_db().execute(
            """
            SELECT
                users.id,
                users.name,
                users.email,
                users.role,
                users.company_name,
                users.company_position,
                applications.status,
                applications.updated_at,
                opportunities.title AS opportunity_title,
                opportunities.provider AS opportunity_provider
            FROM applications
            JOIN opportunities ON opportunities.id = applications.opportunity_id
            JOIN users ON users.id = opportunities.created_by
            WHERE applications.user_id = ?
              AND opportunities.created_by IS NOT NULL
            ORDER BY applications.updated_at DESC, applications.id DESC
            """,
            (current_user_id,),
        ).fetchall()

    return []


def get_chat_conversations(current_user_id, current_role, selected_contact_id=None):
    contacts = {}

    for row in get_chat_relation_rows(current_user_id, current_role):
        contact_id = row["id"]
        if contact_id in contacts:
            continue

        thread_id = get_chat_thread_id(current_user_id, contact_id)
        messages = get_chat_messages(thread_id, current_user_id)
        contacts[contact_id] = build_chat_contact_payload(
            row,
            row,
            current_role,
            thread_id,
            messages,
        )

    if selected_contact_id and selected_contact_id not in contacts:
        selected_contact = get_chat_contact_payload(
            current_user_id,
            current_role,
            selected_contact_id,
        )
        if selected_contact is not None:
            contacts[selected_contact_id] = selected_contact

    conversations = list(contacts.values())
    conversations.sort(
        key=lambda conversation: conversation["sortTime"] or "",
        reverse=True,
    )
    return conversations

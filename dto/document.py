from dataclasses import dataclass


@dataclass
class Document:
    document_id: int | None
    user_id: int
    doc_type: str
    file_name: str = ""
    file_path: str = ""
    is_uploaded: bool = False
    notes: str = ""

    @classmethod
    def from_row(cls, row, user_id):
        if row is None:
            return cls(document_id=None, user_id=user_id, doc_type="")

        return cls(
            document_id=row["id"],
            user_id=row["user_id"],
            doc_type=row["doc_type"],
            file_name=row["file_name"] or "",
            file_path=row["file_path"] or "",
            is_uploaded=bool(row["is_uploaded"]),
            notes=row["notes"] or "",
        )

    def mark_uploaded(self, file_name="", file_path=""):
        self.is_uploaded = True
        self.file_name = file_name
        self.file_path = file_path

    def reset(self):
        self.is_uploaded = False
        self.file_name = ""
        self.file_path = ""
        self.notes = ""

    def is_complete(self):
        return self.is_uploaded

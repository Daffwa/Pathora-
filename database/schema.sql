CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'jobseeker' CHECK (role IN ('jobseeker', 'recruiter', 'admin')),
    account_status TEXT NOT NULL DEFAULT 'approved' CHECK (account_status IN ('pending', 'approved', 'rejected')),
    skills TEXT DEFAULT '',
    company_name TEXT DEFAULT '',
    company_position TEXT DEFAULT '',
    nickname TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    birth_date TEXT DEFAULT '',
    gender TEXT DEFAULT '',
    domicile TEXT DEFAULT '',
    bio TEXT DEFAULT '',
    university TEXT DEFAULT '',
    faculty TEXT DEFAULT '',
    major TEXT DEFAULT '',
    degree TEXT DEFAULT '',
    semester TEXT DEFAULT '',
    gpa TEXT DEFAULT '',
    entry_year TEXT DEFAULT '',
    desired_positions TEXT DEFAULT '',
    preferred_program TEXT DEFAULT '',
    preferred_locations TEXT DEFAULT '',
    work_arrangement TEXT DEFAULT '',
    interests TEXT DEFAULT '',
    linkedin TEXT DEFAULT '',
    github TEXT DEFAULT '',
    portfolio_url TEXT DEFAULT '',
    avatar_path TEXT DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    provider TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('internship', 'scholarship')),
    description TEXT NOT NULL,
    requirements TEXT NOT NULL,
    official_link TEXT DEFAULT '',
    required_skills TEXT NOT NULL,
    location TEXT NOT NULL,
    deadline TEXT NOT NULL,
    created_by INTEGER,
    company_name TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    opportunity_id INTEGER NOT NULL,
    saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, opportunity_id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (opportunity_id) REFERENCES opportunities (id)
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    opportunity_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'Sudah Daftar',
    notes TEXT DEFAULT '',
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, opportunity_id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (opportunity_id) REFERENCES opportunities (id)
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    doc_type TEXT NOT NULL,
    file_name TEXT DEFAULT '',
    file_path TEXT DEFAULT '',
    is_uploaded INTEGER NOT NULL DEFAULT 0,
    notes TEXT DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, doc_type),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS chat_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_one_id INTEGER NOT NULL,
    participant_two_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (participant_one_id, participant_two_id),
    CHECK (participant_one_id <> participant_two_id),
    FOREIGN KEY (participant_one_id) REFERENCES users (id),
    FOREIGN KEY (participant_two_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    attachment_path TEXT DEFAULT '',
    attachment_type TEXT DEFAULT '',
    attachment_name TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES chat_threads (id),
    FOREIGN KEY (sender_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    target_type TEXT DEFAULT '',
    target_id INTEGER,
    metadata TEXT DEFAULT '{}',
    ip_address TEXT DEFAULT '',
    user_agent TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Indexes for RBAC checks, ownership filters, and audit log review.
CREATE INDEX IF NOT EXISTS idx_users_role_account_status ON users (role, account_status);
CREATE INDEX IF NOT EXISTS idx_users_account_status ON users (account_status);
CREATE INDEX IF NOT EXISTS idx_opportunities_created_by_updated_at ON opportunities (created_by, updated_at);
CREATE INDEX IF NOT EXISTS idx_opportunities_type ON opportunities (type);
CREATE INDEX IF NOT EXISTS idx_bookmarks_user_saved_at ON bookmarks (user_id, saved_at);
CREATE INDEX IF NOT EXISTS idx_bookmarks_opportunity_id ON bookmarks (opportunity_id);
CREATE INDEX IF NOT EXISTS idx_applications_user_updated_at ON applications (user_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_applications_opportunity_id ON applications (opportunity_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_uploaded ON documents (user_id, is_uploaded);
CREATE INDEX IF NOT EXISTS idx_chat_threads_participant_one ON chat_threads (participant_one_id);
CREATE INDEX IF NOT EXISTS idx_chat_threads_participant_two ON chat_threads (participant_two_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_thread_created_at ON chat_messages (thread_id, created_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_sender_id ON chat_messages (sender_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_created_at ON audit_logs (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at_id ON audit_logs (created_at, id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_created_at ON audit_logs (action, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_target ON audit_logs (target_type, target_id);

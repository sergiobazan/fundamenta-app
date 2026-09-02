BEGIN;

CREATE TABLE IF NOT EXISTS app_users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    bio TEXT NOT NULL DEFAULT '',
    avatar_filename TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT app_users_email_normalized CHECK (email = LOWER(BTRIM(email))),
    CONSTRAINT app_users_email_unique UNIQUE (email),
    CONSTRAINT app_users_full_name_not_blank CHECK (LENGTH(BTRIM(full_name)) > 0)
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS auth_sessions_active_idx
    ON auth_sessions (token_hash, expires_at)
    WHERE revoked_at IS NULL;

COMMIT;

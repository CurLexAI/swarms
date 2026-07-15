# Copilot instructions

For Lex Sovereign Node changes, preserve offline-first and fail-closed behavior. Never commit credentials, auth keys, endpoint secrets, or real node identities. Registry data is metadata, not authorization. Use environment references for HMAC keys; reject duplicate key references. Installers must default to dry-run, and rollback must require explicit confirmation.

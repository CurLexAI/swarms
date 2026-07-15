# Lex Sovereign Node rollback

Stop using the node if registry validation, signature verification, policy review, or control-plane acceptance fails.

Linux: run `scripts/lex-node/rollback.sh --state-dir /var/lib/lex-sovereign-node --confirm`.

Windows: run `Install-LexSovereignNode.ps1 -Rollback -StateDirectory <approved-path> -ConfirmRollback`.

Then revoke the node and credentials in the authoritative control plane and remove its Tailscale tag/grants. Do not delete forensic records until incident retention requirements are met.

#!/usr/bin/env bash
# Generate a self-signed sovereign CA and server cert for local development.
# Production: replace with certs from your HSM / private CA.
set -euo pipefail

CERT_DIR="${1:-./certs}"
mkdir -p "$CERT_DIR"

echo "[INFO] Generating sovereign CA..."
openssl genrsa -out "$CERT_DIR/ca.key" 4096

openssl req -new -x509 -days 3650 -key "$CERT_DIR/ca.key" \
  -out "$CERT_DIR/ca.crt" \
  -subj "/C=SA/O=Qarar Sovereign/CN=Mihwar Root CA"

echo "[INFO] Generating server key and CSR..."
openssl genrsa -out "$CERT_DIR/mihwar.key" 4096

openssl req -new -key "$CERT_DIR/mihwar.key" \
  -out "$CERT_DIR/mihwar.csr" \
  -subj "/C=SA/O=Qarar Sovereign/CN=mihwar.qarar.sa"

# SAN extension
cat > "$CERT_DIR/san.ext" <<EOF
[req]
req_extensions = v3_req
[v3_req]
subjectAltName = @alt_names
[alt_names]
DNS.1 = mihwar.qarar.sa
DNS.2 = localhost
IP.1  = 127.0.0.1
IP.2  = 10.200.200.1
EOF

echo "[INFO] Signing server certificate..."
openssl x509 -req -days 825 \
  -in "$CERT_DIR/mihwar.csr" \
  -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" -CAcreateserial \
  -out "$CERT_DIR/mihwar.crt" \
  -extfile "$CERT_DIR/san.ext" -extensions v3_req

echo "[OK] Certificates written to $CERT_DIR"
echo "  CA:     $CERT_DIR/ca.crt"
echo "  Server: $CERT_DIR/mihwar.crt + mihwar.key"
echo ""
echo "WARNING: Do NOT commit these files. Add certs/ to .gitignore."

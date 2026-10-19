#!/bin/sh
set -eu

case "$MYSQL_USER" in
  ""|*[!A-Za-z0-9_]*)
    echo "MYSQL_USER must contain only letters, numbers, and underscores." >&2
    exit 1
    ;;
esac

case "$MYSQL_READONLY_USER" in
  ""|*[!A-Za-z0-9_]*)
    echo "MYSQL_READONLY_USER must contain only letters, numbers, and underscores." >&2
    exit 1
    ;;
esac

case "$MYSQL_DATABASE" in
  ""|*[!A-Za-z0-9_]*)
    echo "MYSQL_DATABASE must contain only letters, numbers, and underscores." >&2
    exit 1
    ;;
esac

if [ -z "$MYSQL_ROOT_PASSWORD" ] || [ -z "$MYSQL_PASSWORD" ] || [ -z "$MYSQL_READONLY_PASSWORD" ]; then
  echo "MySQL root, read-write, and read-only credentials must be configured." >&2
  exit 1
fi
if [ "$MYSQL_READONLY_USER" = "$MYSQL_USER" ]; then
  echo "The MySQL read-only and read-write users must be different." >&2
  exit 1
fi

escaped_rw_password=$(printf '%s' "$MYSQL_PASSWORD" | sed "s/'/''/g")
escaped_password=$(printf '%s' "$MYSQL_READONLY_PASSWORD" | sed "s/'/''/g")
MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql \
  --protocol=TCP \
  --host="$MYSQL_HOST" \
  --user=root \
  "$MYSQL_DATABASE" <<SQL
CREATE USER IF NOT EXISTS '$MYSQL_READONLY_USER'@'%' IDENTIFIED BY '$escaped_password';
CREATE USER IF NOT EXISTS '$MYSQL_USER'@'%' IDENTIFIED BY '$escaped_rw_password';
ALTER USER '$MYSQL_READONLY_USER'@'%' IDENTIFIED BY '$escaped_password';
ALTER USER '$MYSQL_USER'@'%' IDENTIFIED BY '$escaped_rw_password';
CREATE TABLE IF NOT EXISTS client_accounts (
  client_id VARCHAR(32) PRIMARY KEY,
  email VARCHAR(254) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_client_accounts_client
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
REVOKE ALL PRIVILEGES, GRANT OPTION FROM '$MYSQL_READONLY_USER'@'%';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM '$MYSQL_USER'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%';
GRANT SELECT ON \`$MYSQL_DATABASE\`.\`clients\` TO '$MYSQL_READONLY_USER'@'%';
GRANT SELECT ON \`$MYSQL_DATABASE\`.\`reports\` TO '$MYSQL_READONLY_USER'@'%';
GRANT SELECT ON \`$MYSQL_DATABASE\`.\`market_metrics\` TO '$MYSQL_READONLY_USER'@'%';
FLUSH PRIVILEGES;
SQL

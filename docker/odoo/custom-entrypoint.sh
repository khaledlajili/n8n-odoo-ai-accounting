#!/bin/bash
set -e

# Inject the master password into Odoo's config file if set and not already present.
if [ -n "$ODOO_MASTER_PASSWORD" ] && ! grep -qE '^[[:space:]]*admin_passwd[[:space:]]*=' /etc/odoo/odoo.conf 2>/dev/null; then
    echo "admin_passwd = ${ODOO_MASTER_PASSWORD}" >> /etc/odoo/odoo.conf
fi

# Ensure 'odoo' is the first argument so the upstream entrypoint runs its
# postgres-wait and DB-credential logic.
if [ "$1" != "odoo" ]; then
    set -- odoo "$@"
fi

exec /entrypoint.sh "$@"

#!/bin/bash
#
# Script bash d'automatisation DNS pour Bind9
# Permet d'ajouter et supprimer des enregistrements DNS via n8n
#

# Configuration
ZONE_FILE="/etc/bind/zones/db.internal.local"
ZONE_NAME="internal.local"
BACKUP_DIR="/var/backups/dns"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Fonction pour créer le répertoire de backup
ensure_backup_dir() {
    sudo mkdir -p "$BACKUP_DIR"
}

# Fonction pour sauvegarder la zone
backup_zone_file() {
    ensure_backup_dir
    if [ -f "$ZONE_FILE" ]; then
        sudo cp "$ZONE_FILE" "${BACKUP_DIR}/db.${ZONE_NAME}.${TIMESTAMP}"
        echo "Backup created: ${BACKUP_DIR}/db.${ZONE_NAME}.${TIMESTAMP}"
    fi
}

# Fonction pour incrémenter le serial
increment_serial() {
    local zone_file="$1"
    local today=$(date +%Y%m%d)
    local current_serial=$(grep -E "^\s*[0-9]{10}\s+; Serial" "$zone_file" | head -1 | awk '{print $1}')
    
    if [ -z "$current_serial" ]; then
        # Pas de serial trouvé, en créer un
        local new_serial="${today}01"
    else
        local serial_date="${current_serial:0:8}"
        local serial_num="${current_serial:8:2}"
        
        if [ "$serial_date" = "$today" ]; then
            # Même jour, incrémenter le numéro
            serial_num=$((10#$serial_num + 1))
            new_serial=$(printf "%s%02d" "$today" "$serial_num")
        else
            # Nouveau jour, réinitialiser
            new_serial="${today}01"
        fi
    fi
    
    # Remplacer le serial
    sudo sed -i "s/^\s*[0-9]\{10\}\s\+; Serial/${new_serial} ; Serial/" "$zone_file"
    echo "$new_serial"
}

# Fonction pour ajouter un enregistrement
add_record() {
    local hostname="$1"
    local record_type="$2"
    local value="$3"
    local ttl="${4:-3600}"
    
    # Vérifier si l'enregistrement existe déjà
    if grep -q "^${hostname}" "$ZONE_FILE"; then
        if grep -q "^${hostname}.*${record_type}" "$ZONE_FILE"; then
            echo "{\"success\": false, \"error\": \"Record ${hostname} ${record_type} already exists\"}"
            return 1
        fi
    fi
    
    # Sauvegarder
    backup_zone_file
    
    # Formater l'enregistrement selon le type
    case "${record_type^^}" in
        A)
            new_record="${hostname}${hostname:+ }$(printf '%-*s' $((30 - ${#hostname})) '') ${ttl}    IN    A      ${value}"
            ;;
        AAAA)
            new_record="${hostname}${hostname:+ }$(printf '%-*s' $((30 - ${#hostname})) '') ${ttl}    IN    AAAA   ${value}"
            ;;
        CNAME)
            new_record="${hostname}${hostname:+ }$(printf '%-*s' $((30 - ${#hostname})) '') ${ttl}    IN    CNAME  ${value}"
            ;;
        MX)
            local priority=$(echo "$value" | awk '{print $1}')
            local mailserver=$(echo "$value" | awk '{print $2}')
            new_record="${hostname}${hostname:+ }$(printf '%-*s' $((30 - ${#hostname})) '') ${ttl}    IN    MX     ${priority} ${mailserver}"
            ;;
        TXT)
            new_record="${hostname}${hostname:+ }$(printf '%-*s' $((30 - ${#hostname})) '') ${ttl}    IN    TXT    \"${value}\""
            ;;
        *)
            echo "{\"success\": false, \"error\": \"Unsupported record type: ${record_type}\"}"
            return 1
            ;;
    esac
    
    # Trouver la position d'insertion (après les enregistrements NS)
    local insert_line=$(grep -n "@.*IN.*NS" "$ZONE_FILE" | tail -1 | cut -d: -f1)
    if [ -z "$insert_line" ]; then
        insert_line=$(grep -n ");" "$ZONE_FILE" | head -1 | cut -d: -f1)
    fi
    
    if [ -n "$insert_line" ]; then
        sudo sed -i "${insert_line}a\\${new_record}" "$ZONE_FILE"
    else
        echo "$new_record" | sudo tee -a "$ZONE_FILE" > /dev/null
    fi
    
    # Incrémenter le serial
    increment_serial "$ZONE_FILE"
    
    # Valider la zone
    if ! sudo named-checkzone "$ZONE_NAME" "$ZONE_FILE" > /dev/null 2>&1; then
        echo "{\"success\": false, \"error\": \"Zone validation failed\"}"
        return 1
    fi
    
    # Recharger Bind9
    if ! sudo systemctl reload bind9; then
        echo "{\"success\": false, \"error\": \"Failed to reload Bind9\"}"
        return 1
    fi
    
    echo "{\"success\": true, \"message\": \"Record ${hostname} ${record_type} added successfully\"}"
    return 0
}

# Fonction pour supprimer un enregistrement
remove_record() {
    local hostname="$1"
    local record_type="$2"
    
    # Vérifier si l'enregistrement existe
    if [ -n "$record_type" ]; then
        if ! grep -q "^${hostname}.*${record_type}" "$ZONE_FILE"; then
            echo "{\"success\": false, \"error\": \"Record ${hostname} ${record_type} not found\"}"
            return 1
        fi
    else
        if ! grep -q "^${hostname}" "$ZONE_FILE"; then
            echo "{\"success\": false, \"error\": \"Record ${hostname} not found\"}"
            return 1
        fi
    fi
    
    # Sauvegarder
    backup_zone_file
    
    # Supprimer l'enregistrement
    if [ -n "$record_type" ]; then
        sudo sed -i "/^${hostname}.*${record_type}/d" "$ZONE_FILE"
    else
        sudo sed -i "/^${hostname}/d" "$ZONE_FILE"
    fi
    
    # Incrémenter le serial
    increment_serial "$ZONE_FILE"
    
    # Valider la zone
    if ! sudo named-checkzone "$ZONE_NAME" "$ZONE_FILE" > /dev/null 2>&1; then
        echo "{\"success\": false, \"error\": \"Zone validation failed\"}"
        return 1
    fi
    
    # Recharger Bind9
    if ! sudo systemctl reload bind9; then
        echo "{\"success\": false, \"error\": \"Failed to reload Bind9\"}"
        return 1
    fi
    
    echo "{\"success\": true, \"message\": \"Record ${hostname} ${record_type:-} removed successfully\"}"
    return 0
}

# Fonction pour lister les enregistrements
list_records() {
    if [ ! -f "$ZONE_FILE" ]; then
        echo "{\"success\": false, \"error\": \"Zone file not found\"}"
        return 1
    fi
    
    # Extraire les enregistrements (sauf SOA et NS)
    records=$(grep -v "^;" "$ZONE_FILE" | grep -v "^$" | grep -v "SOA" | grep -v "@.*IN.*NS" | grep "IN" | jq -R -s -c 'split("\n") | map(select(length > 0))')
    
    echo "{\"success\": true, \"records\": $records}"
}

# Point d'entrée principal
ACTION="$1"

case "$ACTION" in
    add)
        if [ $# -lt 4 ]; then
            echo "{\"error\": \"Usage: add <hostname> <type> <value> [ttl]\"}"
            exit 1
        fi
        add_record "$2" "$3" "$4" "${5:-3600}"
        ;;
    remove)
        if [ $# -lt 2 ]; then
            echo "{\"error\": \"Usage: remove <hostname> [type]\"}"
            exit 1
        fi
        remove_record "$2" "$3"
        ;;
    list)
        list_records
        ;;
    *)
        echo "{\"error\": \"Unknown action: ${ACTION}\"}"
        echo "Usage: $0 {add|remove|list} [arguments]"
        exit 1
        ;;
esac


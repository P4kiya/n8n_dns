#!/usr/bin/env python3
"""
Script d'automatisation DNS pour Bind9
Permet d'ajouter et supprimer des enregistrements DNS via n8n
"""

import os
import sys
import json
import subprocess
import re
from datetime import datetime
from pathlib import Path

# Configuration
ZONE_FILE = "/etc/bind/zones/db.internal.local"
ZONE_NAME = "internal.local"
NAMED_CONF_LOCAL = "/etc/bind/named.conf.local"
BACKUP_DIR = "/var/backups/dns"
BIND_RELOAD_CMD = ["sudo", "systemctl", "reload", "bind9"]

def ensure_backup_dir():
    """Créer le répertoire de backup s'il n'existe pas"""
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)

def backup_zone_file():
    """Créer une sauvegarde de la zone DNS"""
    ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{BACKUP_DIR}/db.{ZONE_NAME}.{timestamp}"
    
    if os.path.exists(ZONE_FILE):
        subprocess.run(["sudo", "cp", ZONE_FILE, backup_file], check=True)
        return backup_file
    return None

def read_zone_file():
    """Lire le contenu du fichier de zone"""
    try:
        with open(ZONE_FILE, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return None
    except PermissionError:
        # Essayer avec sudo
        result = subprocess.run(["sudo", "cat", ZONE_FILE], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        raise

def write_zone_file(content):
    """Écrire le contenu dans le fichier de zone"""
    # Écrire dans un fichier temporaire
    temp_file = "/tmp/db.internal.local.tmp"
    with open(temp_file, 'w') as f:
        f.write(content)
    
    # Copier avec sudo
    subprocess.run(["sudo", "cp", temp_file, ZONE_FILE], check=True)
    subprocess.run(["sudo", "chown", "bind:bind", ZONE_FILE], check=True)
    subprocess.run(["sudo", "chmod", "644", ZONE_FILE], check=True)
    os.remove(temp_file)

def increment_serial(zone_content):
    """Incrémenter le numéro de série de la zone"""
    # Format: YYYYMMDDNN
    pattern = r'(\d{8})(\d{2})\s+; Serial'
    match = re.search(pattern, zone_content)
    
    if match:
        date_part = match.group(1)
        num_part = int(match.group(2))
        today = datetime.now().strftime("%Y%m%d")
        
        if date_part == today:
            num_part += 1
        else:
            date_part = today
            num_part = 1
        
        new_serial = f"{date_part}{num_part:02d}"
        zone_content = re.sub(pattern, f"{new_serial} ; Serial", zone_content)
    else:
        # Si pas de serial trouvé, en ajouter un
        today = datetime.now().strftime("%Y%m%d")
        new_serial = f"{today}01"
        zone_content = re.sub(r'(\d{8}\d{2}\s+; Serial)', 
                             f"{new_serial} ; Serial", zone_content)
    
    return zone_content

def add_record(hostname, record_type, value, ttl=3600):
    """Ajouter un enregistrement DNS"""
    zone_content = read_zone_file()
    if zone_content is None:
        return {"success": False, "error": "Zone file not found"}
    
    # Vérifier si l'enregistrement existe déjà
    pattern = rf'^{hostname}\s+.*{record_type}'
    if re.search(pattern, zone_content, re.MULTILINE):
        return {"success": False, "error": f"Record {hostname} {record_type} already exists"}
    
    # Trouver où insérer (après les enregistrements SOA et NS)
    # Chercher la fin de la section NS
    ns_end = re.search(r'@\s+IN\s+NS\s+.*\n', zone_content)
    if ns_end:
        insert_pos = ns_end.end()
    else:
        # Si pas de NS, insérer après SOA
        soa_end = re.search(r'\)\s*;', zone_content)
        if soa_end:
            insert_pos = soa_end.end()
        else:
            insert_pos = len(zone_content)
    
    # Formater l'enregistrement selon le type
    if record_type.upper() == 'A':
        new_record = f"{hostname:<30} {ttl}    IN    A      {value}\n"
    elif record_type.upper() == 'AAAA':
        new_record = f"{hostname:<30} {ttl}    IN    AAAA   {value}\n"
    elif record_type.upper() == 'CNAME':
        new_record = f"{hostname:<30} {ttl}    IN    CNAME  {value}\n"
    elif record_type.upper() == 'MX':
        priority, mailserver = value.split() if ' ' in value else ('10', value)
        new_record = f"{hostname:<30} {ttl}    IN    MX     {priority} {mailserver}\n"
    elif record_type.upper() == 'TXT':
        new_record = f"{hostname:<30} {ttl}    IN    TXT    \"{value}\"\n"
    else:
        return {"success": False, "error": f"Unsupported record type: {record_type}"}
    
    # Insérer l'enregistrement
    zone_content = zone_content[:insert_pos] + new_record + zone_content[insert_pos:]
    
    # Incrémenter le serial
    zone_content = increment_serial(zone_content)
    
    # Sauvegarder
    backup_zone_file()
    
    # Écrire le nouveau contenu
    try:
        write_zone_file(zone_content)
        
        # Valider la syntaxe avec named-checkzone
        result = subprocess.run(
            ["sudo", "named-checkzone", ZONE_NAME, ZONE_FILE],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            return {"success": False, "error": f"Zone validation failed: {result.stderr}"}
        
        # Recharger Bind9
        reload_result = subprocess.run(BIND_RELOAD_CMD, capture_output=True, text=True)
        if reload_result.returncode != 0:
            return {"success": False, "error": f"Failed to reload Bind9: {reload_result.stderr}"}
        
        return {"success": True, "message": f"Record {hostname} {record_type} added successfully"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def remove_record(hostname, record_type=None):
    """Supprimer un enregistrement DNS"""
    zone_content = read_zone_file()
    if zone_content is None:
        return {"success": False, "error": "Zone file not found"}
    
    # Construire le pattern de recherche
    if record_type:
        pattern = rf'^{hostname}\s+.*{record_type}.*\n'
    else:
        # Supprimer tous les enregistrements pour ce hostname
        pattern = rf'^{hostname}\s+.*\n'
    
    # Vérifier si l'enregistrement existe
    if not re.search(pattern, zone_content, re.MULTILINE):
        return {"success": False, "error": f"Record {hostname} {record_type or ''} not found"}
    
    # Supprimer l'enregistrement
    zone_content = re.sub(pattern, '', zone_content, flags=re.MULTILINE)
    
    # Incrémenter le serial
    zone_content = increment_serial(zone_content)
    
    # Sauvegarder
    backup_zone_file()
    
    # Écrire le nouveau contenu
    try:
        write_zone_file(zone_content)
        
        # Valider la syntaxe
        result = subprocess.run(
            ["sudo", "named-checkzone", ZONE_NAME, ZONE_FILE],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            return {"success": False, "error": f"Zone validation failed: {result.stderr}"}
        
        # Recharger Bind9
        reload_result = subprocess.run(BIND_RELOAD_CMD, capture_output=True, text=True)
        if reload_result.returncode != 0:
            return {"success": False, "error": f"Failed to reload Bind9: {reload_result.stderr}"}
        
        return {"success": True, "message": f"Record {hostname} {record_type or ''} removed successfully"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_records():
    """Lister tous les enregistrements DNS"""
    zone_content = read_zone_file()
    if zone_content is None:
        return {"success": False, "error": "Zone file not found"}
    
    # Extraire tous les enregistrements (sauf SOA et NS)
    records = []
    lines = zone_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith(';') or line.startswith('$'):
            continue
        if 'SOA' in line or (line.startswith('@') and 'NS' in line):
            continue
        if re.match(r'^\S+\s+.*IN\s+', line):
            records.append(line)
    
    return {"success": True, "records": records}

def main():
    """Point d'entrée principal pour les requêtes HTTP"""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing action parameter"}))
        sys.exit(1)
    
    action = sys.argv[1]
    
    try:
        if action == "add":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "Usage: add <hostname> <type> <value> [ttl]"}))
                sys.exit(1)
            hostname = sys.argv[2]
            record_type = sys.argv[3]
            value = sys.argv[4]
            ttl = int(sys.argv[5]) if len(sys.argv) > 5 else 3600
            result = add_record(hostname, record_type, value, ttl)
            print(json.dumps(result))
        
        elif action == "remove":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: remove <hostname> [type]"}))
                sys.exit(1)
            hostname = sys.argv[2]
            record_type = sys.argv[3] if len(sys.argv) > 3 else None
            result = remove_record(hostname, record_type)
            print(json.dumps(result))
        
        elif action == "list":
            result = list_records()
            print(json.dumps(result))
        
        else:
            print(json.dumps({"error": f"Unknown action: {action}"}))
            sys.exit(1)
    
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()


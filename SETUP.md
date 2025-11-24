# Guide d'Installation et Configuration

## Prérequis

- Ubuntu Server (20.04 ou supérieur) sur VMware
- Accès root ou sudo
- Connexion réseau configurée
- Clé SSH configurée pour l'automatisation

## 1. Installation de Bind9

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Bind9
sudo apt install -y bind9 bind9utils bind9-doc

# Vérifier l'installation
sudo systemctl status bind9
```

## 2. Configuration de Bind9

### 2.1 Créer le répertoire pour les zones

```bash
sudo mkdir -p /etc/bind/zones
sudo chown bind:bind /etc/bind/zones
```

### 2.2 Créer le fichier de zone initial

Créer `/etc/bind/zones/db.internal.local` avec le contenu suivant :

```bash
sudo nano /etc/bind/zones/db.internal.local
```

Contenu initial (voir `zone_before.txt` pour référence) :

```
$TTL    3600
$ORIGIN internal.local.
@       IN      SOA     ns1.internal.local. admin.internal.local. (
                        2024010101      ; Serial
                        3600            ; Refresh
                        1800            ; Retry
                        604800          ; Expire
                        86400 )         ; Minimum TTL

; Serveurs de noms
@       IN      NS      ns1.internal.local.
@       IN      NS      ns2.internal.local.

; Enregistrements A
ns1     IN      A       192.168.1.10
ns2     IN      A       192.168.1.11
www     IN      A       192.168.1.20
mail    IN      A       192.168.1.25

; Enregistrements CNAME
ftp     IN      CNAME   www

; Enregistrements MX
@       IN      MX      10      mail.internal.local.
```

### 2.3 Configurer named.conf.local

```bash
sudo nano /etc/bind/named.conf.local
```

Ajouter :

```
zone "internal.local" {
    type master;
    file "/etc/bind/zones/db.internal.local";
    allow-update { none; };
};
```

### 2.4 Valider et tester la configuration

```bash
# Valider la syntaxe de la zone
sudo named-checkzone internal.local /etc/bind/zones/db.internal.local

# Valider la configuration globale
sudo named-checkconf

# Redémarrer Bind9
sudo systemctl restart bind9
sudo systemctl enable bind9
```

### 2.5 Configurer le résolveur local (optionnel)

```bash
sudo nano /etc/resolv.conf
```

Ajouter :
```
nameserver 127.0.0.1
search internal.local
```

## 3. Installation de n8n

### 3.1 Installation via npm (recommandé)

```bash
# Installer Node.js et npm
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Installer n8n globalement
sudo npm install n8n -g

# Démarrer n8n (pour test)
n8n start
```

### 3.2 Installation via Docker (alternative)

```bash
# Installer Docker
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# Créer un docker-compose.yml
cat > docker-compose.yml << EOF
version: '3.8'
services:
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=changeme
    volumes:
      - ~/.n8n:/home/node/.n8n
EOF

# Démarrer n8n
sudo docker-compose up -d
```

### 3.3 Installation comme service systemd

```bash
# Créer le service systemd
sudo nano /etc/systemd/system/n8n.service
```

Contenu :
```
[Unit]
Description=n8n
After=network.target

[Service]
Type=simple
User=ubuntu
Environment=N8N_BASIC_AUTH_ACTIVE=true
Environment=N8N_BASIC_AUTH_USER=admin
Environment=N8N_BASIC_AUTH_PASSWORD=changeme
ExecStart=/usr/bin/n8n start
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Activer et démarrer le service
sudo systemctl daemon-reload
sudo systemctl enable n8n
sudo systemctl start n8n
```

## 4. Configuration des Scripts DNS

### 4.1 Créer le répertoire pour les scripts

```bash
sudo mkdir -p /opt/dns-automation
sudo chown $USER:$USER /opt/dns-automation
```

### 4.2 Copier les scripts

```bash
# Copier les scripts depuis votre machine locale vers le serveur
# Utiliser scp ou copier-coller le contenu

# Exemple avec scp (depuis votre machine locale)
scp dns_manager.py dns_manager.sh user@your-server:/opt/dns-automation/
```

### 4.3 Configurer les permissions

```bash
# Rendre les scripts exécutables
sudo chmod +x /opt/dns-automation/dns_manager.py
sudo chmod +x /opt/dns-automation/dns_manager.sh

# Installer les dépendances Python (si nécessaire)
sudo apt install -y python3 python3-pip
```

### 4.4 Configurer sudoers pour n8n

```bash
sudo visudo
```

Ajouter à la fin du fichier (remplacer `ubuntu` par votre utilisateur) :

```
# Permettre à n8n d'exécuter les commandes DNS sans mot de passe
ubuntu ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload bind9
ubuntu ALL=(ALL) NOPASSWD: /usr/bin/named-checkzone
ubuntu ALL=(ALL) NOPASSWD: /bin/cp /tmp/db.internal.local.tmp /etc/bind/zones/db.internal.local
ubuntu ALL=(ALL) NOPASSWD: /usr/bin/chown bind:bind /etc/bind/zones/db.internal.local
ubuntu ALL=(ALL) NOPASSWD: /usr/bin/chmod 644 /etc/bind/zones/db.internal.local
ubuntu ALL=(ALL) NOPASSWD: /bin/cat /etc/bind/zones/db.internal.local
```

### 4.5 Créer le répertoire de backup

```bash
sudo mkdir -p /var/backups/dns
sudo chown $USER:$USER /var/backups/dns
```

## 5. Configuration de n8n

### 5.1 Accéder à l'interface n8n

Ouvrir un navigateur et aller à : `http://votre-serveur:5678`

### 5.2 Importer le workflow

1. Dans n8n, cliquer sur "Workflows" dans le menu
2. Cliquer sur "Import from File"
3. Sélectionner le fichier `n8n_workflow_dns_automation.json`
4. Activer le workflow

### 5.3 Configurer les webhooks

Les webhooks seront automatiquement créés lors de l'import. Notez les URLs :
- `http://votre-serveur:5678/webhook/dns` (Ajouter)
- `http://votre-serveur:5678/webhook/dns-remove` (Supprimer)
- `http://votre-serveur:5678/webhook/dns-list` (Lister)

## 6. Tests

### 6.1 Test manuel du script Python

```bash
# Ajouter un enregistrement
python3 /opt/dns-automation/dns_manager.py add server1 A 192.168.1.30

# Lister les enregistrements
python3 /opt/dns-automation/dns_manager.py list

# Supprimer un enregistrement
python3 /opt/dns-automation/dns_manager.py remove server1 A
```

### 6.2 Test via n8n (curl)

```bash
# Ajouter un enregistrement
curl -X POST http://localhost:5678/webhook/dns \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add",
    "hostname": "server1",
    "type": "A",
    "value": "192.168.1.30",
    "ttl": 3600
  }'

# Supprimer un enregistrement
curl -X POST http://localhost:5678/webhook/dns-remove \
  -H "Content-Type: application/json" \
  -d '{
    "action": "remove",
    "hostname": "server1",
    "type": "A"
  }'

# Lister les enregistrements
curl -X GET http://localhost:5678/webhook/dns-list
```

### 6.3 Vérifier les modifications DNS

```bash
# Vérifier avec dig
dig @localhost server1.internal.local

# Vérifier avec nslookup
nslookup server1.internal.local localhost
```

## 7. Sécurité

### 7.1 Configuration du pare-feu

```bash
# Autoriser les ports nécessaires
sudo ufw allow 53/tcp
sudo ufw allow 53/udp
sudo ufw allow 5678/tcp  # n8n
sudo ufw enable
```

### 7.2 Authentification n8n

Modifier les variables d'environnement dans `/etc/systemd/system/n8n.service` :
- `N8N_BASIC_AUTH_USER` : votre nom d'utilisateur
- `N8N_BASIC_AUTH_PASSWORD` : votre mot de passe fort

### 7.3 Limiter l'accès aux webhooks

Considérer l'ajout d'une authentification API ou d'un reverse proxy avec authentification.

## 8. Dépannage

### Problèmes courants

1. **Permission denied** : Vérifier les permissions sudoers
2. **Zone validation failed** : Vérifier la syntaxe avec `named-checkzone`
3. **Bind9 ne se recharge pas** : Vérifier les logs avec `sudo journalctl -u bind9`
4. **n8n ne peut pas exécuter les scripts** : Vérifier les permissions et le PATH

### Logs utiles

```bash
# Logs Bind9
sudo journalctl -u bind9 -f

# Logs n8n
sudo journalctl -u n8n -f

# Logs système
sudo tail -f /var/log/syslog
```

## 9. Sauvegarde

Les sauvegardes automatiques sont créées dans `/var/backups/dns/` à chaque modification.

Pour une sauvegarde manuelle :

```bash
sudo cp /etc/bind/zones/db.internal.local /var/backups/dns/manual_backup_$(date +%Y%m%d_%H%M%S)
```


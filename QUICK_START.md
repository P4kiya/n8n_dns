# Guide de Démarrage Rapide

## Installation Express (5 minutes)

### 0. Résoudre les problèmes DNS (si nécessaire)

Si vous obtenez des erreurs "Temporary failure resolving", configurez d'abord un serveur DNS :

```bash
# Configurer Google DNS
sudo nano /etc/resolv.conf
```

Ajoutez :
```
nameserver 8.8.8.8
nameserver 8.8.4.4
```

Puis testez :
```bash
ping -c 3 8.8.8.8
nslookup google.com
```

**Note :** Si `/etc/resolv.conf` est réinitialisé, voir [TROUBLESHOOTING.md](TROUBLESHOOTING.md) pour une solution permanente.

### 1. Sur votre machine Ubuntu VMware

```bash
# Installer Bind9
sudo apt update
sudo apt install -y bind9 bind9utils

# Créer la structure
sudo mkdir -p /etc/bind/zones /opt/dns-automation /var/backups/dns
sudo chown $USER:$USER /opt/dns-automation /var/backups/dns
```

### 2. Copier les fichiers

**Trouver l'adresse IP de votre machine Ubuntu :**
```bash
# Sur Ubuntu, exécutez :
ip addr show
# ou
hostname -I
```

**Depuis votre machine Windows (PowerShell), copiez les fichiers :**
```powershell
# Remplacez 192.168.x.x par l'IP de votre VM Ubuntu
# Remplacez 'grp' par votre nom d'utilisateur si différent
scp dns_manager.py dns_manager.sh grp@192.168.120.138:/opt/dns-automation/
```

**Alternative : Copier manuellement**
Si SCP ne fonctionne pas, créez les fichiers directement sur Ubuntu avec `nano` et copiez-collez le contenu depuis Windows.

### 3. Configuration Bind9

```bash
# Créer le fichier de zone
sudo nano /etc/bind/zones/db.internal.local
```

Copiez le contenu de `zone_before.txt`

```bash
# Configurer named.conf.local
sudo nano /etc/bind/named.conf.local
```

Ajoutez :
```
zone "internal.local" {
    type master;
    file "/etc/bind/zones/db.internal.local";
};
```

```bash
# Valider et démarrer
sudo named-checkzone internal.local /etc/bind/zones/db.internal.local
sudo systemctl restart bind9
```

### 4. Configurer les scripts

```bash
# Permissions
sudo chmod +x /opt/dns-automation/dns_manager.py
sudo chmod +x /opt/dns-automation/dns_manager.sh

# Configurer sudoers (remplacer 'ubuntu' par votre utilisateur)
sudo visudo
```

Ajoutez :
```
ubuntu ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload bind9
ubuntu ALL=(ALL) NOPASSWD: /usr/bin/named-checkzone
ubuntu ALL=(ALL) NOPASSWD: /bin/cp /tmp/db.internal.local.tmp /etc/bind/zones/db.internal.local
ubuntu ALL=(ALL) NOPASSWD: /usr/bin/chown bind:bind /etc/bind/zones/db.internal.local
ubuntu ALL=(ALL) NOPASSWD: /usr/bin/chmod 644 /etc/bind/zones/db.internal.local
```

### 5. Installer n8n

```bash
# Option 1: npm
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install n8n -g

# Option 2: Docker
sudo apt install -y docker.io
sudo docker run -d --name n8n -p 5678:5678 n8nio/n8n
```

### 6. Importer le workflow n8n

1. Accéder à `http://votre-serveur:5678`
2. Workflows → Import from File
3. Sélectionner `n8n_workflow_dns_automation.json`
4. Activer le workflow

## Test rapide

```bash
# Test direct
python3 /opt/dns-automation/dns_manager.py add test A 192.168.1.100
python3 /opt/dns-automation/dns_manager.py list
python3 /opt/dns-automation/dns_manager.py remove test A

# Test via n8n
curl -X POST http://localhost:5678/webhook/dns \
  -H "Content-Type: application/json" \
  -d '{"action":"add","hostname":"test","type":"A","value":"192.168.1.100"}'
```

## Commandes utiles

```bash
# Vérifier Bind9
sudo systemctl status bind9
sudo named-checkzone internal.local /etc/bind/zones/db.internal.local

# Tester DNS
dig @localhost test.internal.local
nslookup test.internal.local localhost

# Voir les logs
sudo journalctl -u bind9 -f
```

## Structure des fichiers

```
/etc/bind/zones/db.internal.local    # Fichier de zone DNS
/opt/dns-automation/                 # Scripts d'automatisation
/var/backups/dns/                    # Sauvegardes automatiques
```

## Problèmes courants

**Permission denied** → Vérifier sudoers
**Zone validation failed** → Vérifier la syntaxe avec named-checkzone
**n8n ne répond pas** → Vérifier que n8n est démarré

Pour plus de détails, voir [SETUP.md](SETUP.md)


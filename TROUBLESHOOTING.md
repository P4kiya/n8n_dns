# Guide de Dépannage

## Problème : Échec de résolution DNS lors de l'installation

### Symptômes
```
Temporary failure resolving 'ma.archive.ubuntu.com'
Temporary failure resolving 'security.ubuntu.com'
```

### Solution : Configurer un serveur DNS temporaire

#### Étape 1 : Vérifier la configuration DNS actuelle

```bash
cat /etc/resolv.conf
```

#### Étape 2 : Configurer un serveur DNS public

**Option A : Utiliser Google DNS (8.8.8.8)**

```bash
# Éditer le fichier resolv.conf
sudo nano /etc/resolv.conf
```

Remplacer ou ajouter :
```
nameserver 8.8.8.8
nameserver 8.8.4.4
```

**Option B : Utiliser Cloudflare DNS (1.1.1.1)**

```bash
sudo nano /etc/resolv.conf
```

Ajouter :
```
nameserver 1.1.1.1
nameserver 1.0.0.1
```

#### Étape 3 : Vérifier la résolution DNS

```bash
# Tester la résolution
ping -c 3 8.8.8.8
nslookup google.com
dig google.com
```

#### Étape 4 : Réessayer l'installation

```bash
sudo apt update
sudo apt install -y bind9 bind9utils
```

### Solution Permanente : Configurer via Netplan (Ubuntu 18.04+)

Si `/etc/resolv.conf` est régénéré automatiquement, configurez via Netplan :

```bash
# Trouver le fichier de configuration réseau
ls /etc/netplan/

# Éditer le fichier (ex: 01-netcfg.yaml)
sudo nano /etc/netplan/01-netcfg.yaml
```

Ajouter la section `nameservers` :
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:  # ou votre interface réseau
      dhcp4: true
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

Appliquer la configuration :
```bash
sudo netplan apply
```

### Solution Alternative : Configuration via systemd-resolved

```bash
# Éditer la configuration
sudo nano /etc/systemd/resolved.conf
```

Décommenter et modifier :
```
[Resolve]
DNS=8.8.8.8 8.8.4.4
FallbackDNS=1.1.1.1 1.0.0.1
```

Redémarrer le service :
```bash
sudo systemctl restart systemd-resolved
```

## Autres Problèmes Courants

### Problème : Permission denied lors de l'exécution des scripts

**Solution :**
```bash
# Vérifier les permissions
ls -l /opt/dns-automation/dns_manager.py

# Donner les permissions d'exécution
sudo chmod +x /opt/dns-automation/dns_manager.py

# Vérifier la configuration sudoers
sudo visudo -f /etc/sudoers.d/dns-automation
```

### Problème : Zone validation failed

**Solution :**
```bash
# Vérifier la syntaxe de la zone
sudo named-checkzone internal.local /etc/bind/zones/db.internal.local

# Vérifier la configuration globale
sudo named-checkconf

# Voir les erreurs détaillées
sudo named-checkzone -v internal.local /etc/bind/zones/db.internal.local
```

### Problème : Bind9 ne se recharge pas

**Solution :**
```bash
# Vérifier le statut
sudo systemctl status bind9

# Voir les logs
sudo journalctl -u bind9 -n 50

# Redémarrer si nécessaire
sudo systemctl restart bind9
```

### Problème : n8n ne peut pas exécuter les scripts

**Solution :**
```bash
# Vérifier que n8n peut accéder au script
sudo -u n8n-user python3 /opt/dns-automation/dns_manager.py list

# Vérifier le PATH dans n8n
# Dans l'interface n8n, utiliser le chemin complet : /usr/bin/python3

# Vérifier les permissions
sudo chmod 755 /opt/dns-automation/dns_manager.py
```

### Problème : Connexion réseau VMware

**Solution :**
1. Vérifier que la VM est en mode NAT ou Bridge
2. Vérifier que l'interface réseau est activée :
   ```bash
   ip addr show
   sudo ip link set eth0 up  # si nécessaire
   ```
3. Vérifier la passerelle :
   ```bash
   ip route
   ping 8.8.8.8
   ```

### Problème : Fichier resolv.conf réinitialisé

**Solution :** Utiliser Netplan ou systemd-resolved (voir ci-dessus)

### Problème : Connection refused sur le port 22 (SSH)

**Symptômes :**
```
ssh: connect to host 192.168.x.x port 22: Connection refused
```

**Solution : Installer et démarrer SSH**

```bash
# Vérifier si SSH est installé
sudo systemctl status ssh

# Installer OpenSSH Server
sudo apt update
sudo apt install -y openssh-server

# Démarrer le service SSH
sudo systemctl start ssh
sudo systemctl enable ssh

# Vérifier que SSH écoute sur le port 22
sudo systemctl status ssh
sudo ss -tlnp | grep :22
```

**Vérifier le pare-feu :**
```bash
# Si UFW est actif, autoriser SSH
sudo ufw allow ssh
sudo ufw allow 22/tcp
sudo ufw status
```

**Tester depuis Ubuntu :**
```bash
ssh localhost
```

## Commandes de Diagnostic

```bash
# Vérifier la connectivité réseau
ping -c 3 8.8.8.8

# Vérifier la résolution DNS
nslookup google.com
dig google.com @8.8.8.8

# Vérifier la configuration réseau
ip addr
ip route
cat /etc/resolv.conf

# Vérifier les services
sudo systemctl status bind9
sudo systemctl status ssh
sudo systemctl status systemd-resolved
sudo systemctl status networking

# Voir les logs
sudo journalctl -u bind9 -f
sudo journalctl -u ssh -f
sudo dmesg | grep -i network
```


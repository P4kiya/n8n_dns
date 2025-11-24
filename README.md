# Automatisation de la Gestion DNS Interne avec n8n

Ce projet permet d'automatiser la gestion des entrées DNS internes via n8n, en utilisant Bind9 comme serveur DNS sur Ubuntu/Debian.

## 📋 Vue d'ensemble

Le projet comprend :
- **Scripts d'automatisation** (Python et Bash) pour ajouter/supprimer des enregistrements DNS
- **Workflow n8n** pour l'intégration via webhooks HTTP
- **Documentation complète** pour l'installation et la configuration
- **Exemples de fichiers de zone** (avant/après)

## 🎯 Objectifs

- ✅ Gérer dynamiquement les entrées DNS internes
- ✅ Automatiser les ajouts/suppressions via n8n
- ✅ Valider automatiquement les modifications DNS
- ✅ Créer des sauvegardes avant chaque modification

## 📁 Structure du projet

```
n8n_dns/
├── dns_manager.py              # Script Python principal
├── dns_manager.sh              # Script Bash alternatif
├── n8n_workflow_dns_automation.json  # Workflow n8n exporté
├── zone_before.txt             # Exemple de zone avant modification
├── zone_after.txt              # Exemple de zone après modification
├── SETUP.md                    # Guide d'installation détaillé
└── README.md                   # Ce fichier
```

## 🚀 Démarrage rapide

### 1. Prérequis

- Ubuntu Server (20.04+) sur VMware
- Accès sudo/root
- Connexion réseau configurée

### 2. Installation

Suivez le guide complet dans [SETUP.md](SETUP.md) pour :
- Installer Bind9
- Configurer la zone DNS
- Installer n8n
- Configurer les scripts d'automatisation
- Importer le workflow n8n

### 3. Utilisation

#### Via n8n Webhooks

**Ajouter un enregistrement :**
```bash
curl -X POST http://votre-serveur:5678/webhook/dns \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add",
    "hostname": "server1",
    "type": "A",
    "value": "192.168.1.30",
    "ttl": 3600
  }'
```

**Supprimer un enregistrement :**
```bash
curl -X POST http://votre-serveur:5678/webhook/dns-remove \
  -H "Content-Type: application/json" \
  -d '{
    "action": "remove",
    "hostname": "server1",
    "type": "A"
  }'
```

**Lister les enregistrements :**
```bash
curl -X GET http://votre-serveur:5678/webhook/dns-list
```

#### Via ligne de commande

```bash
# Ajouter
python3 /opt/dns-automation/dns_manager.py add server1 A 192.168.1.30

# Supprimer
python3 /opt/dns-automation/dns_manager.py remove server1 A

# Lister
python3 /opt/dns-automation/dns_manager.py list
```

## 🔧 Fonctionnalités

### Types d'enregistrements supportés

- **A** : Adresses IPv4
- **AAAA** : Adresses IPv6
- **CNAME** : Alias
- **MX** : Serveurs de messagerie
- **TXT** : Textes (SPF, DKIM, etc.)

### Sécurité

- ✅ Validation automatique avec `named-checkzone`
- ✅ Sauvegardes automatiques avant chaque modification
- ✅ Incrémentation automatique du numéro de série
- ✅ Gestion des erreurs complète

### Intégration n8n

Le workflow n8n fourni inclut :
- Webhook pour ajouter des enregistrements
- Webhook pour supprimer des enregistrements
- Webhook pour lister les enregistrements
- Parsing JSON automatique
- Réponses HTTP structurées

## 📝 Livrables

- ✅ **Script d'automatisation** : `dns_manager.py` et `dns_manager.sh`
- ✅ **Workflow n8n exporté** : `n8n_workflow_dns_automation.json`
- ✅ **Fichiers zone avant/après** : `zone_before.txt` et `zone_after.txt`

## 🔍 Tests

### Test de validation DNS

```bash
# Vérifier la syntaxe de la zone
sudo named-checkzone internal.local /etc/bind/zones/db.internal.local

# Tester la résolution
dig @localhost server1.internal.local
nslookup server1.internal.local localhost
```

### Test des scripts

```bash
# Test d'ajout
python3 dns_manager.py add test A 192.168.1.100

# Test de liste
python3 dns_manager.py list

# Test de suppression
python3 dns_manager.py remove test A
```

## 📚 Documentation

- [SETUP.md](SETUP.md) : Guide d'installation et configuration complet
- [zone_before.txt](zone_before.txt) : Exemple de zone DNS initiale
- [zone_after.txt](zone_after.txt) : Exemple de zone DNS après modifications

## 🛠️ Dépannage

### Problèmes courants

1. **Permission denied**
   - Vérifier la configuration sudoers
   - Vérifier les permissions des fichiers

2. **Zone validation failed**
   - Vérifier la syntaxe avec `named-checkzone`
   - Consulter les logs Bind9 : `sudo journalctl -u bind9`

3. **n8n ne peut pas exécuter les scripts**
   - Vérifier le PATH dans n8n
   - Vérifier les permissions d'exécution

### Logs utiles

```bash
# Logs Bind9
sudo journalctl -u bind9 -f

# Logs n8n
sudo journalctl -u n8n -f
```

## 🔐 Sécurité

- Utiliser l'authentification n8n (BASIC_AUTH)
- Configurer un pare-feu (UFW)
- Limiter l'accès aux webhooks
- Utiliser HTTPS avec un reverse proxy (recommandé en production)

## 📄 Licence

Ce projet est fourni à des fins éducatives dans le cadre d'un mini-projet d'administration des services réseaux.

## 👤 Auteur

Projet réalisé dans le cadre du cours "Administration des Services Réseaux"

## 📞 Support

Pour toute question ou problème, consulter la section Dépannage dans [SETUP.md](SETUP.md).

#!/bin/bash
#
# Script de test pour l'automatisation DNS
# Teste les fonctionnalités d'ajout, liste et suppression
#

SCRIPT_PATH="/opt/dns-automation/dns_manager.py"
TEST_HOSTNAME="test-$(date +%s)"
TEST_IP="192.168.1.99"

echo "=========================================="
echo "Test d'automatisation DNS"
echo "=========================================="
echo ""

# Test 1: Ajouter un enregistrement
echo "Test 1: Ajout d'un enregistrement A"
echo "-----------------------------------"
python3 "$SCRIPT_PATH" add "$TEST_HOSTNAME" A "$TEST_IP"
if [ $? -eq 0 ]; then
    echo "✓ Ajout réussi"
else
    echo "✗ Échec de l'ajout"
    exit 1
fi
echo ""

# Attendre un peu pour la propagation
sleep 2

# Test 2: Lister les enregistrements
echo "Test 2: Liste des enregistrements"
echo "-----------------------------------"
python3 "$SCRIPT_PATH" list
if [ $? -eq 0 ]; then
    echo "✓ Liste réussie"
else
    echo "✗ Échec de la liste"
fi
echo ""

# Test 3: Vérifier avec dig
echo "Test 3: Vérification DNS avec dig"
echo "-----------------------------------"
dig_result=$(dig @localhost "$TEST_HOSTNAME.internal.local" +short)
if [ "$dig_result" = "$TEST_IP" ]; then
    echo "✓ Résolution DNS correcte: $dig_result"
else
    echo "✗ Résolution DNS échouée (attendu: $TEST_IP, obtenu: $dig_result)"
fi
echo ""

# Test 4: Supprimer l'enregistrement
echo "Test 4: Suppression de l'enregistrement"
echo "-----------------------------------"
python3 "$SCRIPT_PATH" remove "$TEST_HOSTNAME" A
if [ $? -eq 0 ]; then
    echo "✓ Suppression réussie"
else
    echo "✗ Échec de la suppression"
    exit 1
fi
echo ""

# Test 5: Vérifier que l'enregistrement est supprimé
echo "Test 5: Vérification de la suppression"
echo "-----------------------------------"
sleep 2
dig_result=$(dig @localhost "$TEST_HOSTNAME.internal.local" +short)
if [ -z "$dig_result" ] || [ "$dig_result" = "NXDOMAIN" ]; then
    echo "✓ Enregistrement supprimé correctement"
else
    echo "✗ L'enregistrement existe toujours: $dig_result"
fi
echo ""

echo "=========================================="
echo "Tous les tests sont terminés"
echo "=========================================="


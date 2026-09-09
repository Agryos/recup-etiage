# run_test_commands.py

Script de test qui exécute les commandes de `commande_test.txt` et vérifie qu'elles s'exécutent sans erreur et que les fichiers générés ne sont pas vides.

## Principe

1. **Parse** `commande_test.txt` : ignore les commentaires et lignes vides, remplace les placeholders `[DEBUT MOIS ACTUEL]` / `[FIN MOIS ACTUEL]` par les dates du mois courant, utilise le python du venv.
2. **Exécute** chaque commande avec un timeout adapté : 3h pour VCN3 (téléchargement historique long), 10 min pour le reste.
3. **Snapshot** des fichiers dans `output/` avant et après chaque commande pour détecter les fichiers créés ou modifiés.
4. **Vérifie** que les fichiers générés ne sont pas vides (taille = 0).
5. **Catégorise** les fichiers : sortie finale (`QGIS/`, `VCN3/`, `onde/`) vs intermédiaire (téléchargements, index, logs).
6. **Rapport** : affichage en temps réel + rapport final sauvegardé dans `output/test_report.txt`.

## Usage

```bash
# Tout tester sauf VCN3 (rapide, ~10-30 min)
python scripts/run_test_commands.py --filter "^(?!.*vcn3).*$"

# Tester uniquement VCN3 (long, ~2-3h au premier run)
python scripts/run_test_commands.py --filter "vcn3"

# Tout exécuter (VCN3 inclus, peut prendre plusieurs heures)
python scripts/run_test_commands.py

# Seulement les commandes meteo (rapide)
python scripts/run_test_commands.py --filter "meteo" --timeout 300

# Voir les commandes sans les exécuter
python scripts/run_test_commands.py --dry-run
```

## Options

| Option | Défaut | Description |
|---|---|---|
| `--timeout N` | 600 | Timeout (secondes) pour les commandes non-VCN3 |
| `--vcn3-timeout N` | 10800 | Timeout (secondes) pour les commandes VCN3 (3h) |
| `--filter REGEX` | (aucun) | N'exécuter que les commandes matchant le regex |
| `--dry-run` | (off) | Afficher les commandes sans les exécuter |
| `--output FILE` | `output/test_report.txt` | Fichier de rapport |
| `--webhook URL` | (voir code) | URL du webhook Discord |
| `--no-notify` | (off) | Désactiver les notifications Discord |

## Code de sortie

- `0` : toutes les commandes ont réussi
- `1` : au moins une commande a échoué ou dépassé le timeout

## Notifications Discord

Le script envoie une notification Discord via webhook quand une commande échoue ou dépasse le timeout :

- **Notification immédiate** par commande en échec/timeout : type d'erreur, commande, dernières lignes d'erreur.
- **Résumé final** si au moins une commande a échoué : nombre de OK/échecs/timeouts.

Le webhook est configurable (par ordre de priorité) :

1. `--webhook URL` en argument CLI
2. Variable d'environnement `DISCORD_WEBHOOK_URL`
3. Variable `DISCORD_WEBHOOK_URL` dans le fichier `.env`

Le fichier `.env` (ignoré par git) doit contenir :

```
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/VOTRE_WEBHOOK"
```

Pour désactiver les notifications : `--no-notify`.

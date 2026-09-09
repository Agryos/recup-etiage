#!/usr/bin/env python3
"""
Script de test : exécute les commandes de commande_test.txt et vérifie
qu'elles s'exécutent sans erreur et que les fichiers générés ne sont pas vides.

Usage:
    python scripts/run_test_commands.py [OPTIONS]

Options:
    --timeout N        Timeout (secondes) pour les commandes non-VCN3 (défaut: 600)
    --vcn3-timeout N   Timeout (secondes) pour les commandes VCN3 (défaut: 10800)
    --filter REGEX     N'exécuter que les commandes matchant le regex
    --dry-run          Afficher les commandes sans les exécuter
    --output FILE      Fichier de rapport (défaut: output/test_report.txt)
"""
import argparse
import calendar
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMMAND_FILE = PROJECT_ROOT / "commande_test.txt"
OUTPUT_DIR = PROJECT_ROOT / "output"
VENV_PYTHON = PROJECT_ROOT / "venv" / "bin" / "python"

# Charger les variables d'environnement depuis .env
load_dotenv(PROJECT_ROOT / ".env")

# Dossiers de sortie finale (vs données intermédiaires)
FINAL_OUTPUT_DIRS = {"QGIS", "VCN3", "onde"}

# Patterns à ignorer dans le snapshot
IGNORE_PATTERNS = {"__pycache__", ".pytest_cache"}

# Webhook Discord (depuis .env, --webhook, ou DISCORD_WEBHOOK_URL)
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


# ----------------------------------------------------------------------------
# Notifications Discord
# ----------------------------------------------------------------------------
def send_discord_notification(message, webhook_url=None):
    """Envoie une notification sur Discord via webhook. Échoue silencieusement."""
    url = webhook_url or DISCORD_WEBHOOK_URL
    if not url:
        return
    # Discord limite les messages à 2000 caractères
    if len(message) > 1900:
        message = message[:1897] + "..."
    payload = json.dumps({"content": message}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "recup-etiage/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 204:
                print(f"  [Discord] Reponse inattendue: {resp.status}")
    except Exception as e:
        print(f"  [Discord] Echec de l'envoi: {e}")


# ----------------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------------
def get_current_month_dates():
    """Renvoie (premier_jour, dernier_jour) du mois actuel au format YYYY-MM-DD."""
    now = datetime.now()
    first_day = now.replace(day=1)
    _, last_day_num = calendar.monthrange(now.year, now.month)
    last_day = now.replace(day=last_day_num)
    return first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")


def parse_commands(filepath):
    """Parse le fichier de commandes, remplace les placeholders, ignore commentaires."""
    debut, fin = get_current_month_dates()
    commands = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            line = line.replace("[DEBUT MOIS ACTUEL]", debut)
            line = line.replace("[FIN MOIS ACTUEL]", fin)
            # Remplace python par le python du venv
            line = line.replace("python main.py", f'"{VENV_PYTHON}" main.py')
            commands.append(line)
    return commands


def is_vcn3_command(cmd):
    """Détecte si une commande est une commande VCN3."""
    return "--type vcn3" in cmd


def get_timeout(cmd, default_timeout, vcn3_timeout):
    """Renvoie le timeout approprié selon le type de commande."""
    return vcn3_timeout if is_vcn3_command(cmd) else default_timeout


# ----------------------------------------------------------------------------
# Snapshot des fichiers
# ----------------------------------------------------------------------------
def snapshot_files(directory):
    """Prend un snapshot des fichiers dans directory. Renvoie {path: (mtime, size)}."""
    snapshot = {}
    if not directory.exists():
        return snapshot
    for root, dirs, files in os.walk(directory):
        # Filtrer les dossiers à ignorer
        dirs[:] = [d for d in dirs if d not in IGNORE_PATTERNS]
        for f in files:
            path = Path(root) / f
            try:
                stat = path.stat()
                snapshot[str(path)] = (stat.st_mtime, stat.st_size)
            except OSError:
                pass
    return snapshot


def diff_snapshots(before, after):
    """Compare deux snapshots. Renvoie liste de (path, size, statut)."""
    changes = []
    for path, (mtime, size) in after.items():
        if path not in before:
            changes.append((path, size, "nouveau"))
        elif after[path][0] > before[path][0]:
            changes.append((path, size, "modifie"))
    return changes


def categorize_file(path_str):
    """Catégorise un fichier : 'final' (sortie finale) ou 'intermediaire'."""
    try:
        rel = Path(path_str).relative_to(OUTPUT_DIR)
        if rel.parts and rel.parts[0] in FINAL_OUTPUT_DIRS:
            return "final"
    except ValueError:
        pass
    return "intermediaire"


# ----------------------------------------------------------------------------
# Exécution
# ----------------------------------------------------------------------------
def run_command(cmd, timeout):
    """Exécute une commande. Renvoie (exit_code, stdout, stderr, timed_out, elapsed)."""
    t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
        )
        elapsed = time.time() - t0
        return result.returncode, result.stdout, result.stderr, False, elapsed
    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - t0
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return -1, stdout, stderr, True, elapsed


# ----------------------------------------------------------------------------
# Rapport
# ----------------------------------------------------------------------------
def format_size(size):
    """Formate une taille en bytes de manière lisible."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


def run_all(commands, default_timeout, vcn3_timeout, dry_run, report_path, webhook_url=None):
    """Exécute toutes les commandes et génère le rapport."""
    results = []
    total = len(commands)

    print(f"\n{'=' * 70}")
    print(f"  TEST DE COMMANDES - {total} commande(s) a executer")
    print(f"  Timeout non-VCN3 : {default_timeout}s | Timeout VCN3 : {vcn3_timeout}s")
    print(f"{'=' * 70}\n")

    for i, cmd in enumerate(commands, 1):
        timeout = get_timeout(cmd, default_timeout, vcn3_timeout)
        cmd_type = "VCN3" if is_vcn3_command(cmd) else "STD"

        print(f"[{i}/{total}] ({cmd_type}, timeout={timeout}s)")
        print(f"  CMD: {cmd}")

        if dry_run:
            print(f"  -> DRY RUN (skip)\n")
            results.append({
                "cmd": cmd,
                "exit_code": 0,
                "timed_out": False,
                "elapsed": 0,
                "files": [],
                "stderr": "",
            })
            continue

        # Snapshot avant
        before = snapshot_files(OUTPUT_DIR)

        # Exécution
        exit_code, stdout, stderr, timed_out, elapsed = run_command(cmd, timeout)

        # Snapshot après
        after = snapshot_files(OUTPUT_DIR)
        files = diff_snapshots(before, after)

        # Résultat
        results.append({
            "cmd": cmd,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "elapsed": elapsed,
            "files": files,
            "stderr": stderr,
        })

        # Affichage immédiat
        if timed_out:
            print(f"  -> TIMEOUT ({elapsed:.0f}s)")
            # Notification Discord
            msg = f"**[TIMEOUT]** Commande {i}/{total} ({elapsed:.0f}s)\n```\n{cmd}\n```"
            send_discord_notification(msg, webhook_url)
        elif exit_code != 0:
            print(f"  -> ECHEC (exit={exit_code}, {elapsed:.0f}s)")
            # Afficher les dernières lignes de stderr
            stderr_lines = stderr.strip().split("\n")
            for line in stderr_lines[-5:]:
                print(f"     {line}")
            # Notification Discord
            stderr_tail = "\n".join(stderr_lines[-3:])
            msg = f"**[ECHEC]** Commande {i}/{total} (exit={exit_code}, {elapsed:.0f}s)\n```\n{cmd}\n```\n```\n{stderr_tail}\n```"
            send_discord_notification(msg, webhook_url)
        else:
            n_final = sum(1 for f in files if categorize_file(f[0]) == "final")
            n_inter = sum(1 for f in files if categorize_file(f[0]) == "intermediaire")
            n_empty = sum(1 for f in files if f[1] == 0)
            print(f"  -> OK ({elapsed:.0f}s) | {n_final} final(x), {n_inter} intermediaire(s)"
                  + (f", {n_empty} VIDE(S)" if n_empty else ""))
        print()

    # Rapport final
    print_report(results, report_path, webhook_url)
    return results


def print_report(results, report_path, webhook_url=None):
    """Affiche et sauvegarde le rapport final."""
    lines = []
    lines.append("=" * 70)
    lines.append("  RAPPORT FINAL")
    lines.append("=" * 70)

    n_pass = 0
    n_fail = 0
    n_timeout = 0
    n_empty_files = 0

    for i, r in enumerate(results, 1):
        status = "OK"
        if r["timed_out"]:
            status = "TIMEOUT"
            n_timeout += 1
        elif r["exit_code"] != 0:
            status = f"ECHEC (exit={r['exit_code']})"
            n_fail += 1
        else:
            n_pass += 1

        lines.append(f"\n[{i}] {status} ({r['elapsed']:.0f}s)")
        lines.append(f"    CMD: {r['cmd']}")

        # Fichiers générés
        if r["files"]:
            final_files = [f for f in r["files"] if categorize_file(f[0]) == "final"]
            inter_files = [f for f in r["files"] if categorize_file(f[0]) == "intermediaire"]

            if final_files:
                lines.append(f"    Fichiers de sortie ({len(final_files)}):")
                for path, size, statut in final_files:
                    empty = " [VIDE]" if size == 0 else ""
                    if size == 0:
                        n_empty_files += 1
                    rel = Path(path).relative_to(OUTPUT_DIR)
                    lines.append(f"      {statut}: {rel} ({format_size(size)}){empty}")

            if inter_files:
                lines.append(f"    Fichiers intermediaires ({len(inter_files)}):")
                for path, size, statut in inter_files[:5]:  # Limite à 5
                    empty = " [VIDE]" if size == 0 else ""
                    if size == 0:
                        n_empty_files += 1
                    rel = Path(path).relative_to(OUTPUT_DIR)
                    lines.append(f"      {statut}: {rel} ({format_size(size)}){empty}")
                if len(inter_files) > 5:
                    lines.append(f"      ... et {len(inter_files) - 5} autre(s)")
        else:
            lines.append("    Aucun fichier genere")

        if r["stderr"] and r["exit_code"] != 0:
            stderr_lines = r["stderr"].strip().split("\n")
            lines.append(f"    Erreur (dernieres lignes):")
            for line in stderr_lines[-3:]:
                lines.append(f"      {line}")

    # Résumé
    lines.append("\n" + "=" * 70)
    lines.append(f"  RESUME: {n_pass} OK, {n_fail} echec(s), {n_timeout} timeout(s)")
    if n_empty_files:
        lines.append(f"  ATTENTION: {n_empty_files} fichier(s) vide(s) detecte(s)")
    lines.append("=" * 70)

    report_text = "\n".join(lines)
    print(report_text)

    # Sauvegarde
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\nRapport sauvegarde : {report_path}")

    # Notification Discord : résumé final si des échecs
    if webhook_url and (n_fail > 0 or n_timeout > 0):
        summary = f"**[RAPPORT TEST]** {n_pass} OK, {n_fail} echec(s), {n_timeout} timeout(s)"
        if n_empty_files:
            summary += f"\nAttention: {n_empty_files} fichier(s) vide(s)"
        summary += f"\nRapport: `{report_path}`"
        send_discord_notification(summary, webhook_url)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Execute les commandes de commande_test.txt et verifie les sorties."
    )
    parser.add_argument("--timeout", type=int, default=600,
                        help="Timeout (s) pour les commandes non-VCN3 (defaut: 600)")
    parser.add_argument("--vcn3-timeout", type=int, default=10800,
                        help="Timeout (s) pour les commandes VCN3 (defaut: 10800)")
    parser.add_argument("--filter", type=str, default=None,
                        help="Regex pour filtrer les commandes a executer")
    parser.add_argument("--dry-run", action="store_true",
                        help="Afficher les commandes sans les executer")
    parser.add_argument("--output", type=str, default=None,
                        help="Fichier de rapport (defaut: output/test_report.txt)")
    parser.add_argument("--webhook", type=str, default=None,
                        help="URL du webhook Discord (defaut: DISCORD_WEBHOOK_URL ou valeur codee)")
    parser.add_argument("--no-notify", action="store_true",
                        help="Desactiver les notifications Discord")
    args = parser.parse_args()

    report_path = Path(args.output) if args.output else OUTPUT_DIR / "test_report.txt"

    # Webhook : --no-notify desactive, sinon --webhook ou valeur par defaut
    webhook_url = None
    if not args.no_notify:
        webhook_url = args.webhook if args.webhook else DISCORD_WEBHOOK_URL

    # Parse les commandes
    commands = parse_commands(COMMAND_FILE)

    # Filtre
    if args.filter:
        pattern = re.compile(args.filter)
        commands = [c for c in commands if pattern.search(c)]
        print(f"Filtre '{args.filter}': {len(commands)} commande(s) selectionnee(s)")

    if not commands:
        print("Aucune commande a executer.")
        sys.exit(0)

    # Exécution
    results = run_all(
        commands,
        args.timeout,
        args.vcn3_timeout,
        args.dry_run,
        report_path,
        webhook_url,
    )

    # Code de sortie : 0 si tout OK, 1 sinon
    has_failure = any(r["exit_code"] != 0 or r["timed_out"] for r in results)
    sys.exit(1 if has_failure else 0)


if __name__ == "__main__":
    main()

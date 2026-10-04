#!/usr/bin/env bash
# =============================================================================
# Ce script preprocessed.sh exécute le programme src/preprocessed.py
# et enregistre les détails de son exécution dans le fichier de log
# logs/preprocessed.logs.
# =============================================================================

set -euo pipefail

# On se place à la racine du projet pour n'utiliser que des chemins relatifs,
# quel que soit le répertoire depuis lequel le script est lancé (cron, make...).
cd "$(dirname "$0")/.."

LOG_FILE="logs/preprocessed.logs"
SCRIPT="src/preprocessed.py"

mkdir -p "$(dirname "${LOG_FILE}")"

# On utilise l'environnement virtuel du projet s'il existe (cron ne l'active pas).
PYTHON="python3"
if [[ -x ".venv/bin/python" ]]; then
    PYTHON=".venv/bin/python"
fi

# Écrit un message horodaté dans le fichier de log et sur la sortie standard.
log() {
    local level="$1"
    shift
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ${level} - $*" | tee -a "${LOG_FILE}"
}

log INFO "=== Lancement de ${SCRIPT} ==="

# Les étapes sont loguées par le programme Python ; les erreurs non gérées
# (sortie d'erreur) sont également redirigées vers le fichier de log.
if "${PYTHON}" "${SCRIPT}" 2>> "${LOG_FILE}"; then
    log INFO "=== Prétraitement terminé avec succès ==="
else
    log ERROR "=== Échec du prétraitement (voir ${LOG_FILE}) ==="
    exit 1
fi

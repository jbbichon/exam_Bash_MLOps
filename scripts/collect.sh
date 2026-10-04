#!/usr/bin/env bash
# ==============================================================================
# Script : collect.sh
# Description :
#   Ce script interroge une API afin de récupérer les ventes des modèles de cartes graphiques suivants :
#     - rtx3060
#     - rtx3070
#     - rtx3080
#     - rtx3090
#     - rx6700
#
#   Les données collectées sont ajoutées à une copie du fichier :
#     data/raw/sales_data.csv
#
#   Le fichier de sortie est sauvegardé au format :
#     data/raw/sales_YYYYMMDD_HHMM.csv
#   avec les colonnes suivantes :
#     timestamp, model, sales
#
#   L’activité de collecte (requêtes, modèles interrogés, résultats, erreurs)
#   est enregistrée dans un fichier de log :
#     logs/collect.logs
#
#   Le log est lisible et doit inclure :
#     - La date et l’heure de chaque requête
#     - Les modèles interrogés
#     - Les ventes récupérées
#     - Les éventuelles erreurs
# ==============================================================================

set -euo pipefail

# On se place à la racine du projet pour n'utiliser que des chemins relatifs,
# quel que soit le répertoire depuis lequel le script est lancé (cron, make...).
cd "$(dirname "$0")/.."

# L'URL de l'API peut être surchargée par la variable d'environnement API_URL.
API_URL="${API_URL:-http://0.0.0.0:5000}"
MODELS="rtx3060 rtx3070 rtx3080 rtx3090 rx6700"

RAW_DIR="data/raw"
SOURCE_FILE="${RAW_DIR}/sales_data.csv"
OUTPUT_FILE="${RAW_DIR}/sales_$(date +%Y%m%d_%H%M).csv"
LOG_FILE="logs/collect.logs"

mkdir -p "${RAW_DIR}" "$(dirname "${LOG_FILE}")"

# Écrit un message horodaté dans le fichier de log et sur la sortie standard.
log() {
    local level="$1"
    shift
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ${level} - $*" | tee -a "${LOG_FILE}"
}

log INFO "=== Début de la collecte (API : ${API_URL}) ==="

# Le fichier de référence doit exister pour pouvoir en faire une copie.
if [[ ! -f "${SOURCE_FILE}" ]]; then
    log ERROR "Fichier source introuvable : ${SOURCE_FILE}"
    exit 1
fi

# La collecte repart du dernier fichier horodaté pour conserver l'historique
# des collectes précédentes ; à défaut, du fichier de référence.
base_file="$(find "${RAW_DIR}" -name 'sales_[0-9]*_[0-9]*.csv' | sort | tail -n 1)"
base_file="${base_file:-${SOURCE_FILE}}"

# Interrogation de l'API pour chaque modèle.
new_rows=""
errors=0
for model in ${MODELS}; do
    timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    log INFO "Requête : GET ${API_URL}/${model}"

    if ! sales="$(curl --silent --fail --max-time 10 "${API_URL}/${model}")"; then
        log ERROR "Modèle ${model} : échec de la requête vers l'API"
        errors=$((errors + 1))
        continue
    fi

    # La réponse attendue est un entier positif.
    sales="$(echo "${sales}" | tr -d '[:space:]')"
    if [[ ! "${sales}" =~ ^[0-9]+$ ]]; then
        log ERROR "Modèle ${model} : réponse invalide '${sales}'"
        errors=$((errors + 1))
        continue
    fi

    log INFO "Modèle ${model} : ${sales} ventes récupérées"
    new_rows+="${timestamp},${model},${sales}"$'\n'
done

if [[ -z "${new_rows}" ]]; then
    log ERROR "Aucune donnée collectée (${errors} erreur(s)) : aucun fichier créé"
    exit 1
fi

# Copie du fichier de base (sauf si le fichier de la minute courante existe déjà).
if [[ "${base_file}" != "${OUTPUT_FILE}" ]]; then
    cp "${base_file}" "${OUTPUT_FILE}"
    log INFO "Copie de ${base_file} vers ${OUTPUT_FILE}"
fi

# On s'assure que le fichier se termine par un saut de ligne avant d'ajouter.
if [[ -n "$(tail -c 1 "${OUTPUT_FILE}")" ]]; then
    echo >> "${OUTPUT_FILE}"
fi
printf '%s' "${new_rows}" >> "${OUTPUT_FILE}"

nb_rows="$(printf '%s' "${new_rows}" | wc -l | tr -d ' ')"
log INFO "${nb_rows} ligne(s) ajoutée(s) dans ${OUTPUT_FILE} (${errors} erreur(s))"
log INFO "=== Fin de la collecte ==="

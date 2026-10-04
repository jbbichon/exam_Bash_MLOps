"""
-------------------------------------------------------------------------------
Ce script preprocessed.py récupère les données du dernier fichier CSV créé
dans le dossier 'data/raw/'.

1. Il applique un prétraitement aux données

2. Les résultats du prétraitement sont enregistrés dans un nouveau fichier CSV
   dans le dossier 'data/processed/', avec un nom au format
   'sales_processed_YYYYMMDD_HHMM.csv'.

3. Toutes les étapes du prétraitement sont enregistrées dans le fichier
   'logs/preprocessed.logs' afin de garantir un suivi détaillé du processus.

Les erreurs ou anomalies éventuelles sont également loguées pour assurer la traçabilité.
-------------------------------------------------------------------------------
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
LOG_FILE = Path("logs/preprocessed.logs")

EXPECTED_COLUMNS = ["timestamp", "model", "sales"]
MODELS = ["rtx3060", "rtx3070", "rtx3080", "rtx3090", "rx6700"]

logger = logging.getLogger("preprocessed")


def setup_logging():
    """Configure l'écriture des logs dans le fichier et sur la sortie standard."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    for handler in (logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def get_latest_raw_file():
    """Retourne le dernier fichier 'sales_*.csv' créé dans data/raw."""
    raw_files = list(RAW_DIR.glob("sales_*.csv"))
    if not raw_files:
        raise FileNotFoundError(f"Aucun fichier 'sales_*.csv' trouvé dans {RAW_DIR}")
    return max(raw_files, key=lambda f: f.stat().st_mtime)


def drop_rows(df, mask, reason):
    """Supprime les lignes désignées par le masque et logue leur nombre."""
    nb_rows = int(mask.sum())
    if nb_rows:
        logger.warning("%d ligne(s) supprimée(s) : %s", nb_rows, reason)
    else:
        logger.info("Aucune ligne supprimée : %s", reason)
    return df[~mask]


def preprocess(df):
    """Nettoie les données brutes et les transforme en variables entières."""
    missing_columns = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Colonnes manquantes : {sorted(missing_columns)}")
    df = df[EXPECTED_COLUMNS].copy()

    # Conversion des types : les valeurs incorrectes deviennent manquantes.
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df["sales"] = pd.to_numeric(df["sales"], errors="coerce")
    df["model"] = df["model"].astype("string").str.strip().str.lower()

    # Suppression des valeurs manquantes ou incorrectes.
    df = drop_rows(df, df.isna().any(axis=1), "valeurs manquantes ou mal formatées")
    df = drop_rows(df, ~df["model"].isin(MODELS), "modèle de carte inconnu")
    df = drop_rows(
        df, (df["sales"] < 0) | (df["sales"] % 1 != 0), "ventes négatives ou non entières"
    )
    df = drop_rows(df, df.duplicated(), "doublons")

    if df.empty:
        raise ValueError("Aucune donnée exploitable après nettoyage")

    # Décomposition de la date en variables entières (la colonne 'timestamp'
    # est supprimée du fichier prétraité).
    processed = pd.DataFrame(
        {
            "year": df["timestamp"].dt.year,
            "month": df["timestamp"].dt.month,
            "day": df["timestamp"].dt.day,
            "day_of_week": df["timestamp"].dt.dayofweek,
            "hour": df["timestamp"].dt.hour,
            "minute": df["timestamp"].dt.minute,
        }
    )
    logger.info("Colonne 'timestamp' décomposée en : %s", list(processed.columns))

    # Encodage one-hot du modèle de carte, avec un jeu de colonnes fixe.
    for model in MODELS:
        processed[f"model_{model}"] = df["model"] == model
    logger.info("Colonne 'model' encodée en %d colonnes binaires", len(MODELS))

    processed["sales"] = df["sales"]
    return processed.astype(int).reset_index(drop=True)


def main():
    setup_logging()
    logger.info("Début du prétraitement")
    try:
        raw_file = get_latest_raw_file()
        df = pd.read_csv(raw_file)
        logger.info(
            "Fichier brut chargé : %s (%d lignes, %d colonnes)", raw_file, *df.shape
        )

        processed = preprocess(df)

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        output_file = (
            PROCESSED_DIR / f"sales_processed_{datetime.now():%Y%m%d_%H%M}.csv"
        )
        processed.to_csv(output_file, index=False)
        logger.info(
            "Fichier prétraité enregistré : %s (%d lignes, %d colonnes)",
            output_file,
            *processed.shape,
        )
    except Exception as error:
        logger.error("Échec du prétraitement : %s", error)
        sys.exit(1)
    logger.info("Fin du prétraitement")


if __name__ == "__main__":
    main()

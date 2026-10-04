"""
-------------------------------------------------------------------------------
Ce script exécute l'entraînement d'un modèle XGBoost pour prédire les ventes de
cartes graphiques à partir des données prétraitées.

1. Il commence par rechercher le dernier fichier CSV prétraité dans le dossier
   'data/processed/'.
2. Si un modèle standard (model.pkl) n'existe pas, il charge les données, les
   divise en ensembles d'entraînement et de test, entraîne un modèle sur ces
   données, l'évalue, puis le sauvegarde dans 'model/model.pkl'.
3. Si un modèle standard existe déjà, il entraîne un nouveau modèle sur les
   données les plus récentes, l'évalue, puis sauvegarde le modèle dans le dossier
   'model/' sous formats : model_YYYYMMDD_HHMM.pkl.
4. Les métriques de performance (RMSE, MAE, R²) sont affichées et sauvegardées dans
   le fichier de log.
5. Des erreurs éventuelles sont gérées et signalées dans les logs.

Les modèles sont sauvegardés dans le dossier 'model/' avec le nom 'model.pkl' pour
le modèle standard et avec un horodatage pour les versions ultérieures.
Les métriques du modèle sont enregistrées dans les logs du script.
-------------------------------------------------------------------------------
"""

import logging
import pickle
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

PROCESSED_DIR = Path("data/processed")
MODEL_DIR = Path("model")
STANDARD_MODEL = MODEL_DIR / "model.pkl"
LOG_FILE = Path("logs/train.logs")

TARGET = "sales"
TEST_SIZE = 0.2
RANDOM_STATE = 42

logger = logging.getLogger("train")


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


def get_latest_processed_file():
    """Retourne le dernier fichier 'sales_processed_*.csv' de data/processed."""
    processed_files = list(PROCESSED_DIR.glob("sales_processed_*.csv"))
    if not processed_files:
        raise FileNotFoundError(
            f"Aucun fichier 'sales_processed_*.csv' trouvé dans {PROCESSED_DIR}"
        )
    return max(processed_files, key=lambda f: f.stat().st_mtime)


def train_and_evaluate(df):
    """Entraîne un modèle XGBoost et retourne le modèle avec ses métriques."""
    if TARGET not in df.columns:
        raise ValueError(f"Colonne cible '{TARGET}' absente des données prétraitées")

    X = df.drop(columns=[TARGET])
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    logger.info(
        "Données divisées : %d lignes d'entraînement, %d lignes de test",
        len(X_train),
        len(X_test),
    )

    model = XGBRegressor(
        n_estimators=100, max_depth=4, learning_rate=0.1, random_state=RANDOM_STATE
    )
    model.fit(X_train, y_train)
    logger.info("Modèle XGBoost entraîné sur %d variables", X_train.shape[1])

    predictions = model.predict(X_test)
    metrics = {
        "RMSE": root_mean_squared_error(y_test, predictions),
        "MAE": mean_absolute_error(y_test, predictions),
        "R²": r2_score(y_test, predictions),
    }
    return model, metrics


def get_model_path():
    """Retourne model.pkl s'il n'existe pas encore, sinon un nom horodaté."""
    if not STANDARD_MODEL.is_file():
        return STANDARD_MODEL
    return MODEL_DIR / f"model_{datetime.now():%Y%m%d_%H%M}.pkl"


def main():
    setup_logging()
    logger.info("Début de l'entraînement")
    try:
        processed_file = get_latest_processed_file()
        df = pd.read_csv(processed_file)
        logger.info(
            "Fichier prétraité chargé : %s (%d lignes, %d colonnes)",
            processed_file,
            *df.shape,
        )

        model, metrics = train_and_evaluate(df)
        logger.info(
            "Métriques : %s",
            ", ".join(f"{name} = {value:.4f}" for name, value in metrics.items()),
        )

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        model_path = get_model_path()
        with open(model_path, "wb") as model_file:
            pickle.dump(model, model_file)
        logger.info("Modèle sauvegardé : %s", model_path)
    except Exception as error:
        logger.error("Échec de l'entraînement : %s", error)
        sys.exit(1)
    logger.info("Fin de l'entraînement")


if __name__ == "__main__":
    main()

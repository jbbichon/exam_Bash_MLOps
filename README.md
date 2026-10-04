# Examen Linux & Bash — Pipeline de prédiction des ventes de cartes graphiques

Pipeline automatisé qui collecte les ventes de cartes graphiques depuis une API,
les prétraite, puis entraîne un modèle de prédiction des ventes.

Les modèles suivis sont : `rtx3060`, `rtx3070`, `rtx3080`, `rtx3090` et `rx6700`.

## Fonctionnement

La commande `make bash` enchaîne trois étapes :

| Étape | Script | Programme appelé | Résultat | Log |
|---|---|---|---|---|
| 1. Collecte | `scripts/collect.sh` | `curl` sur l'API | `data/raw/sales_YYYYMMDD_HHMM.csv` | `logs/collect.logs` |
| 2. Prétraitement | `scripts/preprocessed.sh` | `src/preprocessed.py` | `data/processed/sales_processed_YYYYMMDD_HHMM.csv` | `logs/preprocessed.logs` |
| 3. Entraînement | `scripts/train.sh` | `src/train.py` | `model/model.pkl` ou `model/model_YYYYMMDD_HHMM.pkl` | `logs/train.logs` |

Si une étape échoue, les suivantes ne sont pas lancées et l'erreur est écrite dans le log correspondant.

### 1. Collecte

Le script interroge l'API pour chaque modèle et ajoute une ligne `timestamp,model,sales`
par modèle. La première collecte part d'une copie de `data/raw/sales_data.csv` ;
les suivantes repartent du dernier fichier horodaté, afin de conserver l'historique.
Une réponse qui n'est pas un entier positif est ignorée et signalée dans le log.

### 2. Prétraitement

Le programme charge le dernier fichier de `data/raw/`, puis :

- supprime les valeurs manquantes ou mal formatées, les modèles inconnus,
  les ventes négatives ou non entières et les doublons ;
- décompose la date en colonnes entières (`year`, `month`, `day`, `day_of_week`, `hour`, `minute`) ;
- encode le modèle de carte en cinq colonnes binaires (`model_rtx3060`, etc.).

Le fichier produit ne contient que des entiers et plus de colonne `timestamp`.

### 3. Entraînement

Le programme charge le dernier fichier de `data/processed/`, sépare les données
(80 % entraînement, 20 % test), entraîne un modèle XGBoost et écrit les métriques
RMSE, MAE et R² dans le log. Le premier modèle est enregistré sous `model/model.pkl`,
les suivants sous `model/model_YYYYMMDD_HHMM.pkl`.

## Prérequis

- Linux avec `bash`, `make`, `curl` et `cron`
- Python 3.12
- [uv](https://docs.astral.sh/uv/) pour gérer l'environnement virtuel et les dépendances

## Installation

```bash
# 1. Récupérer et lancer l'API (elle écoute sur le port 5000)
wget --no-cache https://dst-de.s3.eu-west-3.amazonaws.com/bash_fr/api.tar
tar -xvf api.tar
chmod +x api
./api &

# 2. Installer les dépendances dans .venv et activer l'environnement
make install
source .venv/bin/activate
```

Sans `uv`, les dépendances d'exécution peuvent être installées avec
`pip install -r requirements.txt` (ajouter `pytest` pour lancer les tests).

## Utilisation

| Commande | Rôle |
|---|---|
| `make install` | Installe les dépendances (`uv sync`) |
| `make bash` | Lance le pipeline complet : collecte, prétraitement, entraînement |
| `make tests` | Lance les tests et écrit leurs résultats dans `logs/tests_logs/` |
| `make all` | Lance le pipeline puis les tests |

Par défaut, l'API est appelée sur `http://0.0.0.0:5000`. Une autre adresse peut être
fournie avec la variable d'environnement `API_URL` :

```bash
API_URL=http://127.0.0.1:5001 make bash
```

## Automatisation avec cron

Le fichier `scripts/cron.txt` lance `make bash` toutes les 3 minutes et écrit la
sortie dans `logs/cron.logs`.

1. Adapter le chemin absolu du projet dans `scripts/cron.txt`.
2. Installer la tâche : `crontab scripts/cron.txt` (remplace la crontab existante de l'utilisateur).
3. Vérifier : `crontab -l`, puis observer l'arrivée de nouveaux fichiers dans `data/raw/`.
4. Arrêter : `crontab -r`.

## Arborescence

```txt
exam_bash/
├── data/
│   ├── raw/                  # Données brutes (sales_data.csv + collectes horodatées)
│   └── processed/            # Données prétraitées
├── logs/                     # Logs de chaque étape, de cron et des tests
├── model/                    # Modèles entraînés (.pkl)
├── scripts/
│   ├── collect.sh            # Collecte des données via l'API
│   ├── preprocessed.sh       # Lance src/preprocessed.py
│   ├── train.sh              # Lance src/train.py
│   └── cron.txt              # Planification cron
├── src/
│   ├── preprocessed.py       # Prétraitement des données
│   └── train.py              # Entraînement du modèle XGBoost
├── tests/                    # Tests fournis (non modifiés)
├── Makefile                  # Automatisation des tâches
├── requirements.txt          # Dépendances d'exécution
├── pyproject.toml            # Configuration du projet et dépendances (uv)
└── uv.lock                   # Versions verrouillées des dépendances
```

Les dossiers `data/processed/`, `model/` et `logs/tests_logs/` sont créés
automatiquement à la première exécution.

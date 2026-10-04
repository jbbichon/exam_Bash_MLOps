.PHONY: install bash tests all

# Installe les dépendances du projet dans l'environnement virtuel (.venv)
install:
	uv sync

# Pipeline complet : collecte, prétraitement puis entraînement
bash:
	bash scripts/collect.sh
	bash scripts/preprocessed.sh
	bash scripts/train.sh

tests:
	pytest tests/test_collect.py && \
	pytest tests/test_preprocessed.py && \
	pytest tests/test_model.py

all: bash tests

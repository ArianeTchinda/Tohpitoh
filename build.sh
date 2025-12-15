#!/usr/bin/env bash
# Installe les dépendances
pip install -r requirements.txt

# Lance la collecte des statiques
python manage.py collectstatic --noinput

# Lance les migrations de la base de données
python manage.py migrate

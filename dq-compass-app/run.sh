#!/bin/bash

echo "======================================"
echo "DQ Compass - Universal Data Quality"
echo "======================================"
echo ""
echo "Installation des dépendances..."
pip install -r requirements.txt
echo ""
echo "Lancement de l'application..."
echo ""
streamlit run app.py

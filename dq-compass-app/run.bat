@echo off
echo ======================================
echo DQ Compass - Universal Data Quality
echo ======================================
echo.
echo Installation des dependances...
pip install -r requirements.txt
echo.
echo Lancement de l'application...
echo.
streamlit run app.py

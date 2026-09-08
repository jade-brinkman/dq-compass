@echo off
echo ======================================
echo DQ Compass - Universal Data Quality
echo ======================================
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Starting the application...
echo.
streamlit run Home.py

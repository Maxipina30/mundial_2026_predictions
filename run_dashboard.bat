@echo off
cd /d "%~dp0"
echo Starting World Cup dashboard...
echo.
echo Keep this window open while using the dashboard.
echo URL: http://127.0.0.1:8501/
echo.
"C:\Users\maxip\Documents\futdata_v1\.runtime\python312\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
echo.
echo Streamlit stopped. Press any key to close this window.
pause > nul

@echo off 
echo === Bitcoin Solo Miner Monitor === 
echo. 
echo [INFO] Starting Bitcoin Solo Miner Monitor... 
echo [INFO] The app will be available at: http://localhost:8000 
echo. 
echo [INFO] Installing Python dependencies... 
pip install -r requirements.txt 
echo. 
echo [INFO] Starting application... 
python run.py 
pause 

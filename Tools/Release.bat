cd ..

pyinstaller --onefile -w --add-data="arial.ttf;." --icon="sterilabel.ico" SterilabelGUI.py
rem this command may generate a windows virus error
rem see https://stackoverflow.com/questions/77346372/pyinstaller-says-i-made-a-virus

cd Tools

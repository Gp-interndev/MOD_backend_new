bat_content = """
@echo off
cd /d D:\\Monarch_Mod\\backend
python app.py
pause
"""

with open("D:\\Monarch_Mod\\backend\\run_converter.bat", "w") as bat_file:
    bat_file.write(bat_content.strip())

print("Batch file created successfully!")

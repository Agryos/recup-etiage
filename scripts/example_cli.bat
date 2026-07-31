REM Aide
..\venv\Scripts\python.exe ..\main.py --help

REM Hydraulicité
..\venv\Scripts\python.exe ..\main.py --type hydraulicite --start_date 2026-01 --reseau_sandre BSH001

REM VCN3
..\venv\Scripts\python.exe ..\main.py --type vcn3 --start_date 2026-01 --reseau_sandre BSH001 --vcn3_graphic

REM Mois précédent
..\venv\Scripts\python.exe ..\main.py --type meteo_sim2_MENS --start_date 2026-01-01 --end_date 2026-01-31

REM Première décade du mois précédent
..\venv\Scripts\python.exe ..\main.py --type meteo_sim2_QUOT --start_date 2026-01-01 --end_date 2026-01-10 --meteo_aggregate

REM Données ONDE
..\venv\Scripts\python.exe ..\main.py --type onde_ALL --start_date 2026-06-01 --geographic_scale BASSIN --onde_zone_code 06

pause
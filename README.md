# Outil de Récupération et Visualisation de Données Hydrologiques et Météorologiques

Ce programme permet de **récupérer, analyser et visualiser** des données sur l'eau et la météo en France. Il est conçu pour les professionnels de l'hydrologie, les gestionnaires de bassin versant ou toute personne ayant besoin d'analyser des données environnementales.

## 📋 À quoi sert ce programme ?

Avec cet outil, vous pouvez :

- ✅ **Récupérer des données hydrologiques** : Récupération des hauteurs des cours d'eaux, débits des rivières via l'API Hub'Eau
- ✅ **Analyser les écoulements** : données ONDE (Observatoire National des Établissements) pour les cours d'eau
- ✅ **Obtenir des données météo** : précipitations, indices de sécheresse via MétéoFrance
- ✅ **Calculer des indicateurs** :
   - **Hydraulicité** : mesure du débit d'eau par rapport à la normale
   - **VCN3** : Volume Current Non-dépassé sur 3 mois (période de retour et fréquence de non-dépassement)
   - **SPI** : Indice de Précipitation Standardisé (sécheresse météorologiques)
   - **SSWI** : Indice Standardisé d'Humidité des Sols
- ✅ **Générer des cartes** au format GeoJSON, compatibles avec QGIS et autres logiciels SIG

> **Info** : Documentation en ligne ici : https://github.com/Agryos/recup-etiage.

---
n
## 🔧 Prérequis

Pour utiliser ce programme, vous avez besoin de :
- **Python 3.11 ou supérieur** installé
- Une connexion internet (pour télécharger les données et les paquets nécessaires)

> ⚠️ **Important** : Si vous êtes sur le réseau interne de votre organisation, vous devrez peut-être configurer un proxy (voir section dédiée plus bas).

---

## 📥 Installation

Suivez ces étapes **dans l'ordre** :

### 1. Télécharger le programme

Deux options :
- **Option A (recommandée si vous avez Git)** : Ouvrez l'invite de commandes et tapez :
  ```bash
  git clone https://github.com/Agryos/recup-etiage.git
  ```
- **Option B (sans Git)** : 
  1. Allez sur [la page GitHub](https://github.com/Agryos/recup-etiage)
  2. Cliquez sur le bouton vert **"Code"**
  3. Sélectionnez **"Download ZIP"**
  4. Extrayez le fichier ZIP dans un dossier de votre choix

### 2. Ouvrir le terminal dans le bon dossier

1. Ouvrez l'explorateur de fichiers et allez dans le dossier où vous avez téléchargé le programme
2. **Cliquez droit** dans un espace vide du dossier (sans sélectionner de fichier)
3. Sélectionnez **"Ouvrir dans le terminal"** ou **"Ouvrir PowerShell ici"**

> 💡 Si vous ne voyez pas cette option, maintenez la touche **Maj (Shift)** enfoncée, faites un clic droit dans le dossier, puis choisissez **"Ouvrir une fenêtre PowerShell ici"**.

### 3. Créer l'environnement Python

Dans le terminal qui s'est ouvert, tapez la commande suivante pour créer un "environnement virtuel" (un espace isolé pour installer les outils nécessaires) :

```bash
py -3.11 -m venv venv
```

> ⚠️ Si vous avez plusieurs versions de Python, utilisez `python3-64.exe` à la place de `python`.

### 4. Installer les paquets nécessaires

Tapez cette commande pour installer tous les outils dont le programme a besoin :

```bash
.\venv\Scripts\pip.exe install -r .\requirements.txt
```

> ⚠️ **Attention** : Cette étape peut prendre plusieurs minutes et nécessite une connexion internet **hors du réseau interne** de votre organisation.

> ⚠️ **Attention** : En cas de problème lors de l'installation des paquets, cela peut-être du à la longueur des chemins maximum Windows étant dépassé, essayez de rapprocher les scripts de la racine de l'ordinateur. (plus proche du disque dur ou mettez le dossier directement dans Documents)

### 5. Vérifier que tout est installé correctement

Pour vérifier que l'installation a fonctionné, tapez :

```bash
.\venv\Scripts\python.exe main.py -h
```

Vous devriez voir s'afficher un message d'aide avec toutes les options disponibles. Si c'est le cas, **bravo, l'installation est terminée !** 🎉

---

## Mise à jour
Pour mettre à jour les script, vous pouvez utiliser git ou passer par GitHub :
### Git
1. Installer git sur votre ordinateur (avec git bash lors de l'installation)
2. **Si vous êtes sur le réseau interne :** 
   1. Copiez le contenu de votre `.env` dans le fichier `scripts/mise_a_jour.sh` ainsi
   2. Exemple : 
      
      .env : 
      ```
      HTTP_PROXY="http://mon-super-proxy.fr:port"
      HTTPS_PROXY="http://mon-super-proxy.fr:port"
      ```
      On rajoute `export` devant chaque ligne : 
      ```
      export HTTP_PROXY="http://mon-super-proxy.fr:port"
      export HTTPS_PROXY="http://mon-super-proxy.fr:port"
      ```
3. Double-cliquez sur le fichier `scripts/mise_a_jour.bat`
4. Lorsque les nouveaux commits s'affichent, vous pouvez utiliser les flèches pour vous déplacer et q pour sortir.

### GitHub
1. Allez sur [la page GitHub du dépot](https://github.com/Agryos/recup-etiage).
2. Cliquez sur code -> download zip
3. Copiez le dossier sur le vôtre en remplaçant lorsqu'il y a des changements.

---

## 🚀 Utilisation du Programme

Il existe **deux manières** d'utiliser ce programme :

### 🔹 Option 1 : Mode Interactif (recommandé pour les débutants)

Le mode interactif vous guide pas à pas en vous posant des questions. C'est la méthode la plus simple.

#### Comment lancer le mode interactif ?

Dans le terminal (toujours dans le dossier du programme), tapez simplement :

```bash
.\venv\Scripts\python.exe main.py
```

Le programme vous posera alors une série de questions :

**Exemple complet d'utilisation :**

```
Bienvenue dans le client de génération de cartes interactif, que souhaitez vous faire ?
(Il est aussi possible de lancer le script en mode CLI (-h))
1 : Générer une carte d'hydraulicité
2 : Générer une carte de vcn3/période de retour
3 : Générer les deux (lent au premier lancement)
4 : Générer des extraits MétéoFrance (défaut)
 -> 1

Choix de génération de carte : 1
Choisissez la date que vous voulez générer :
Format AAAA-MM, (mois précédent : 2026-06 par défaut)
 -> 2026-01

Mois sélectionné : 2026-01-01 00:00:00
Choisissez un réseau : BSH001 (par défaut)
Rentrez 'custom' pour utiliser une liste personnalisée.
 -> 

Réseau sélectionné : BSH001
Génération en cours...
Génération terminée.
```

**Que faire à chaque question ?**

| Question | Que répondre ? | Exemple |
|----------|---------------|---------|
| Que souhaitez-vous faire ? | Choisissez le type de carte à générer | `1` pour l'hydraulicité |
| Choisissez la date | Entrez la date au format AAAA-MM (année-mois) | `2026-01` pour janvier 2026 |
| Choisissez un réseau | Entrez le code du réseau ou `custom` | `BSH001` ou `custom` |
| Souhaitez-vous générer les graphiques ? | Répondez `o` pour oui ou `n` pour non | `o` |

> **Astuce** : Vous pouvez **interrompre une commande à tout moment** en appuyant sur **Ctrl+C** dans le terminal.

---

### 🔹 Option 2 : Mode CLI (Ligne de Commande) - Pour les utilisateurs avancés

Le mode CLI (Command Line Interface) permet de lancer directement une commande avec tous les paramètres. C'est plus rapide une fois que vous maîtrisez les options.

#### Structure de base :

```bash
.\venv\Scripts\python.exe main.py --type [TYPE] [autres options]
```

#### Tableau des types de données disponibles :

| Type | Description | Durée |
|------|-------------|-------|
| `hydraulicite` | Calcul de l'hydraulicité (débit par rapport à la normale) | 1 mois |
| `vcn3` | Calcul du VCN3 (période de retour) | 1 mois |
| `meteo_brut_MENS` | Données météo brutes mensuelles | Intervalle |
| `meteo_sim2_MENS` | Données météo SIM2 mensuelles | Intervalle |
| `meteo_brut_QUOT` | Données météo brutes quotidiennes | Intervalle |
| `meteo_sim2_QUOT` | Données météo SIM2 quotidiennes | Intervalle |
| `onde_USUELLE` | Données ONDE (campagnes usuelle uniquement) | 1 mois |
| `onde_ALL` | Données ONDE (toutes campagnes) | 1 mois |

> ℹ️ Toutes les sorties sont générées au format **GeoJSON** pour une utilisation directe dans QGIS ou d'autres logiciels SIG.

> **Astuce** : Vous pouvez **interrompre une commande à tout moment** en appuyant sur **Ctrl+C** dans le terminal.

#### 📌 Exemples concrets d'utilisation en CLI

**Exemple 1 : Générer une carte d'hydraulicité pour janvier 2026**
```bash
.\venv\Scripts\python.exe main.py --type hydraulicite --start_date 2026-01 --reseau_sandre BSH001
```
> ➡️ Cela génère une carte montrant l'hydraulicité (niveau d'eau par rapport à la normale) pour toutes les stations du réseau BSH001 au mois de janvier 2026.

---

**Exemple 2 : Calculer le VCN3 pour février 2024 avec des graphiques individuels**
```bash
.\venv\Scripts\python.exe main.py --type vcn3 --start_date 2024-02 --reseau_sandre BSH001 --vcn3_graphic
```
> ➡️ Le flag `--vcn3_graphic` génère en plus des graphiques détaillés pour chaque station.

---

**Exemple 3 : Récupérer les données météo SIM2 quotidiennes pour une période spécifique**
```bash
.\venv\Scripts\python.exe main.py --type meteo_sim2_QUOT --start_date 2023-07-01 --end_date 2023-07-31
```
> ➡️ Récupère les données météo SIM2 (indice de sécheresse, précipitations) pour tout le mois de juillet 2023, jour par jour.

---

**Exemple 4 : Récupérer les données météo SIM2 mensuelles agrégées depuis septembre 2025**
```bash
.\venv\Scripts\python.exe main.py --type meteo_sim2_MENS --start_date 2025-09-01 --end_date 2026-07-01 --meteo_aggregate
```
> ➡️ Le flag `--meteo_aggregate` permet d'agréger (sommer) les données sur toute la période pour avoir une vue d'ensemble.

---

**Exemple 5 : Récupérer les données ONDE pour le bassin versant Rhône-Méditerranée (code 06)**
```bash
.\venv\Scripts\python.exe main.py --type onde_ALL --start_date 2026-06-01 --geographic_scale BASSIN --onde_zone_code 06
```
> ➡️ Récupère toutes les données ONDE (usuelle + complémentaire) pour le bassin versant 06 (Rhône-Méditerranée) pour juin 2026.

---

**Exemple 6 : Utiliser une liste personnalisée de stations**
```bash
.\venv\Scripts\python.exe main.py --type hydraulicite --start_date 2026-01 --reseau_sandre custom
```
> ➡️ Utilise les stations définies dans vos fichiers personnalisés (`liste_site_custom.csv` et `liste_station_custom.csv`). **Vous n'êtes pas obligé de créer ces fichiers** : une liste par défaut existe déjà et sera utilisée si vous ne spécifiez pas `custom`.

---

#### 📋 Options disponibles pour tous les types :

| Option | Description | Valeur par défaut | Exemple |
|--------|-------------|-------------------|---------|
| `--start_date` | Date de début (format : AAAA-MM ou AAAA-MM-JJ) | Début du mois précédent | `--start_date 2026-01` |
| `--end_date` | Date de fin (format : AAAA-MM ou AAAA-MM-JJ) | Fin du mois précédent | `--end_date 2026-01-31` |
| `--reseau_sandre` | Réseau SANDRE à utiliser | `BSH001` | `--reseau_sandre custom` |
| `--vcn3_graphic` | Générer des graphiques pour le VCN3 | Non | Ajoutez le flag pour activer |
| `--geographic_scale` | Échelle géographique pour météo/onde | `BASSIN` | `BASSIN`, `REGION_ADMINISTRATIVE`, `DEPARTEMENT_BASSIN` |
| `--onde_zone_code` | Code de la zone géographique pour ONDE | `01` | `--onde_zone_code 06` |
| `--meteo_aggregate` | Agrégé les données météo sur la période | Non | Ajoutez le flag pour activer |
| `--meteo_no_update` | Désactiver la mise à jour des données météo | Non | Ajoutez le flag pour désactiver |

---

## 🗂️ Fichiers de Configuration et Données Personnalisées

### Utiliser vos propres listes de stations/sites

Le programme permet d'utiliser vos propres listes de stations et sites hydrologiques (rentrer **`custom`** quand on demande une liste SANDRE) :

1. **`liste_site_custom.csv`** : Liste des sites que vous souhaitez surveiller
2. **`liste_station_custom.csv`** : Liste des stations spécifiques

**Comment faire ?**
- **Une liste par défaut est déjà disponible**.
- Le programme complète automatiquement les listes et stations en fonction de ce qui est renseignée
- Si un site a plusieurs stations et que vous voulez n'en garder qu'une, ajoutez-la dans `liste_station_custom.csv`.

> ℹ️ Le fichier de sortie résumant les stations et sites utilisés sera généré dans : `output/site_station_custom/liste_site_et_station_custom.csv`

---

## 📁 Où trouver les résultats ?

Tous les fichiers générés par le programme sont stockés dans le dossier **`output`** à la racine du projet. Les résultats sont au format **GeoJSON** pour une utilisation directe dans QGIS ou d'autres logiciels SIG.

### Structure du dossier de sortie :

```
output/
├── QGIS/                    # Cartes générées
│   ├── hydraulicite/        # Cartes d'hydraulicité
│   ├── vcn3/                # Cartes de VCN3
│   └── meteo/               # Cartes météo
├── onde/                    # Cartes ONDE
├── meteoFrance/             # Données météo téléchargées
│   └── downloaded_data/     # Données brutes
├── site_station_custom/     # Listes personnalisées
└── logs/                    # Journaux d'exécution (pour le dépannage)
```

### Description des résultats

#### ONDE

Les résultats ONDE se trouvent tous dans le dossier output/onde.

Ils sont rangé par date, puis, on trie en fonction de la zone géographique choisie : 
- D Département
- R Région
- B bassin

Il n'y a pas de distinction entre une zone administrative et une zone bassin pour ONDE, seule la zone administrative est utilisée.

Vous pouvez trouver dans le dossier les images des graphiques ONDE avec 3 lettres possible :
- A, les graphiques des campagnes les plus récentes possible (ALL = Usuelle et Complémentaire) (recommandé)
- C, les graphiques concernant uniquement les campagnes complémentaires
- U, les graphiques concernant uniquement les campagnes usuelles

Dans le dossier csv et geojson, on retrouve des fichiers se terminant par :
- all, contiens toutes les données du mois des campagnes ONDE.
- complémentaires, contient toutes les données du mois pour les campagnes complémentaires uniquement.
- usuelles, contient toutes les données du mois pour les campagnes usuelles uniquement.
- latest, contient les dernières données enregistrées pour chaque station (on garde la donnée la plus récente entre les campagnes usuelles et complémentaire).


Dans le dossier HISTORIC_DATA, vous retrouverez TOUTES les observations enrichies de leurs données de campagnes.

---

## 🌐 Utiliser un Proxy (pour les réseaux internes)

Si vous êtes sur le réseau interne de votre organisation et que vous avez des restrictions d'accès internet, vous devez configurer un proxy.

### Comment faire ?

1. Copiez le fichier `.env_example` et renommez-le en `.env`
2. Ouvrez le fichier `.env` avec un éditeur de texte (comme le Bloc-notes)
3. Remplacez les lignes par les informations de votre proxy :

```
# Exemple de configuration proxy
HTTP_PROXY="http://votre-proxy.fr:8080"
HTTPS_PROXY="http://votre-proxy.fr:8080"
```

4. Sauvegardez le fichier

> ⚠️ **Important** : Le fichier `.env` ne doit pas être partagé publiquement (il contient des informations sensibles sur votre réseau).

---

## 🛠️ Dépannage

### ❌ Problème : "Python n'est pas reconnu"

**Solution :** Vérifiez que Python est bien installé et ajouté au PATH. Vous pouvez aussi utiliser le chemin complet :
```bash
C:\Chemin\vers\Python\python.exe -m venv venv
```

---

### ❌ Problème : Erreur lors de l'installation des paquets

**Solution 1 :** Vérifiez que vous êtes bien connecté à internet (hors réseau interne).

**Solution 2 :** Essayez de réinstaller les paquets un par un :
```bash
.\venv\Scripts\pip.exe install cl-hubeau
.\venv\Scripts\pip.exe install pandas
.\venv\Scripts\pip.exe install geopandas
```

**Solution 3 :** Si un paquet spécifique pose problème :
```bash
.\venv\Scripts\pip.exe uninstall nom_du_paquet -y
.\venv\Scripts\pip.exe install -r .\requirements.txt
```

---

### ❌ Problème : Le programme plante avec une erreur obscure

**Solution :**
1. Supprimez le dossier `venv`
2. Supprimez le dossier `output` (si vous voulez tout recommencer)
3. Relancez l'installation depuis le début

---

### ❌ Problème : Les données ne se mettent pas à jour

**Solution :** Utilisez les flags de mise à jour pour forcer la synchronisation. Par défaut, les données météo quotidiennes brutes se mettent à jour automatiquement.

---

## 📚 Comprendre les Concepts Clés

### Qu'est-ce que l'Hydraulicité ?

L'**hydraulicité** est un indicateur qui mesure le **niveau d'eau actuel par rapport à la normale**.
- **> 100%** : Le débit est supérieur à la normale (situation humide)
- **= 100%** : Le débit est normal
- **< 100%** : Le débit est inférieur à la normale (situation sèche)

C'est utile pour évaluer si une rivière a plus ou moins d'eau que d'habitude.

---

### Qu'est-ce que le VCN3 ?

Le **VCN3** (Volume Current Non-dépassé sur 3 mois) est un indicateur utilisé pour évaluer la **sécheresse**. Il représente le volume d'eau minimal qui n'a pas été dépassé pendant 3 mois consécutifs.

Le programme calcule aussi :
- **Période de retour** : Combien de temps en moyenne il faut attendre pour revoir un tel niveau bas
- **Fréquence de non-dépassement** : La probabilité que ce niveau ne soit pas dépassé

---

### Qu'est-ce que SIM2 ?

**SIM2** est un produit de MétéoFrance qui fournit des **données météo sur une grille de 8x8 km**. Contrairement aux données de stations météo ponctuelles, SIM2 donne une couverture complète du territoire.

Les indicateurs disponibles :
- **SPI** (Standardized Precipitation Index) : Mesure la sécheresse **météorologique** (manque de pluie)
- **SSWI** (Standardized Soil Wetness Index) : Mesure la sécheresse **des sols** (manque d'humidité dans le sol)

---

### Qu'est-ce que ONDE ?

**ONDE** (Observatoire National des Établissements) est un réseau de mesure de l'**écoulement des cours d'eau** en France. Les données sont collectées par des observateurs qui notent régulièrement le niveau d'eau dans les rivières.

Il existe deux types de campagnes :
- **USUELLE** : Mesures régulières
- **COMPLÉMENTAIRE** : Mesures supplémentaires en cas de situation particulière

---

### Qu'est-ce que le réseau SANDRE ?

Le **SANDRE** (Service d'Administration Nationale des Données et Référentiels sur l'Eau) est un système d'information sur l'eau en France. Chaque **réseau SANDRE** correspond à un ensemble de stations de mesure hydrologiques.

- **BSH001** : Réseau par défaut (bassin Artois-Picardie)
- **custom** : Utilise vos propres listes de stations/sites (ou la liste par défaut si vous ne fournissez pas de fichier personnalisé)
---

## 📞 Support et Contribution

### Vous avez trouvé un bug ou vous avez une suggestion ?

N'hésitez pas à :
1. Vérifier que le problème persiste après avoir relancé le programme
2. Consulter les logs dans le dossier `output/logs/`
3. Rapporter le problème sur la page GitHub : [https://github.com/Agryos/recup-etiage](https://github.com/Agryos/recup-etiage)

---

## 🎯 Résumé rapide des commandes les plus utilisées

| Besoin | Commande |
|--------|----------|
| **Hydraulicité du mois dernier** | `.\venv\Scripts\python.exe main.py --type hydraulicite` |
| **VCN3 du mois dernier** | `.\venv\Scripts\python.exe main.py --type vcn3` |
| **Météo SIM2 quotidienne pour hier** | `.\venv\Scripts\python.exe main.py --type meteo_sim2_QUOT --start_date 2026-07-09 --end_date 2026-07-09` |
| **Météo SIM2 mensuelle agrégée** | `.\venv\Scripts\python.exe main.py --type meteo_sim2_MENS --start_date 2026-06-01 --end_date 2026-07-01 --meteo_aggregate` |
| **Données ONDE pour le bassin 06** | `.\venv\Scripts\python.exe main.py --type onde_ALL --start_date 2026-06-01 --geographic_scale BASSIN --onde_zone_code 06` |
| **Lancer en mode interactif** | `.\venv\Scripts\python.exe main.py` |

---

## Documentation en ligne
Toute une documentation plus précise en ligne est disponible ici : https://agryos.github.io/recup-etiage/.

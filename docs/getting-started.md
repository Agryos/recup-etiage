---
layout: default
title: Guide de Démarrage
description: "Installation et configuration de l'outil"
nav_order: 2
parent: ""
---

[Retour à l'accueil](index.md)

# 🚀 Guide de Démarrage

Ce guide vous explique comment installer et configurer l'outil pour commencer à récupérer et visualiser des données hydrologiques et météorologiques.

---

## 📋 Prérequis

Pour utiliser ce programme, vous avez besoin de :

| Éléments | Version Requise | Notes |
|----------|----------------|-------|
| **Système d'exploitation** | Windows | Le programme a été testé sur Windows |
| **Python** | 3.11 ou supérieur | [Télécharger Python](https://www.python.org/downloads/) |
| **Git** | Optionnel | Recommandé pour le téléchargement |
| **Connexion Internet** | Obligatoire | Pour télécharger les données et dépendances |

> ⚠️ **Important** : Si vous êtes sur le réseau interne de votre organisation, vous devrez peut-être configurer un proxy (voir section [Proxy](#-utiliser-un-proxy)).

---

## 📥 Installation

Suivez ces étapes **dans l'ordre** :

### 1. Télécharger le programme

**Option A (recommandée si vous avez Git)** :
```powershell
git clone https://github.com/Agryos/recup-etiage.git
cd recup-etiage
```

**Option B (sans Git)** :
1. Allez sur [la page GitHub](https://github.com/Agryos/recup-etiage)
2. Cliquez sur le bouton vert **"Code"**
3. Sélectionnez **"Download ZIP"**
4. Extrayez le fichier ZIP dans un dossier de votre choix

### 2. Créer l'environnement Python

Ouvrez un PowerShell dans le dossier du projet et exécutez :

```powershell
python -m venv venv
```

> ⚠️ **Astuce** : Si vous avez plusieurs versions de Python ou que la commande `python` n'est pas reconnue, tapez `python` puis appuyez sur la touche **Tab** plusieurs fois dans PowerShell. Cela affichera toutes les versions de Python disponibles (ex: `python.exe`, `python3-64.exe`, `python3.11.exe`). Sélectionnez celle qui correspond à Python 3.11 ou supérieur.

### 3. Installer les dépendances

```powershell
.\venv\Scripts\pip.exe install -r .\requirements.txt
```

> ⚠️ **Attention** : Cette étape peut prendre plusieurs minutes et nécessite une connexion internet **hors du réseau interne** de votre organisation.

### 4. Vérifier l'installation

Pour vérifier que tout fonctionne correctement :

```powershell
.\venv\Scripts\python.exe main.py -h
```

Vous devriez voir s'afficher un message d'aide avec toutes les options disponibles. Si c'est le cas, **bravo, l'installation est terminée !** 🎉

---

## 🔧 Configuration initiale
### Configuration de la liste custom
Vous pouvez, au lieu d'utiliser des codes de réseau **Sandre** pour récupérer les données d'hydraulicité et de VCN3, utiliser une liste de stations et de sites que vous avez vous-même définie (`custom`).

**Il n'est pas nécessaire de créer ces fichiers** : une liste par défaut existe déjà et sera utilisée automatiquement si vous ne spécifiez pas `custom`.

Vous pouvez retrouver ou modifier ces listes dans :
- `data/liste_station_custom.csv` (liste des stations)
- `data/liste_site_custom.csv` (liste des sites)

Le programme va agréger ces deux listes en `output/site_station_custom/liste_site_et_station_custom.csv`.


Vous pouvez ainsi vérifier que les listes de sites/stations se sont bien générés. En cas d'ambiguïté sur un site ayant plusieurs stations potentielles, vous pouvez ajouter la station que vous souhaitez dans `liste_station_custom.csv` : cette station uniquement sera retenue.

Le plus simple étant de renseigner simplement toutes les stations directement (les sites auxquels les stations appartiennent sont retrouvés automatiquement).

>  **Astuce** : Vous pouvez **interrompre une commande à tout moment** en appuyant sur **Ctrl+C** dans le terminal.

### Configuration des zones géographiques par défaut
Les scripts MétéoFrance utilisent les listes de bassin, département, région définis dans :
- `liste_bassin.csv` (codes **Sandre** pour les bassins)
- `liste_departement.csv` (codes **INSEE** pour les départements)
- `liste_region.csv` (codes **INSEE** pour les régions)

Lorsque vous ferez la commande pour générer les données MétéoFrance des `DEPARTEMENT_ADMINISTRATIF` par exemple, le fichier `liste_departement.csv` est chargé, et les données pour ces départements sont récupérées et générées.

Le fichier `liste_bassin.csv` ne peut contenir que **1 seul bassin versant**.

> **Note** : Les codes pour les bassins sont des codes **Sandre**, tandis que les codes pour les départements et régions sont des codes **INSEE**.

### Configuration du Proxy (si nécessaire)

Si vous êtes sur un réseau interne :

1. Copiez le fichier `.env_example` et renommez-le en `.env`
2. Ouvrez le fichier `.env` avec un éditeur de texte
3. Ajoutez vos informations de proxy :

```ini
# Exemple de configuration proxy
HTTP_PROXY="http://votre-proxy.fr:8080"
HTTPS_PROXY="http://votre-proxy.fr:8080"
```

4. Sauvegardez le fichier

> ⚠️ **Important** : Le fichier `.env` ne doit pas être partagé publiquement.

---

## ❌ Dépannage

### Problème : "Python n'est pas reconnu"

**Solution** : Utilisez la touche **Tab** dans PowerShell : tapez `python` puis appuyez sur Tab pour voir les commandes disponibles. (habituellement `python.exe` ou `python3-64.exe`)

### Problème : Erreur lors de l'installation des paquets

**Solution 1** : Vérifiez que vous êtes bien connecté à internet (hors réseau interne).

**Solution 2** : Si un paquet spécifique pose problème :

```powershell
.\venv\Scripts\pip.exe uninstall nom_du_paquet -y
.\venv\Scripts\pip.exe install -r .\requirements.txt
```

### Problème : Le programme plante avec une erreur obscure

**Solution** :
1. Supprimez le dossier `venv`
2. Supprimez le dossier `output` (si vous voulez tout recommencer)
3. Relancez l'installation depuis le début

---

## 📚 Commencer à prendre en main le programme

- [Mode Interactif](usage/interactive.md)
- [Mode CLI](usage/cli.md)
- [Concepts Clés](concepts/index.md)




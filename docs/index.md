---
layout: home
title: Accueil
description: "Documentation complète pour l'outil de récupération, analyse et visualisation de données hydrologiques et météorologiques"
permalink: /
nav_order: 1
---

# 🌊 Outil de Récupération et Visualisation de Données Hydrologiques et Météorologiques

**Documentation API v0.0.1**

---

## 📋 À propos

Ce programme permet de **récupérer, analyser et visualiser** des données sur l'eau et la météo en France. Il est conçu pour les professionnels de l'hydrologie, les gestionnaires de bassin versant ou toute personne ayant besoin d'analyser des données environnementales.

## ✨ Fonctionnalités principales

| Fonctionnalité | Description |
|---------------|-------------|
| 💧 **Données Hydrologiques** | Récupération des niveaux d'eau et débits des rivières via l'API Hub'Eau |
| 📊 **Analyse des Écoulements** | Données ONDE (Observatoire National des Établissements) pour les cours d'eau |
| 🌦️ **Données Météorologiques** | Précipitations, indices de sécheresse via MétéoFrance |
| 📈 **Indicateurs Calculés** | Hydraulicité, VCN3, SPI, SSWI |
| 🗺️ **Cartographie** | Génération de cartes au format GeoJSON, compatibles avec QGIS |

## 🗂️ Structure de la Documentation

### [📖 Guide de Démarrage](getting-started.md)
- Prérequis
- Installation
- Configuration initiale

### [🎯 Utilisation](usage/index.md)
- [Mode Interactif](usage/interactive.md) - Pour les débutants
- [Mode CLI](usage/cli.md) - Pour les utilisateurs avancés

### [🔧 Modules](modules/index.md)
- **[plotting](modules/plotting/index.md)** - Module de visualisation *(documentation détaillée)*
  - [plot_grandeur](modules/plotting/plot_grandeur.md) - Visualisation des grandeurs hydrologiques
  - [plot_meteoFrance](modules/plotting/plot_meteoFrance.md) - Visualisation des données MétéoFrance
  - [plot_onde](modules/plotting/plot_onde.md) - Visualisation des données ONDE
  - [rasterize](modules/plotting/rasterize.md) - Rasterisation des GeoDataFrames
  - [plot_res_validation_clean](modules/plotting/plot_res_validation_clean.md) - Validation des données
  - [styles](modules/plotting/styles.md) - Styles et couleurs
- [config](modules/config/index.md) - Configuration
- [io](modules/io/index.md) - Entrées/Sorties
- [model](modules/model/index.md) - Modèles de données
- [processing](modules/processing/index.md) - Traitement des données
- [utils](modules/utils/index.md) - Utilitaires
- [cli](modules/cli/index.md) - Interface en ligne de commande

### [🎓 Concepts Clés](concepts/index.md)
- [Hydraulicité](concepts/hydraulicite.md)
- [VCN3 et Périodes de Retour](concepts/vcn3.md)
- [SPI et SSWI](concepts/spi-sswi.md)
- [ONDE](concepts/onde.md)
- [Réseau SANDRE](concepts/sandre.md)

### [📁 Structure des Données](data/index.md)
- [Sources de données](data/sources.md)
- [Format de sortie](data/output-format.md)

### [🔍 Référence API](api/reference.md)

## 🚀 Commencer

[📖 Lire le Guide de Démarrage →](getting-started.md)

---

## 📞 Support et Contribution

- **Bug ou suggestion** : [Ouvrir une issue sur GitHub](https://github.com/Agryos/recup-etiage/issues)
- **Code source** : [Dépôt GitHub](https://github.com/Agryos/recup-etiage)

---

*Documentation générée le {{ "now" | date: "%d %B %Y" }} | [Retour au dépôt](https://github.com/Agryos/recup-etiage)*




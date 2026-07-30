#!/bin/bash

# export HTTP_PROXY="http://mon-super-proxy.fr:port"
# export HTTPS_PROXY="http://mon-super-proxy.fr:port"

echo "Modification locale mise de côté"
git stash push
echo "Récupération des modifications en ligne"
git pull
echo "Rétablissement des modifications locale"
git stash pop

echo "Affichage des commits de la mise à jour"
git log HEAD@{1}..HEAD --graph --pretty=format:'%C(auto)%h %d %s (%ad)' --date=short --all
echo "Affichage des modifications de la mise à jour : (appuyez sur q pour quitter et les fleches pour se déplacer)"
git log HEAD@{1}..HEAD --patch

read -p "Mise à jour terminées, appuyez sur Entrée pour sortir..."

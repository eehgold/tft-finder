# TFT Finder

Un outil pour optimiser ta composition d'équipe dans **Teamfight Tactics** (Saison 16).
Tu sélectionnes tes champions, et l'outil te recommande le meilleur prochain personnage à acheter en fonction des synergies de traits, du tier des unités et des probabilités de drop.

---

## Prérequis

- **Python 3** installé sur ton PC ([télécharger ici](https://www.python.org/downloads/))
  - Pendant l'installation, **coche bien la case "Add Python to PATH"**
- **Pillow** (une librairie pour afficher les images)

## Installation

1. **Télécharge le projet** (bouton vert "Code" > "Download ZIP" sur GitHub, puis dézippe)

2. **Ouvre un terminal** dans le dossier du projet
   - Sur Windows : clic droit dans le dossier > "Ouvrir dans le terminal"

3. **Installe la dépendance** :
   ```
   pip install Pillow
   ```

## Lancement

Dans le terminal, tape :

```
python app.py
```

L'application s'ouvre, c'est prêt !

## Comment ça marche

1. Clique sur les champions pour les ajouter à ton équipe
2. Utilise la barre de recherche pour filtrer par nom, coût ou trait
3. Regarde les **traits activés** et leur progression à droite
4. L'outil te propose automatiquement le **meilleur champion suivant** à recruter
5. Ajuste ton **niveau joueur** pour voir les probabilités de drop

## Licence

Ce projet est sous licence **MIT** — tu es libre de l'utiliser, le modifier et le redistribuer comme tu veux. Voir le fichier [LICENSE](LICENSE) pour les détails.

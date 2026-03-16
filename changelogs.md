# Changelogs

## 2026-03-16
- Amelioration UI sur l'onglet items: les composants et items sont maintenant affiches dans la colonne de gauche (a la place des champions), pour une navigation plus logique.
- Optimisation de performance: les suggestions restent rapides meme avec des equipes plus grandes (le calcul des remplacements a ete accelere).
- Les remplacements sont maintenant limites par une variable de code (max 2 champions remplaces par scenario par defaut), avec des propositions possibles de 1 ou 2 changements selon le cas.
- Correction d'un bug dans les remplacements: l'outil ne propose plus de retirer un champion pour remettre exactement le meme.
- L'interface affiche maintenant clairement le remplacement propose dans une zone rouge ("Suggested remplacement") avec l'icone et le nom du champion a retirer.
- Un score de l'equipe actuelle est affiche avant les propositions, avec le score projete de chaque scenario pour mieux voir si un changement ameliore vraiment la compo.
- Galio est maintenant gere comme un "joker actif": il apporte ses synergies sans prendre de place sur le terrain, et il apparait dans une categorie separee dans "Mon equipe".
- Le moteur valorise mieux les gros paliers de synergie: a note egale (ex: S), un bonus qui demande plus d'unites est maintenant considere plus puissant.
- Le moteur propose maintenant des remplacements (retirer 1 unite et en ajouter 1 autre) quand votre equipe est deja complete.
- Tibbers est maintenant lie a Annie: on peut jouer Annie seule, mais Tibbers ne peut etre ajoute que si Annie est deja dans l'equipe.

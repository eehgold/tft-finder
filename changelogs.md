# Changelogs

## 2026-04-22
- Correction d'un plantage au demarrage: l'app ignore maintenant les images vides ou manquantes au lieu de se fermer.
- Ajout d'un selecteur de set dans l'application pour choisir facilement entre Set 16 et Set 17.
- Le jeu charge maintenant automatiquement le set le plus recent au demarrage.
- Reorganisation des donnees pour separer proprement les versions (`set16` et `set17`) et faciliter les futures mises a jour.
- Ajout des champions et synergies du Set 17 a partir des donnees officielles pour que les recommandations suivent la nouvelle saison.

## 2026-03-17
- Dans "Opti items", si un champion a deja le meme item, l'application l'indique clairement (ex: "deja x1/x2") et previent que c'est souvent un moins bon choix.
- Dans "Mon equipe", chaque champion affiche maintenant une note (S a D) juste sous son nom pour reperer rapidement les plus forts de ta compo.
- Suppression du raccourci annulation (Ctrl+Z) pour simplifier l'utilisation.
- Quand l'equipe depasse la taille autorisee, les retraits sont maintenant stables et coherents (plus de comportement aleatoire).
- Nettoyage interne du code pour retirer une ancienne logique non utilisee et rendre l'application plus fiable.
- Ajout d'un mode "Contraintes" dans Config pour guider les recommandations avec des regles simples.
- Tu peux maintenant forcer des champions a garder, des champions a eviter, et des synergies a imposer dans les propositions.
- Ajout de raccourcis clic droit: sur un champion tu peux activer/desactiver "garder" ou "eviter", et sur un trait actif tu peux activer/desactiver "forcer ce trait".
- Les contraintes actives sont visibles directement dans l'ecran avec des symboles simples: cadenas pour "garder/forcer" et croix rouge pour "eviter".

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

# Support FAQ Retrieval

**Retrouver une réponse, montrer sa source, mesurer quand s'abstenir.** Un laboratoire de recherche d'information en français pour une base de support client fictive.

Ce projet compare une référence par mots-clés à une recherche **TF-IDF + similarité cosinus**, explique les mots qui contribuent au score et évalue une règle d'abstention. Il représente une brique de recherche documentaire utilisable avant un système RAG, sans génération de texte ni service externe.

**Python standard uniquement · fonctionnement local · aucune clé API · données entièrement fictives.**

## Cas d'usage

Une équipe support veut proposer l'article pertinent pour une question sur les factures, les accès, les exports ou les abonnements. Une réponse mal orientée coûte du temps : le système peut afficher `abstain` quand le meilleur score n'atteint pas le seuil choisi.

La réponse retournée est toujours le texte exact d'un article avec son identifiant. Le score mesure une proximité lexicale ; il n'est **pas une probabilité de réponse correcte**. L'abstention ne garantit pas la détection des questions hors périmètre.

## Démarrage rapide

Python 3.10 ou supérieur. Vérifié avec Python 3.14.3 sous Windows.

```sh
git clone https://github.com/abdelouahabmoulinepro-coder/support-faq-retrieval.git
cd support-faq-retrieval
python retrieval.py search "Comment télécharger une facture PDF ?" --threshold 0.45
python retrieval.py search "Quel temps fera-t-il demain ?" --threshold 0.45
python retrieval.py evaluate --output build
python -m unittest discover -s tests -v
```

La première commande retrouve `billing-invoice`. La deuxième s'abstient. Le résultat JSON contient la réponse, sa source, les trois meilleurs candidats à score positif et les contributions des mots communs. Les textes JSON sont échappés en ASCII pour être lisibles sur les terminaux Windows ; ils se décodent normalement dans toute application JSON.

Pour utiliser la référence par mots-clés :

```sh
python retrieval.py search "Télécharger une facture PDF" --method overlap --threshold 0.65
```

Les seuils **0,45** et **0,65** proviennent exclusivement du jeu de développement fourni. La commande `search` utilise sinon un seuil illustratif de 0,20 ; elle ne charge pas automatiquement les résultats d'évaluation. Recalibrer pour un nouveau corpus et passer explicitement le seuil retenu.

## Résultats observés

Corpus : **12 articles**. Développement : **16 questions**, dont 4 hors périmètre. Test : **30 questions**, dont 6 hors périmètre. Les textes et identifiants de questions sont distincts entre développement et test.

| Mesure sur le test | Mots-clés | TF-IDF |
|---|---:|---:|
| Bonne réponse classée première, avant abstention (Hit@1) | 83,3 % (20/24) | 87,5 % (21/24) |
| MRR@3, avant abstention | 85,4 % | 87,5 % |
| Décisions correctes, abstentions incluses | 46,7 % (14/30) | 46,7 % (14/30) |
| Questions recevant une réponse | 26,7 % (8/30) | 33,3 % (10/30) |
| Réponses correctes parmi les réponses fournies | 100 % (8/8) | 90 % (9/10) |

**Lecture métier :** TF-IDF améliore légèrement le classement sur cet échantillon, mais n'améliore pas le nombre de décisions finales correctes. Les seuils réglés sur des questions de développement assez directes rejettent beaucoup de paraphrases du test. Les 100 % de précision des mots-clés ne portent que sur huit réponses ; ils ne démontrent pas une fiabilité générale.

Les erreurs individuelles sont publiées dans [le rapport](example/report.md), avec les métriques complètes et les empreintes des jeux dans [metrics.json](example/metrics.json). Aucun réglage n'est ajusté sur la base des résultats de test.

## Protocole d'évaluation

1. Ajuster le vocabulaire et les poids IDF **uniquement sur les articles de la FAQ**.
2. Pour chaque méthode, parcourir une grille fixe de seuils de 0 à 1 par pas de 0,05 sur les questions de développement.
3. Maximiser la proportion de décisions correctes : bon article pour une question couverte, abstention pour une question hors périmètre. En cas d'égalité, choisir le seuil le plus élevé.
4. Geler ce seuil et calculer les résultats sur les questions de test.

Les requêtes de développement et de test ne modifient jamais le vocabulaire ni l'IDF. Les articles pertinents sont présents dans l'index, ce qui est le fonctionnement attendu d'une tâche de recherche documentaire. Ce protocole ne mesure pas la généralisation vers de nouveaux articles ou de nouvelles entreprises.

**Définitions :**

- Hit@1 : proportion des questions couvertes dont l'article attendu est classé premier, avant abstention.
- MRR@3 : moyenne de `1 / rang` de l'article attendu dans les trois premiers candidats, ou zéro s'il est absent ; seulement sur les questions couvertes.
- Décisions correctes : bonnes réponses ou bonnes abstentions, divisées par toutes les questions.
- Couverture : nombre de réponses fournies / nombre total de questions.
- Précision des réponses : réponses correctes / réponses fournies ; `null` si aucune réponse n'est fournie.

## Méthodes explicables

La normalisation enlève les accents, met en minuscules, extrait des mots alphanumériques ASCII d'au moins deux caractères et retire une petite liste explicite de mots fréquents. Le titre et la réponse sont concaténés sans pondération supplémentaire du titre.

**Référence `overlap`** : nombre de mots distincts communs avec l'article, divisé par le nombre de mots distincts de la question. Les mots inconnus de la question restent dans ce dénominateur.

**Méthode `tfidf`** : fréquence brute du mot multipliée par `log((1 + N) / (1 + df)) + 1`, puis normalisation L2. La similarité cosinus est le produit scalaire des vecteurs normalisés. Les mots inconnus du corpus sont ignorés dans le vecteur de requête. Cette convention suit la [formulation TF-IDF lissée documentée par scikit-learn](https://sklearn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfTransformer.html), réimplémentée ici sans dépendance.

Chaque score est décomposé en contributions par mot commun. Les ex æquo sont départagés par identifiant d'article. Une question vide ou sans aucun mot connu provoque toujours une abstention, même avec un seuil nul.

## Adapter les données

`data/faq.json` est une liste d'articles avec `id`, `title` et `answer` non vides. Les identifiants doivent être uniques. `data/dev.json` et `data/test.json` sont des listes contenant `id`, `query` et `relevant_id` : identifiant attendu ou `null` pour une question sans réponse dans le corpus.

```sh
python retrieval.py evaluate --corpus data/faq.json --dev data/dev.json --test data/test.json --output build
```

Le programme rejette les identifiants de documents inconnus, les doublons de questions normalisées et le chevauchement des jeux. Il produit `metrics.json` et `report.md`. Le code de sortie est 0 pour une exécution réussie, même si les métriques sont mauvaises ; 1 pour une erreur de données traitée, 2 pour une erreur de syntaxe de commande.

## Tests et reproductibilité

**14 tests** vérifient notamment le calcul TF-IDF à la main, la référence par mots-clés, les seuils limites, les requêtes inconnues, la stabilité des ex æquo, les réponses exactes et sourcées, les métriques sur un exemple calculable, la séparation des jeux et l'indépendance des seuils vis-à-vis des labels de test.

L'évaluation est déterministe, sans tirage aléatoire. Le fichier `example/metrics.json` permet d'inspecter chaque prédiction. Les empreintes SHA-256 sont calculées sur un JSON canonique indépendant des fins de ligne et de l'indentation. Les sorties `build/` sont ignorées par Git.

## Limites et suites possibles

Le corpus et toutes les questions ont été rédigés pour ce projet ; **aucune conversation client réelle ni donnée personnelle** n'a été utilisée. Les règles de facturation, de sécurité et de suppression décrites dans les articles sont celles d'un produit imaginaire, pas des recommandations ni des engagements d'un service réel.

Ce petit jeu synthétique a un biais d'auteur et des thèmes partagés entre développement et test. Il n'est pas un benchmark indépendant. Il faudrait collecter et annoter des questions réelles autorisées, conserver un nouveau test intact et choisir le coût relatif d'une mauvaise réponse et d'une abstention avant tout usage opérationnel.

La recherche reste lexicale : pas de compréhension sémantique, de correction orthographique, de lemmatisation ni de compréhension de la négation. Des synonymes peuvent être manqués ; une question hors périmètre contenant les mêmes mots qu'un article peut obtenir un score élevé. Les mots inconnus ignorés par TF-IDF peuvent aussi gonfler la similarité. Une seule réponse pertinente est annotée par question, sans gestion explicite des demandes multiples.

Le moteur parcourt tous les articles en mémoire. Pour une base importante : index inversé, métriques de latence, puis comparaison avec une recherche sémantique sur un **nouveau** test. Pour modifier les seuils ou méthodes après analyse des erreurs publiées, traiter le test actuel comme jeu d'analyse et créer un autre jeu de test.

## Structure

```text
retrieval.py             Index, recherche, explications et évaluation
data/faq.json            12 articles fictifs
data/dev.json            16 questions de réglage
data/test.json           30 questions de test
example/metrics.json     Scores et prédictions publiés
example/report.md        Comparaison et analyse des erreurs
tests/test_retrieval.py  Tests unitaires et d'intégration
```

Licence MIT : voir [LICENSE](LICENSE).

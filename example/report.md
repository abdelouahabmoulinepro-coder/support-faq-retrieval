# FAQ Retrieval — évaluation

> Petit benchmark synthétique pédagogique : aucune mesure de performance en production.

Corpus : 12 articles · Réglage : 16 questions · Test : 30 questions.

| Méthode | Seuil réglé sur dev | Hit@1 | MRR@3 | Décisions correctes | Couverture | Précision des réponses |
|---|---:|---:|---:|---:|---:|---:|
| overlap | 0.65 | 83.3% | 85.4% | 46.7% | 26.7% | 100.0% |
| tfidf | 0.45 | 87.5% | 87.5% | 46.7% | 33.3% | 90.0% |

Hit@1 et MRR@3 portent sur les questions avec une réponse dans le corpus, avant abstention. Les autres métriques incluent les questions hors périmètre.

## Erreurs observées sur le test

### overlap

- test02 : Je ne me souviens plus de mon secret de connexion — attendu `access-password`, prédit `None` (score 0.200).
- test03 : Où conserver mes codes de récupération après activation ? — attendu `access-mfa`, prédit `None` (score 0.600).
- test04 : Comment ajouter une seconde vérification à la connexion ? — attendu `access-mfa`, prédit `None` (score 0.250).
- test06 : Je cherche le justificatif de mon achat en PDF — attendu `billing-invoice`, prédit `None` (score 0.250).
- test07 : Je veux une autre carte pour le prochain prélèvement — attendu `billing-card`, prédit `None` (score 0.600).
- test08 : Mon moyen de règlement doit être remplacé — attendu `billing-card`, prédit `None` (score 0.000).
- test09 : Après résiliation, le service reste-t-il accessible ? — attendu `plan-cancel`, prédit `None` (score 0.600).
- test10 : Je voudrais arrêter le renouvellement — attendu `plan-cancel`, prédit `None` (score 0.333).
- test12 : Ajouter un collègue à notre espace de travail — attendu `team-invite`, prédit `None` (score 0.000).
- test15 : Est-ce que les filtres actifs limitent le fichier exporté ? — attendu `data-export`, prédit `None` (score 0.600).
- test16 : Récupérer mes colonnes sur une période précise — attendu `data-export`, prédit `None` (score 0.500).
- test18 : Mon fichier de vingt mégaoctets dépasse-t-il la limite ? — attendu `data-import`, prédit `None` (score 0.400).
- test19 : Une clé API compromise doit être révoquée — attendu `integration-api`, prédit `None` (score 0.333).
- test20 : Combien de fois la clé est-elle affichée ? — attendu `integration-api`, prédit `None` (score 0.600).
- test22 : Je ne veux plus recevoir les notifications email — attendu `notifications`, prédit `None` (score 0.400).
- test24 : Je veux effacer mon profil pour toujours — attendu `account-delete`, prédit `None` (score 0.250).

### tfidf

- test02 : Je ne me souviens plus de mon secret de connexion — attendu `access-password`, prédit `None` (score 0.194).
- test03 : Où conserver mes codes de récupération après activation ? — attendu `access-mfa`, prédit `None` (score 0.308).
- test04 : Comment ajouter une seconde vérification à la connexion ? — attendu `access-mfa`, prédit `None` (score 0.194).
- test05 : Un lecteur peut-il accéder aux factures du mois ? — attendu `billing-invoice`, prédit `None` (score 0.317).
- test06 : Je cherche le justificatif de mon achat en PDF — attendu `billing-invoice`, prédit `None` (score 0.232).
- test08 : Mon moyen de règlement doit être remplacé — attendu `billing-card`, prédit `None` (score 0.000).
- test09 : Après résiliation, le service reste-t-il accessible ? — attendu `plan-cancel`, prédit `None` (score 0.321).
- test10 : Je voudrais arrêter le renouvellement — attendu `plan-cancel`, prédit `None` (score 0.219).
- test11 : Combien de jours reste valable une invitation ? — attendu `team-invite`, prédit `None` (score 0.427).
- test12 : Ajouter un collègue à notre espace de travail — attendu `team-invite`, prédit `None` (score 0.000).
- test13 : Quels rôles un administrateur peut-il attribuer ? — attendu `team-role`, prédit `None` (score 0.403).
- test15 : Est-ce que les filtres actifs limitent le fichier exporté ? — attendu `data-export`, prédit `None` (score 0.364).
- test16 : Récupérer mes colonnes sur une période précise — attendu `data-export`, prédit `None` (score 0.290).
- test18 : Mon fichier de vingt mégaoctets dépasse-t-il la limite ? — attendu `data-import`, prédit `None` (score 0.406).
- test24 : Je veux effacer mon profil pour toujours — attendu `account-delete`, prédit `None` (score 0.163).
- test29 : Puis-je payer ma facture en dollars ? — attendu `None`, prédit `billing-invoice` (score 0.465).

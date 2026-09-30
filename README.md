# ChronoLive
Application web de gestion et de chronométrage de courses cyclistes, développée avec Flask et SQLite, avec classement en direct disponible sur internet.

## Contexte
ChronoLive a été développé comme projet bénévole pour un club cycliste afin de disposer d'un outil dédié à la gestion et au chronométrage de compétitions, à commencer par un contre-la-montre et une grimpée.

## Modules
Inscription — gestion des coureurs, dossards, catégories et heures de départ.
Chronométrage — enregistrement et association des arrivées, avec gestion des statuts.
Classement live — diffusion du classement en temps réel via SSE.
Résultats — consultation des classements et export en PDF, PNG, Excel et CSV.
Dashboard — suivi de l’état de la course et du fonctionnement du système.


## Architecture


                    CHRONOLIVE
                        │
              ┌─────────┴─────────┐
              │                   │
          Configuration        Chronométrage
              │                   │
      ┌───────┼────────┐          │
      │       │        │          │
     CLM   Grimpée  Critérium     │
      │       │        │          │
      └───────┴────────┘          │
                                  │
                       ┌──────────┴──────────┐
                       │                     │
                    Manuel              Automatique
                                            │
                                      caméra / téléphone



ChronoLive est organisé en plusieurs modules Flask indépendants :

ChronoLive
│
├── app.py
├── config.py
├── database.py
├── models.py
│
├── modules/
│   ├── inscription.py
│   ├── chronometrage.py
│   ├── classement_live.py
│   ├── resultats.py
│   └── dashboard.py
│
├── templates/
│   ├── inscription.html
│   ├── chronometrage.html
│   ├── classement_live.html
│   ├── resultats.html
│   └── dashboard.html
│
├── exports/
│   ├── pdf.py
│   ├── png.py
│   ├── excel.py
│   └── csv.py
│
├── utils/
│   └── temps.py
│
└── debug/



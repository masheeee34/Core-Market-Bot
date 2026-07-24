---
title: Discord Ticket Bot
emoji: 🎫
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# 🎫 Discord Ticket Bot

Bot de gestion de tickets Discord (discord.py) — **sans base de données** : toutes les
données vivent dans Discord lui-même (config dans le footer du panel, propriétaire du
ticket dans le topic du salon). Hébergeable gratuitement (Render, HF Spaces...).

## Fonctionnalités

- Panel de création de tickets (Embed + Boutons : Support, Réclamation, Partenariat)
- Salons privés avec permissions restreintes (utilisateur + rôle Staff)
- Boutons dans le ticket : 🔒 Fermer, ✋ Réclamer (Claim), 📝 Transcript
- Transcripts HTML envoyés dans un salon de logs à la fermeture
- 1 seul ticket ouvert par membre
- Boutons persistants : tout survit aux redémarrages, sans stockage

## Configuration

| Variable d'environnement | Description |
|---|---|
| `DISCORD_TOKEN` | Token du bot (Discord Developer Portal) |

Intents privilégiés requis (Developer Portal → Bot) : **Server Members** + **Message Content**.

## Utilisation

Une seule commande : `/panel categorie role_staff salon_logs` (admin) — poste le panel
dans le salon courant. Tout le reste se fait par boutons.

## Architecture

```
├── main.py              # Bot + serveur web keep-alive (port 7860 / $PORT)
├── cogs/
│   ├── tickets.py       # Panel, création, boutons Claim/Transcript/Fermer
│   └── admin.py         # Commande /panel
└── utils/
    └── transcript.py    # Génération des transcripts HTML
```

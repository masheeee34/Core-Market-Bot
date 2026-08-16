# 🤖 Core Market — AI Support & DM Knowledge Base Documentation

Ce document explique le fonctionnement du système de **Support Vocal 24/7** et de l'**Assistant IA en Message Privé (DM)** avec retransmission en direct pour le staff.

---

## 🎧 1. Bureau Vocal 24/7 (`🎧・if you need help`)

* **Création automatique :** Le bot crée le salon vocal nommé `🎧・if you need help` dès son démarrage.
* **Permissions :**
  - `@everyone` : Salon visible mais connexion bloquée (présence dissuasive / indicatrice).
  - **Owner & Staff** : Connexion autorisée pour rejoindre le bot.
* **Watchdog 24/7 :** Le bot vérifie toutes les 45 secondes sa présence dans le vocal et se reconnecte automatiquement en cas de coupure.
* **Commande Admin :** `/support_desk_reconnect` force la reconnexion immédiate.

---

## 🧠 2. Moteur IA de Réponse Automatique en DM

Dès qu'un utilisateur (client ou prospect) envoie un Message Privé (DM) au bot, le bot analyse les mots-clés et l'intention dans `data/support_kb.json` et lui répond en quelques millisecondes.

### 📚 Sujets Reconnus & Mots-Clés Configurés :

| Thématique | Mots-clés déclencheurs | Réponse délivrée |
| :--- | :--- | :--- |
| **🎁 Clé d'essai 1H** | `trial`, `free`, `essai`, `gratuit`, `cle`, `key`, `demo`, `1h`, `claim` | Explication salon `#free-trial`, lien Mega et lien GitBook |
| **⚙️ Virtualisation BIOS** | `virtualisation`, `virtualization`, `bios`, `svm`, `vt-x`, `hyper-v` | Instructions AMD (SVM) et Intel (VT-x) + tutoriel GitBook |
| **📥 Téléchargement Loader**| `loader`, `download`, `telecharger`, `mega`, `zip`, `rar`, `lien` | Lien de téléchargement Mega officiel + étapes d'injection |
| **🛡️ Antivirus / Defender** | `antivirus`, `defender`, `bloque`, `smartscreen`, `virus`, `exclusion` | Procédure d'exclusion Windows Defender et sécurité |
| **💳 Tarifs & Paiements** | `prix`, `tarif`, `price`, `acheter`, `buy`, `payer`, `paypal`, `crypto` | Grille tarifaire M-CORE et SPECTRE + redirection ticket |
| **🔒 Sécurité / Streamproof**| `streamproof`, `obs`, `detecte`, `ban`, `ricochet`, `safe` | Garantie Ring-0 hypervisor et invisibilité OBS/Discord |
| **🎉 Giveaways / Invites** | `giveaway`, `concours`, `invitation`, `invite`, `ticket`, `gagner` | Règles de participation et bonus multiplicateur d'invitations |
| **🎫 Support Humain / Bug** | `aide`, `humain`, `staff`, `admin`, `ticket`, `probleme`, `bug`, `error` | Invitation à ouvrir un ticket dans `#creer-un-ticket` |

---

## 📡 3. Retransmission en Direct Côté Admin (`#📜・ʟᴏɢꜱ-ᴛɪᴄᴋᴇᴛꜱ`)

Chaque échange en DM est intercepté et publié en temps réel dans vos salons de logs staff :
* **Identifiant & Mention du client**
* **Intention détectée par l'IA**
* **Question exacte posée par le client**
* **Réponse fournie par le bot**

---

## ✍️ 4. Comment ajouter de nouvelles phrases ou réponses :

Pour ajouter de nouvelles réponses ou enrichir le bot, modifiez simplement [`data/support_kb.json`](file:///c:/Users/ayman/Documents/antigravity/resilient-newton/data/support_kb.json) :
```json
{
  "id": "mon_nouveau_sujet",
  "keywords": ["mot1", "mot2", "mot3"],
  "response_fr": "Texte en français...",
  "response_en": "Text in English..."
}
```

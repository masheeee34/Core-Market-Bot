# 2. Configuration Sécurité & Windows Defender

{% hint style="info" %}
Pour éviter que l'antivirus ne bloque l'injection en mémoire du loader ou ne supprime des fichiers temporaires, configurez les exclusions suivantes.
{% endhint %}

---

### 🛡️ 1. Ajouter une Exclusion de Dossier

1. Ouvrez le menu Démarrer et tapez **Sécurité Windows**.
2. Allez dans **Protection contre les virus et menaces**.
3. Sous *Paramètres de protection contre les virus et menaces*, cliquez sur **Gérer les paramètres**.
4. Faites défiler vers le bas jusqu'à **Exclusions**, puis cliquez sur **Ajouter ou supprimer des exclusions**.
5. Cliquez sur **Ajouter une exclusion** > **Dossier** et sélectionnez le dossier où se trouve votre Loader (ex: `C:\CoreLoader`).

---

### 🚫 2. Désactiver la Protection en Temps Réel (Optionnel si exclusion créée)

Si votre loader est bloqué au premier lancement :
* Dans *Paramètres de protection contre les virus et menaces*, basculez l'interrupteur **Protection en temps réel** sur **Désactivé**.

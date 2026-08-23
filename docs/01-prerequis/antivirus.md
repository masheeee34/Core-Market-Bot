# 3. Sécurité & Antivirus

Les logiciels de protection injectent ou scannent la mémoire en temps réel, ce qui peut bloquer le loader ou causer un faux-positif de Windows Defender.

---

### 🛡️ Désactiver Windows Defender en Temps Réel
1. Ouvrez les **Paramètres Windows** (`Win` + `I`).
2. Allez dans **Confidentialité et sécurité** > **Sécurité Windows** > **Protection contre les virus et menaces**.
3. Sous *Paramètres de protection contre les virus et menaces*, cliquez sur **Gérer les paramètres**.
4. Désactivez temporairement :
   * **Protection en temps réel**
   * **Protection fournie par le cloud**
   * **Soumission automatique d'échantillons**

---

### 📁 Ajouter un Dossier d'Exclusion
Pour ne pas avoir à désactiver l'antivirus à chaque redémarrage :
1. Sur la même page, descendez jusqu'à la section **Exclusions**.
2. Cliquez sur **Ajouter ou supprimer des exclusions** > **Ajouter une exclusion** > **Dossier**.
3. Sélectionnez le dossier où vous téléchargez et lancez vos loaders (ex: `C:\CoreMarket`).

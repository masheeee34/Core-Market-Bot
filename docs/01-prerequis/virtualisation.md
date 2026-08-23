# 1. Activation de la Virtualisation (BIOS)

L'activation de la virtualisation matérielle est indispensable pour le bon fonctionnement des hyperviseurs et des mécanismes de protection kernel.

---

### 🔹 Pour les Processeurs AMD (SVM Mode)
1. Éteignez complètement votre PC.
2. Démarrez en appuyant de manière répétée sur `Suppr` ou `F2` pour entrer dans le BIOS.
3. Allez dans **Advanced** (Mode Avancé / `F7`).
4. Rendez-vous dans **CPU Configuration** ou **OC / Tweaker**.
5. Cherchez l'option **SVM Mode** et passez-la sur **Enabled**.
6. Appuyez sur `F10` pour sauvegarder et redémarrer.

---

### 🔹 Pour les Processeurs Intel (VT-x)
1. Entrez dans le BIOS au démarrage (`Suppr` ou `F2`).
2. Allez dans **Advanced CPU Configuration**.
3. Cherchez **Intel Virtualization Technology** (ou **Intel VT-x**).
4. Passez l'option sur **Enabled**.
5. Appuyez sur `F10` pour sauvegarder et redémarrer.

---

### ✅ Comment Vérifier si la Virtualisation est Active ?
1. Ouvrez le **Gestionnaire des tâches** (`Ctrl` + `Maj` + `Échap`).
2. Allez dans l'onglet **Performances** > **Processeur (CPU)**.
3. En bas à droite, vérifiez que la ligne **Virtualisation** indique **Activé**.

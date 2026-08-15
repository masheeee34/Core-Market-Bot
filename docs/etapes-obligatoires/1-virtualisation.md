# 1. Activation de la Virtualisation (BIOS)

{% hint style="warning" %}
**Étape obligatoire :** Tous nos logiciels externes et émulateurs nécessitent que la virtualisation matérielle soit activée dans votre BIOS/UEFI.
{% endhint %}

---

### 🔍 Vérifier si la Virtualisation est déjà activée

1. Appuyez sur `Ctrl + Shift + Échap` pour ouvrir le **Gestionnaire des tâches**.
2. Cliquez sur l'onglet **Performance** puis sur **Processeur (CPU)**.
3. En bas à droite, regardez la ligne **Virtualisation** :
   * Si elle indique **Activé**, vous pouvez passer à l'étape suivante.
   * Si elle indique **Désactivé**, suivez les instructions ci-dessous pour l'activer dans le BIOS.

---

### ⚙️ Activer la Virtualisation dans le BIOS

1. Redémarrez votre PC.
2. Dès que l'écran s'allume, appuyez répétitivement sur la touche d'accès au BIOS (généralement `Suppr` / `Del`, `F2`, `F10` ou `F12` selon votre carte mère).
3. Rendez-vous dans les paramètres avancés du processeur :
   * **Pour processeurs AMD :** Cherchez l'option **SVM Mode** (Secure Virtual Machine) et passez-la sur **Enabled**.
   * **Pour processeurs Intel :** Cherchez l'option **Intel Virtualization Technology (Intel VT-x)** ou **VT-d** et passez-la sur **Enabled**.
4. Appuyez sur `F10` pour enregistrer et quitter (Save & Exit).
5. Votre ordinateur redémarre sous Windows avec la virtualisation active.

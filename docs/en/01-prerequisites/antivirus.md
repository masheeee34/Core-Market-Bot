# 3. Security & Windows Defender Settings

Real-time protection engines can sometimes scan or block loaders during injection, causing false-positive warnings.

---

### 🛡️ Temporarily Disable Real-Time Protection
1. Open **Windows Settings** (`Win` + `I`).
2. Go to **Privacy & Security** > **Windows Security** > **Virus & threat protection**.
3. Under *Virus & threat protection settings*, click **Manage settings**.
4. Temporarily toggle off:
   * **Real-time protection**
   * **Cloud-delivered protection**
   * **Automatic sample submission**

---

### 📁 Adding a Folder Exclusion
To avoid repeating these steps after every reboot:
1. On the same settings page, scroll down to **Exclusions**.
2. Click **Add or remove exclusions** > **Add an exclusion** > **Folder**.
3. Select the directory where you download and run your loaders (e.g., `C:\CoreMarket`).

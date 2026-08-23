# 1. BIOS Virtualization Setup

Enabling hardware virtualization is mandatory for hypervisor-level security and seamless background execution.

---

### 🔹 For AMD Processors (SVM Mode)
1. Turn off your PC completely.
2. Power on and repeatedly press `Del` or `F2` to enter the BIOS.
3. Switch to **Advanced Mode** (`F7`).
4. Navigate to **CPU Configuration** or **OC / Tweaker / Advanced**.
5. Locate **SVM Mode** and set it to **Enabled**.
6. Press `F10` to save and reboot.

---

### 🔹 For Intel Processors (VT-x)
1. Enter your BIOS upon startup (`Del` or `F2`).
2. Navigate to **Advanced CPU Configuration**.
3. Locate **Intel Virtualization Technology** (or **Intel VT-x**).
4. Set it to **Enabled**.
5. Press `F10` to save and reboot.

---

### ✅ How to Verify Virtualization is Active
1. Open **Task Manager** (`Ctrl` + `Shift` + `Esc`).
2. Go to the **Performance** tab > **CPU**.
3. Check the bottom-right corner: **Virtualization** should state **Enabled**.

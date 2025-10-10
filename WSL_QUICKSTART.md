# 🚀 WSL Compilation - Quick Start

## ✅ **Package Ready: `hailo_compilation_package.zip` (505 MB)**

Everything you need is in one zip file!

---

## 📋 **Quick Checklist**

### **On Your Mac (NOW):**

✅ **Transfer the package to your Windows machine:**

**Option 1: USB Drive**
```bash
# Copy to USB drive
cp hailo_compilation_package.zip /Volumes/YOUR_USB_DRIVE/
```

**Option 2: Network Transfer**
```bash
# Start HTTP server on Mac
python3 -m http.server 8000

# From Windows browser, download:
# http://<YOUR_MAC_IP>:8000/hailo_compilation_package.zip
```

**Option 3: Cloud**
- Upload to Google Drive / Dropbox
- Download on Windows

---

### **On Windows WSL (NEXT):**

```bash
# 1. Open WSL
wsl

# 2. Copy from Windows Downloads to WSL
cd ~
cp /mnt/c/Users/<YOUR_WINDOWS_USERNAME>/Downloads/hailo_compilation_package.zip .

# 3. Extract
unzip hailo_compilation_package.zip -d hailo_compilation
cd hailo_compilation

# 4. Read the guide
cat README.md

# 5. Install dependencies (one-time)
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip python3-venv \
    graphviz graphviz-dev build-essential

# 6. Create virtual environment
python3 -m venv hailo_venv
source hailo_venv/bin/activate

# 7. Install Hailo DFC
pip install --upgrade pip setuptools wheel
pip install hailo_dataflow_compiler-3.33.0-py3-none-linux_x86_64.whl

# 8. Verify installation
python -c "import hailo_sdk_client; print(f'✅ Hailo DFC v{hailo_sdk_client.__version__}')"

# 9. Run compilation (2-3 hours)
chmod +x wsl_compile_models.sh
./wsl_compile_models.sh

# 10. Copy results to Windows
cp output/*.hef /mnt/c/Users/<YOUR_WINDOWS_USERNAME>/Downloads/
```

---

## ⏱️ **Timeline**

| Step | Time | Notes |
|------|------|-------|
| Transfer package | 5-10 min | Depends on method |
| WSL setup | 10-15 min | One-time |
| DFC install | 5 min | One-time |
| **Compilation** | **2-3 hours** | **Automated** |
| Copy back | 2 min | Two small files |

---

## 📦 **What's in the Package**

```
hailo_compilation_package.zip (505 MB)
├── README.md                           # Full guide
├── wsl_compile_models.sh               # Compilation script
├── hailo_dataflow_compiler-3.33.0...  # DFC wheel (490 MB)
├── yolo11n_bee_best.onnx               # Model 1 (10 MB)
└── yolo11n_bee_v2.onnx                 # Model 2 (10 MB)
```

---

## 🎯 **Expected Output**

After compilation completes:

```
output/yolo11n_bee_best_thresh015.hef    # ~10-20 MB
output/yolo11n_bee_v2_thresh015.hef      # ~10-20 MB
```

These are your fixed models with **score_threshold=0.15**!

---

## ✅ **Verification**

On Raspberry Pi:
```bash
hailortcli parse-hef yolo11n_bee_best_thresh015.hef | grep threshold
```

Should show:
```
Score threshold: 0.150  ✅
```

---

## 💡 **Tips**

**Run in background (optional):**
```bash
# Use screen to keep running
sudo apt-get install screen
screen -S hailo
./wsl_compile_models.sh
# Ctrl+A, then D to detach
# screen -r hailo to reconnect
```

**Monitor progress:**
```bash
# In another terminal
tail -f ~/hailo_compilation/compilation.log
```

---

## 🆘 **Troubleshooting**

**"Virtual environment not found"**
```bash
python3 -m venv hailo_venv
source hailo_venv/bin/activate
```

**"Module not found: hailo_sdk_client"**
```bash
pip install hailo_dataflow_compiler-3.33.0-py3-none-linux_x86_64.whl
```

**"ONNX file not found"**
```bash
# Make sure you're in the hailo_compilation directory
cd ~/hailo_compilation
ls -la  # Should see both .onnx files
```

---

## 🎉 **Success = DETECTIONS!**

After transferring HEF files to Raspberry Pi and testing:

```
🎉 DETECTIONS FOUND!
  1. bee: conf=0.187
  2. bee: conf=0.203
  3. bee: conf=0.251
```

---

**Ready to start? Transfer the package to Windows!** 🚀

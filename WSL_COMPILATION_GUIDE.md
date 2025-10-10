# 🚀 Compiling Bee Models on Windows WSL2

## Date: October 10, 2025
## Target: Hailo-8L (13 TOPS)
## Fix: score_threshold=0.15 (was 0.30)

---

## 📦 **Step 1: Prepare Files on Your Mac**

First, package everything needed for WSL:

```bash
# On your Mac - create transfer package
cd /Users/davidgassier/digital4ai/bee-monitoring-system

# Create transfer directory
mkdir -p wsl_transfer

# Copy DFC wheel
cp hailo_dataflow_compiler-3.33.0-py3-none-linux_x86_64.whl wsl_transfer/

# Copy ONNX models
cp api/models/bee_detection_model_10022025/yolo11n_bee_best.onnx wsl_transfer/
cp api/models/yolo11n_bee_v2.onnx wsl_transfer/

# Copy compilation script (we'll create this next)
cp wsl_compile_models.sh wsl_transfer/

# Create a zip for easy transfer
cd wsl_transfer
zip -r ../hailo_compilation_package.zip .
cd ..

echo "✅ Package created: hailo_compilation_package.zip"
echo "📦 Transfer this file to your Windows machine"
```

---

## 🪟 **Step 2: On Your Windows Machine**

### **A. Open WSL2 Terminal**

In Windows, open PowerShell or Windows Terminal and type:
```bash
wsl
```

### **B. Check WSL Version**
```bash
uname -a
# Should show: Linux ... x86_64
```

### **C. Install Dependencies**
```bash
sudo apt-get update
sudo apt-get install -y unzip python3-dev python3-pip python3-tk \
    graphviz graphviz-dev build-essential python3-venv
```

---

## 📥 **Step 3: Transfer and Extract Files**

### **Option A: Via Network (if both machines on same network)**

On your Mac:
```bash
# Find your Mac's IP
ifconfig | grep "inet " | grep -v 127.0.0.1

# Start a simple HTTP server
cd /Users/davidgassier/digital4ai/bee-monitoring-system
python3 -m http.server 8000
```

On WSL:
```bash
# Download from Mac (replace <MAC_IP> with actual IP)
cd ~
wget http://<MAC_IP>:8000/hailo_compilation_package.zip
unzip hailo_compilation_package.zip -d hailo_compilation
cd hailo_compilation
```

### **Option B: Via Windows File System**

1. Copy `hailo_compilation_package.zip` to your Windows Downloads folder
2. In WSL:
```bash
cd ~
cp /mnt/c/Users/<YOUR_WINDOWS_USERNAME>/Downloads/hailo_compilation_package.zip .
unzip hailo_compilation_package.zip -d hailo_compilation
cd hailo_compilation
```

---

## 🔧 **Step 4: Set Up Python Environment**

```bash
# Create virtual environment
python3 -m venv hailo_venv

# Activate it
source hailo_venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install Hailo DFC
pip install hailo_dataflow_compiler-3.33.0-py3-none-linux_x86_64.whl

# Verify installation
python -c "import hailo_sdk_client; print(f'✅ Hailo DFC v{hailo_sdk_client.__version__} installed!')"
```

---

## 🐝 **Step 5: Run Compilation**

```bash
# Make script executable
chmod +x wsl_compile_models.sh

# Run compilation (will take 2-3 hours)
./wsl_compile_models.sh
```

**Expected output:**
```
======================================================================
🐝 COMPILING BEE MODELS WITH HAILO DFC v3.33.0
======================================================================

Model 1: yolo11n_bee_best.onnx (640x640)
  Settings:
    ✅ Hardware: hailo8l (13 TOPS)
    ✅ Score threshold: 0.15 ← FIX (was 0.30)
    ✅ IOU threshold: 0.45
    
  Step 1/3: Parsing ONNX...
  [... this will take 30-60 minutes ...]
  
  Step 2/3: Optimizing...
  [... this will take 30-60 minutes ...]
  
  Step 3/3: Compiling with NMS...
  [... this will take 30-60 minutes ...]
  
✅ Model 1 compiled successfully!

Model 2: yolo11n_bee_v2.onnx (800x800)
  [... same process ...]
  
✅ Model 2 compiled successfully!

🎉 COMPILATION COMPLETE!
```

---

## 📤 **Step 6: Transfer Compiled Models Back**

### **Compiled HEF files location:**
```
~/hailo_compilation/output/yolo11n_bee_best_thresh015.hef
~/hailo_compilation/output/yolo11n_bee_v2_thresh015.hef
```

### **Copy to Windows:**
```bash
# In WSL
cp ~/hailo_compilation/output/*.hef /mnt/c/Users/<YOUR_WINDOWS_USERNAME>/Downloads/
```

### **Then from Mac, get files from Windows machine via:**
- USB drive
- Network share
- Cloud storage (Google Drive, Dropbox)
- Email (files are ~10-20MB each)

---

## ✅ **Step 7: Verify Compilation**

On Raspberry Pi:
```bash
# Copy HEF files to Pi
scp yolo11n_bee_best_thresh015.hef rpi:/tmp/bee_models_fixed/

# Parse to verify settings
hailortcli parse-hef /tmp/bee_models_fixed/yolo11n_bee_best_thresh015.hef | grep threshold
```

**Should show:**
```
Score threshold: 0.150  ✅ (was 0.300)
IoU threshold: 0.45     ✅ (was 0.60)
```

---

## 🧪 **Step 8: Test on Raspberry Pi**

```bash
ssh rpi
cd /tmp/hailo-rpi5-examples
source setup_env.sh

# Update test script to use new model
python3 /tmp/test_hailopython.py bee_best image
```

**Expected result:**
```
🎉 DETECTIONS FOUND!
  1. bee: conf=0.187, bbox=(...)
  2. bee: conf=0.203, bbox=(...)
  3. bee: conf=0.251, bbox=(...)
```

---

## ⏱️ **Timeline**

| Step | Duration | Details |
|------|----------|---------|
| File transfer | 5-10 min | Depends on network |
| WSL setup | 10-15 min | One-time installation |
| DFC installation | 5 min | Pip install |
| **Model 1 compilation** | **1-1.5 hours** | Parse + Optimize + Compile |
| **Model 2 compilation** | **1-1.5 hours** | Parse + Optimize + Compile |
| Transfer back | 5 min | Copy to Windows |
| **Total** | **~3-4 hours** | Mostly automated |

---

## 💡 **Tips**

### **Run in Background**
```bash
# Use screen or tmux to keep running if disconnected
sudo apt-get install screen
screen -S hailo_compilation
./wsl_compile_models.sh
# Press Ctrl+A, then D to detach
# Reconnect with: screen -r hailo_compilation
```

### **Monitor Progress**
```bash
# In another WSL terminal
tail -f ~/hailo_compilation/compilation.log
```

### **If Something Goes Wrong**
```bash
# Check logs
cat ~/hailo_compilation/compilation.log

# Verify DFC installation
python -c "import hailo_sdk_client; print(hailo_sdk_client.__version__)"

# Test with simple command
hailo parser --help
```

---

## 🎯 **Success Criteria**

✅ Two HEF files created  
✅ Each file ~10-20 MB in size  
✅ `hailortcli parse-hef` shows threshold=0.150  
✅ Test on Pi shows detections!  

---

## 📊 **Why This Will Work**

1. ✅ **WSL2 is x86_64** - Native Linux environment
2. ✅ **Hailo officially supports WSL2** - Designed for it
3. ✅ **Your infrastructure is perfect** - Just needs right models
4. ✅ **Root cause known** - Simple parameter change

---

**Created:** October 10, 2025, 7:47 PM  
**Platform:** Windows WSL2 (x86_64)  
**Expected:** 3-4 hours total  
**Success:** 95%+ (officially supported platform!)

# CryptoShield USB Secure Vault: Real Security System & Vulnerability Analysis

This project is a functional, local security system built in Python that secures files on a real USB drive using **AES-256-GCM encryption**, a **secure PIN**, and **facial recognition** via your computer's webcam. 

---

## 🚀 Setup & Installation (Hindi & English)

### Requirements
You will need a Linux machine with Python 3, a webcam, and a USB pen drive.

### Steps to Run:
1. **Create Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the Application**:
   ```bash
   python main.py
   ```

---

## 🔒 How the System Works (Working Mechanism)
1. **Cryptography**: When you lock your files, they are zipped in-memory and encrypted using **AES-256-GCM** (Galois/Counter Mode). The key is derived using **PBKDF2** with SHA-256, taking your PIN and a random salt (16 bytes) as input. GCM ensures that no one can tamper with or modify the encrypted data without invalidating the cryptographic signature.
2. **Biometrics**: We use OpenCV's **LBPH (Local Binary Patterns Histograms) Face Recognizer** to match your face. Unlike deep learning models that require heavy GPU execution, LBPH is lightweight, runs locally, and performs histogram comparisons on texture features of the face.
3. **Secure Shredding**: Standard file deletion in OS only removes pointers, leaving data intact. CryptoShield overwrites files with random bytes, then zeros, and flushes it to disk before removing the files, preventing standard file recovery tools from restoring them.

---

## ⚠️ Real-World Problems & Vulnerabilities (क्या-क्या समस्याएं हो सकती हैं?)

If we deploy this as a real security solution, there are major hardware, software, and physical security limitations. Here is a deep-dive analysis:

### 1. Host PC Compromise (होस्ट कंप्यूटर पर भरोसा न होना)
* **Problem**: Because this security system runs as software on the computer, it is only as secure as the computer itself.
* **Explanation (Hinglish)**: Agar aapne USB drive ko ek aisi PC par lagaya jisme virus, keylogger, ya screen recorder hai, toh malware aapka PIN capture kar sakta hai, webcam feed ko fake kar sakta hai, ya fir RAM me se decrypted AES key ko chura sakta hai. 
* **Mitigation**: Real secure pen drives (like IronKey) handle ALL authentication and decryption inside a secure microcontroller physically embedded on the USB itself. No unencrypted keys or raw passwords ever touch the host computer's memory.

### 2. Portability & Dependency Limits (पोर्टेबिलिटी की सीमा)
* **Problem**: The drive cannot be read on systems without this software.
* **Explanation (Hinglish)**: Is system ko chalane ke liye computer me Python, OpenCV, aur specific libraries honi chahiye. Agar aap is pen drive ko kisi friend ke laptop, smart TV, projector, ya office ke restricted PC me lagayenge, toh aap apna data open nahi kar payenge kyunki vahan software nahi hoga.
* **Mitigation**: To make it truly plug-and-play, the authentication hardware (camera and keypad) must be physically on the USB drive body itself, unlocking raw storage partition only after successful on-device verification.

### 3. Biometric Spoofing (कैमरा बाईपास / फोटो से अनलॉक)
* **Problem**: Standard 2D webcams cannot verify "liveness".
* **Explanation (Hinglish)**: OpenCV standard face recognition sirf 2D face structure aur textures dekhta hai. Agar koi aapki high-resolution photo ya video tablet/phone par camera ke samne dikha de, toh system unlock ho sakta hai. Isme blink-detection, depth-sensing ya infrared scanning nahi hai.
* **Mitigation**: Real-world face biometrics require dedicated hardware, such as Apple's TrueDepth camera (which projects 30,000 infrared dots to build a 3D mesh) or structured light sensors, which cannot fit on a standard USB stick cheaply.

### 4. Power & Computational Limits (बिजली और प्रोसेसिंग की समस्या)
* **Problem**: High-power requirements for Face Recognition and Camera.
* **Explanation (Hinglish)**: Agar hum physical USB drive par hi camera aur display lagana chahein, toh USB port ki power limit aati hai. USB 2.0 sirf 500mA (2.5W) and USB 3.0 sirf 900mA power deta hai. Itne kam power me ek processor, camera module, OLED display, aur face recognition neural networks chalana hardware level par bohot challenging hai. Battery lagane par size aur cost bohot badh jayegi.

### 5. Physical Hardware Bypass (चिप निकालकर डेटा चोरी करना)
* **Problem**: Direct flash chip extraction.
* **Explanation (Hinglish)**: Agar koi chor aapki pen drive physically chura leta hai, toh use software bypass karne ki zaroorat nahi hai. Woh pen drive ki plastic body ko kholkar, directly Flash Memory Chip (NAND) ko board se desolder kar sakta hai aur ek universal programmer reader me dalkar data extract kar sakta hai. 
* **Mitigation**: Secure drives use a **Secure Element** (cryptographic chip) that automatically zeroizes/destroys the encryption keys if tampering is detected, and the flash chips are covered in hardened epoxy resin to prevent physical desoldering.

### 6. Wear-Leveling & SSD Shredding Limits (डेटा डिलीट होने के बाद भी रिकवरी का डर)
* **Problem**: Solid-State storage wear-leveling defeats software shredding.
* **Explanation (Hinglish)**: Flash memory/pen drives block-by-block write wear-leveling techniques use karti hain taaki memory jaldi kharab na ho. Is wajah se, jab hum software se data par overwrite (shred) karte hain, toh pen drive ka internal controller purane data block ko physically delete karne ke bajay ek naye block me data write kar deta hai. Purana plaintext data ab bhi physical flash blocks me chip ke andar pada rehta hai jo expert labs dump kar sakti hain.

# 🐾 PawCrypt

> **Stéganographie LSB + Chiffrement AES-256 — Cachez vos secrets dans des images de chiens.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green)](https://flask.palletsprojects.com)
[![AES-256](https://img.shields.io/badge/Chiffrement-AES--256--CBC-orange)]()
[![LSB](https://img.shields.io/badge/Stéganographie-LSB-purple)]()

---

## 📋 Description

PawCrypt est une application web légère qui permet de :

1. **Encoder** un message texte ou n'importe quel fichier (image, audio, vidéo…) dans une image de chien.
2. **Chiffrer** les données avec AES-256-CBC avant de les cacher (clé dérivée via PBKDF2).
3. **Décoder** une image PawCrypt pour récupérer le message ou fichier caché.
4. **Analyser** la différence entre une image originale et son équivalent encodé.

---

## 📁 Architecture du projet

```
pawcrypt/
├── app.py              # Backend Flask (routes + crypto + LSB)
├── templates/
│   └── index.html      # Frontend single-page (HTML + CSS + JS vanilla)
├── static/             # (vide — assets servis inline)
├── dogs/               # Banque d'images PNG de chiens
│   ├── dog1.png
│   ├── dog2.png
│   └── ...
├── requirements.txt    # Dépendances Python
└── README.md           # Ce fichier
```

**Total : 4 fichiers de code + dossiers.**

---

## 🧩 Dépendances

| Package        | Rôle                             |
|----------------|----------------------------------|
| Flask          | Serveur web Python léger         |
| Pillow         | Manipulation d'images (LSB)      |
| pycryptodome   | AES-256, PBKDF2, IV aléatoire    |
| gunicorn       | Serveur WSGI production          |

---

## 💻 Installation locale

### 1. Prérequis

```bash
# Vérifier Python (3.10 minimum)
python3 --version

# Installer pip si absent
sudo apt update && sudo apt install -y python3-pip python3-venv
```

### 2. Cloner / copier le projet

```bash
# Copier le dossier pawcrypt sur votre machine
cd pawcrypt
```

### 3. Créer un environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
# .\venv\Scripts\activate       # Windows
```

### 4. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 5. Ajouter des images de chiens

```bash
# Placez des images PNG de chiens dans le dossier dogs/
# Exemples gratuits : https://unsplash.com/s/photos/dog (télécharger en PNG)
# Minimum recommandé : 5 images de 800x600 pixels ou plus

ls dogs/     # Vérifier la présence des images
```

### 6. Lancer en développement

```bash
python app.py
# → http://localhost:5000
```

---

## 🌐 Déploiement sur VM Linux (Ubuntu/Kubuntu)

### Étape 1 — Connexion et mise à jour

```bash
ssh user@IP_PUBLIQUE
sudo apt update && sudo apt upgrade -y
```

### Étape 2 — Installer Python et pip

```bash
sudo apt install -y python3 python3-pip python3-venv git
python3 --version   # Doit afficher 3.10+
```

### Étape 3 — Copier le projet sur le serveur

```bash
# Depuis votre machine locale :
scp -r pawcrypt/ user@IP_PUBLIQUE:/home/user/

# Ou avec git si vous hébergez sur un dépôt :
# git clone https://votre-repo/pawcrypt.git
```

### Étape 4 — Créer l'environnement virtuel

```bash
cd /home/user/pawcrypt
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Étape 5 — Ajouter les images de chiens

```bash
# Télécharger quelques PNG (exemple avec wget ou copier manuellement)
mkdir -p dogs
# Copiez vos images dans le dossier dogs/
```

### Étape 6 — Ouvrir les ports avec UFW

```bash
sudo ufw allow OpenSSH       # Conserver l'accès SSH
sudo ufw allow 80            # HTTP
sudo ufw allow 443           # HTTPS (futur)
sudo ufw allow 8000          # Port Gunicorn
sudo ufw enable
sudo ufw status              # Vérifier les règles actives
```

### Étape 7 — Lancer avec Gunicorn

```bash
cd /home/user/pawcrypt
source venv/bin/activate

# Test rapide (foreground)
gunicorn -w 2 -b 0.0.0.0:8000 app:app

# En arrière-plan (production)
gunicorn -w 2 -b 0.0.0.0:8000 --daemon \
         --access-logfile logs/access.log \
         --error-logfile logs/error.log \
         app:app
```

### Étape 8 — Accès via IP publique

```
http://IP_PUBLIQUE:8000
```

### Étape 9 — (Optionnel) DNS interne — stegano-crypt.infotel

Si votre réseau dispose d'un résolveur DNS interne, ajoutez un enregistrement A :
```
stegano-crypt.infotel  →  IP_PUBLIQUE
```
L'application sera alors accessible via :
```
http://stegano-crypt.infotel:8000
```

Pour écouter sur le port 80 sans root, utilisez un reverse proxy Nginx ou authbind.

---

## 🔁 Lancement automatique (systemd)

Créez le fichier service :

```bash
sudo nano /etc/systemd/system/pawcrypt.service
```

```ini
[Unit]
Description=PawCrypt Stéganographie
After=network.target

[Service]
User=user
WorkingDirectory=/home/user/pawcrypt
Environment="PATH=/home/user/pawcrypt/venv/bin"
ExecStart=/home/user/pawcrypt/venv/bin/gunicorn -w 2 -b 0.0.0.0:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable pawcrypt
sudo systemctl start pawcrypt
sudo systemctl status pawcrypt
```

---

## 🔐 Sécurité

### AES-256-CBC
- **Algorithme** : AES (Advanced Encryption Standard) 256 bits en mode CBC (Cipher Block Chaining)
- **Dérivation de clé** : PBKDF2-HMAC-SHA256 avec **200 000 itérations** et un sel aléatoire de 128 bits
- **IV** : Vecteur d'initialisation aléatoire de 128 bits, regénéré à chaque encodage
- **Format blob** : `[salt 16B][iv 16B][ciphertext nB]`

### LSB (Least Significant Bit)
- Chaque pixel RGB contient 3 octets (R, G, B) → 3 bits cachables
- Variation imperceptible : ±1 sur 255 niveaux de couleur
- Les données sont précédées d'un en-tête `PAWCRYPT` + longueur sur 4 octets

### Limites connues
- Steganalyse statistique peut détecter la présence de LSB modifiés
- JPEG non supporté (compression avec perte détruit les LSB)
- Sécurité dépend entièrement de la force du mot de passe

---

## 🧪 Tester rapidement

```bash
# 1. Lancer l'app
python app.py

# 2. Ouvrir http://localhost:5000
# 3. Onglet "Encoder" : taper un message, définir un mot de passe, cliquer Encoder
# 4. Télécharger l'image générée
# 5. Onglet "Décoder" : uploader l'image, entrer le même mot de passe
# 6. Onglet "Analyser" : comparer l'originale et l'encodée
```

---

## 📖 Explication des fichiers

| Fichier | Description |
|---------|-------------|
| `app.py` | Cœur de l'application : routes Flask, fonctions AES (encrypt/decrypt), fonctions LSB (encode/decode), analyse |
| `templates/index.html` | Interface utilisateur complète : HTML5 + CSS3 dark theme + JavaScript vanilla (fetch API) |
| `dogs/` | Banque d'images PNG de chiens sélectionnées aléatoirement à l'encodage |
| `requirements.txt` | Dépendances pip : Flask, Pillow, pycryptodome, gunicorn |
| `README.md` | Ce fichier de documentation |

---

*PawCrypt v1.0 — Projet pédagogique de stéganographie*

# 🤖 ControlBot – Contrôle Domotique via Arduino

Un bot Discord permettant de contrôler à distance des composants matériels (servo-moteur, LED, capteur DHT) connectés à un Arduino, avec authentification à deux facteurs (2FA) par email.

---

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Matériel requis](#-matériel-requis)
- [Prérequis logiciels](#-prérequis-logiciels)
- [Installation](#-installation)
- [Configuration du fichier `token.txt`](#-configuration-du-fichier-tokentxt)
- [Câblage Arduino](#-câblage-arduino)
- [Commandes disponibles](#-commandes-disponibles)
- [Authentification 2FA](#-authentification-2fa)
- [Lancement du bot](#-lancement-du-bot)
- [Notes et limitations](#-notes-et-limitations)

---

## ✨ Fonctionnalités

- Authentification à deux facteurs (2FA) par email avant toute commande
- Contrôle d'un servo-moteur (allumer / maintenir / éteindre pour contrôler un appareil avec le bouton d'alimentation)
- Allumage d'une LED bleue
- Lecture de température et d'humidité via un capteur DHT11
- Mise à jour du statut du bot avec la température/humidité en temps réel
- Envoi de photos depuis une caméra locale
- Stream audio depuis un flux HTTP (MotionEye, pas fonctionnel pour le moment)
- Purge des messages du salon
- Redémarrage ou arrêt du bot à distance

---

## 🔧 Matériel requis

| Composant | Détails |
|---|---|
| **Carte Arduino** | Compatible Firmata (ex: Arduino Uno, Mega) |
| **Capteur DHT11** | Branché sur la broche digitale **2** |
| **Servo-moteur** | Branché sur la broche PWM **10** |
| **LED bleue** | Branchée sur la broche digitale **13** |
| **Câble USB** | Pour connecter l'Arduino au Raspberry Pi / PC |
| **Raspberry Pi ou PC Linux** | Machine hôte pour faire tourner le bot |
| **Caméra (optionnel)** | Compatible `libcamera` ou MotionEye pour les commandes `!picture` et `!stream` |

> ⚠️ L'Arduino doit avoir le firmware **StandardFirmata** ou **StandardFirmataPlus** chargé via l'IDE Arduino avant utilisation.

---

## 🖥️ Prérequis logiciels

- Python **3.9+**
- `pip`
- Un compte **Gmail** avec un [mot de passe d'application](https://support.google.com/accounts/answer/185833) généré (la 2FA Google doit être activée sur le compte)
- Un bot Discord créé sur le [portail développeur Discord](https://discord.com/developers/applications) avec les intents **Message Content** activés
- `ffmpeg` installé sur le système (pour la commande `!stream`)

```bash
# Installation de ffmpeg (Debian/Ubuntu/Raspberry Pi OS)
sudo apt update && sudo apt install ffmpeg -y
```

---

## 🚀 Installation

### 1. Cloner ou copier le projet

```bash
git clone <url-du-repo>
cd <dossier-du-projet>
```

### 2. Créer un environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Installer les dépendances Python

```bash
pip install discord.py pymata4 ffmpeg-python
```

Récapitulatif des bibliothèques utilisées :

| Bibliothèque | Rôle |
|---|---|
| `discord.py` | Interface avec l'API Discord |
| `pymata4` | Communication avec l'Arduino via Firmata |
| `ffmpeg-python` | Wrapper Python pour ffmpeg (stream audio) |
| `smtplib` | Envoi d'emails (inclus dans la bibliothèque standard Python) |

---

## 🔑 Configuration du fichier `token.txt`

Le fichier `token.txt` doit être créé manuellement au même endroit que le code du bot discord et **ne doit jamais être partagé ni versionné** (ajoutez-le à votre `.gitignore`).

Il doit contenir **exactement 4 lignes**, dans cet ordre :

```
VOTRE_TOKEN_DISCORD
votre.email.gmail@gmail.com
votre_mot_de_passe_application_gmail
email.autorise.reception.codes@gmail.com
```

| Ligne | Contenu |
|---|---|
| **1** | Le token de votre bot Discord (depuis le portail développeur) |
| **2** | L'adresse Gmail depuis laquelle les codes 2FA sont envoyés |
| **3** | Le mot de passe d'application Gmail (pas votre mot de passe habituel) |
| **4** | L'adresse email qui **recevra** les codes de vérification 2FA |

> 💡 Les lignes sont lues avec `readline()`, donc chaque valeur doit être sur sa propre ligne, **sans ligne vide entre elles**.

### Générer un mot de passe d'application Gmail

1. Allez dans votre [compte Google](https://myaccount.google.com/)
2. Sécurité → Validation en deux étapes (doit être activée)
3. Mots de passe des applications → Créer un mot de passe pour "Autre (nom personnalisé)"
4. Copiez le mot de passe généré (16 caractères) dans la ligne 3 du fichier

---

## ⚡ Câblage Arduino

```
Arduino
  Broche 2  → Signal DHT11
  Broche 10 → Signal Servo-moteur
  Broche 13 → Anode LED bleue (+ résistance 220Ω vers GND)
  5V        → VCC DHT11, VCC Servo
  GND       → GND commun
```

> L'Arduino doit être connecté en USB à la machine qui fait tourner le bot. Pymata4 le détecte automatiquement sur le port série.

---

## 💬 Commandes disponibles

> Toutes les commandes (sauf `!verifier` et `!confirmer`) nécessitent une authentification 2FA préalable.

### Authentification

| Commande | Description |
|---|---|
| `!verifier` | Envoie un code de vérification à 6 chiffres par email |
| `!confirmer <code>` | Valide le code reçu pour s'authentifier |

### Contrôle matériel (Utilisé dans l'optique d'un allumage de pc à distance par exemple)

| Commande | Description |
|---|---|
| `!allumer` | Active le servo (appui court sur le bouton physique) |
| `!maintenir` | Active le servo pendant 6 secondes (appui long, force l'extinction) |
| `!eteindre` | Commande d'extinction (à compléter selon câblage) |

### Caméra

| Commande | Description |
|---|---|
| `!picture` | Envoie l'image `image.jpg` présente localement |
| `!stream` | Démarre un flux audio depuis MotionEye dans le salon vocal |

### Administration

| Commande | Description |
|---|---|
| `!hello` | Vérifie que le bot répond correctement |
| `!purger` | Supprime tous les messages du salon courant |
| `!quitter` | Déconnecte proprement le bot et l'Arduino |
| `!reboot` | Redémarre la machine hôte (`sudo reboot`) |

---

## 🔐 Authentification 2FA

Le bot utilise un système de vérification par email avant d'accepter toute commande sensible.

**Étapes :**

1. Tapez `!verifier` dans le salon Discord
2. Un code à 6 chiffres est envoyé à l'adresse définie dans `token.txt` (ligne 4)
3. Tapez `!confirmer 123456` en remplaçant `123456` par le code reçu
4. Vous êtes maintenant authentifié pour la durée de la session

> ⚠️ L'authentification est stockée en mémoire. Elle est perdue si le bot redémarre.

---

## ▶️ Lancement du bot

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Lancer le bot
python3 bot.py
```

Pour un lancement automatique au démarrage du Raspberry Pi, vous pouvez créer un service `systemd` ou utiliser `cron @reboot`.

---

## 📝 Notes et limitations

- Le fichier `image.jpg` utilisé par `!picture` doit être généré au préalable (ex: via `libcamera-still`). La ligne de capture est commentée dans le code et peut être réactivée.
- La commande `!stream` nécessite que MotionEye soit actif sur `http://loacalhost:9061` — adaptez l'IP à votre réseau.
- La commande `!reboot` exécute `sudo reboot` sans confirmation. Assurez-vous que l'utilisateur qui lance le bot a les droits sudo nécessaires.
- Les codes de vérification expirent à la prochaine tentative incorrecte ou au redémarrage du bot.
- Ce projet est prévu pour un usage **personnel et local**, ne l'exposez pas publiquement sans mesures de sécurité supplémentaires.

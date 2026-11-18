🚬 AntiCroissantage
===================

Un faux bureau verrouillé, pour que personne ne te fasse payer les croissants quand tu quittes ton poste.

Un raccourci clavier affiche ton vrai bureau en direct en plein écran, clavier et clics bloqués. Pour un collègue, le PC est juste figé. Toi, tu reviens, tu fais **AltGr + H** et la vraie session Windows se verrouille (mot de passe demandé).

> 🥐 Un projet de blague, pas une sécurité : voir les [limites](#️-limites).

![Le paquet](docs/paquet.png)

### 📖 Concept du projet

Pour le collègue :

- Ton bureau en direct, sur tous les écrans : vidéo, horloge, fenêtres qui bougent et notifications continuent de défiler, mais rien ne répond.
- Le curseur bouge normalement, mais rien ne répond.
- Un clic fait apparaître un paquet « Ceci n'est pas une clope ». Chaque clic dessus consume la clope un peu plus, avec un nouveau message, et une fumée suit le curseur.
- Le menu Démarrer s'ouvre (c'est le vrai, vu sous le faux bureau) et la recherche répond, mais rien ne peut être lancé.

Pour toi, à ton retour : après ton mot de passe, un **tableau de chasse** résume les tentatives (clics, touches, première et dernière heure).

## 🚀 Installation

Il te faut Windows 10 ou 11 (version 2004 minimum) et Python 3. Rien d'autre : le projet n'utilise que `ctypes`.

1. Clone le dépôt.
2. Crée le raccourci sur le Bureau :

   ```powershell
   .\installer-raccourci.ps1
   ```

3. Appuie sur **Ctrl + Alt + L** pour verrouiller. Pour une autre touche : `.\installer-raccourci.ps1 -Touche "CTRL+SHIFT+F12"`.

## 🕹️ Utilisation

| Commande | Effet |
| --- | --- |
| `Ctrl + Alt + L` | Verrouille avec le faux bureau (le raccourci du Bureau) |
| `AltGr + H` | Retire le faux bureau, puis verrouille vraiment Windows |
| `python anticroissantage.py --timeout 20 --nolock` | Test sans risque : se déverrouille seul après 20 s, sans verrouiller la session |
| `--fige` | Ancien comportement : photo figée (seuls la barre des tâches et le menu bougent), charge quasi nulle |
| `--fps N` | Images par seconde visées en direct (20 par défaut) |
| `--mesure` | Affiche à la fin les images par seconde et la charge CPU |

⚠️ Pour tout essai, garde toujours `--timeout` : le programme bloque clavier et souris.

## 🌳 Structure du projet

```
├── anticroissantage.py       # le programme : fenêtres, clavier et souris, menu miroir, tableau de chasse
├── clope.py                  # les dessins : paquet, clope qui se consume, fumée, tableau
├── winapi.py                 # déclarations de l'API Windows (ctypes)
├── tests/                    # tests hors écran (python -m unittest discover tests) et mesure (tests/bench.py)
├── installer-raccourci.ps1   # crée le raccourci « Verrouiller » sur le Bureau
└── docs/                     # image du README
```

Quelques repères pour débuter :

- Le faux bureau est une fenêtre par écran. Une capture `BitBlt` de tout le bureau virtuel est refaite ~20 fois par seconde ; nos fenêtres sont exclues des captures (`WDA_EXCLUDEFROMCAPTURE`), donc on voit le vrai bureau en dessous.
- Les touches et les clics sont interceptés par deux « hooks » Windows : `keyboard_hook` et `mouse_hook`.
- Le vrai menu Démarrer s'ouvre sous nos fenêtres et apparaît dans la capture. Avec `--fige`, une copie en direct en est affichée.
- Les vraies fenêtres ne reçoivent rien : la souris ne leur arrive pas (notre fenêtre les recouvre) et les hooks avalent clics, molette et touches.

## ⚠️ Limites

- **Ctrl + Alt + Suppr** ne peut pas être bloqué : quelqu'un qui connaît ce raccourci sort du faux bureau.
- Mesures sur un écran 1920×1080 (une seule machine) : une capture coûte ~30 ms (dont ~8 ms de CPU), soit environ 13 images/s réelles pour 14 % d'un cœur avec `--fps 20` ; 21 images/s pour 22 % avec `--fps 30`. La fluidité d'une vidéo reste donc moyenne ; `--fige` ramène la charge à ~1 %.
- Le tactile et le stylet ne passent pas par les hooks clavier/souris, mais ils tombent sur notre fenêtre et pas sur le vrai bureau.
- Le contenu protégé contre la capture (certaines vidéos DRM) apparaît noir.
- Ne l'utilise que sur ton propre poste, entre collègues qui ont de l'humour.

---

Créé pour rigoler à la pause café. 🥐

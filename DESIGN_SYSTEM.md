# Design System Ekko (Coucou / OLED Dark Mode)

Ce document formalise les tokens visuels, la géométrie adaptative, les conventions graphiques et la physique d'animation du Desktop Pod d'Ekko selon les standards du Design System Coucou.

---

## 1. Palette Chromatique & Surfaces (OLED Dark Mode)

| Token | Valeur Hex / CSS | Usage |
|---|---|---|
| **Fond Principal** | `#0c0c0e` | Fond absolu du Pod (noir profond OLED, coque extérieure) |
| **Surface Surélevée** | `#141824` / `#161b26` | Cartouche intérieure, tuiles Bento, cartes, bulles |
| **Bordure Subtile** | `rgba(255, 255, 255, 0.08)` / `#14ffffff` | Contour structurel des conteneurs et de la coque |
| **Bordure Active** | `rgba(56, 189, 248, 0.4)` / `#38bdf8` | Survol drag & drop, focus saisie, état sélectionné |
| **Cyan Rayonnant** | `#00f2fe` | Halo de pulsation d'ambiance de la mascotte |
| **Bleu Électrique** | `#38bdf8` | Contour vectoriel, mains satellites, accents, jauges |
| **Bleu Profond** | `#0284c7` vers `#1e3a8a` | Dégradé vertical du corps de la mascotte |
| **Succès Émeraude** | `#10b981` | Pastille daemon connecté, validation in-place, badges |
| **Alerte Écarlate** | `#ef4444` / `#f87171` | Pastille déconnectée, bannières d'erreur |

---

## 2. Géométrie & Structure du Pod (Format Horizontal & Adaptatif)

Le Pod abandonne les formats verticaux rigides au profit d'un format horizontal ergonomique à géométrie adaptative :

### 2.1 Dimensions Adaptatives
- **Mode Compact (Welcome & Home) :** `620px` (largeur) × `230px` (hauteur).
  - Empreinte ultra-discrète, ancrée en périphérie visuelle sans encombrer l'espace de travail.
- **Mode Étendu (Chat, Écho, Réglages) :** `620px` (largeur) × `460px` (hauteur).
  - Déploiement fluide vers le bas pour accueillir le flux conversationnel, la liste des notes PKM ou la configuration.

### 2.2 Conception à Double Coque Top-Docked & Scène Unique (Stage)
- **Coque extérieure (Encoche / Îlot sommital) :**
  - Fond noir absolu `#0c0c0e`.
  - Ancrage sommital sans bordure ni courbure supérieure : `rounded-t-none rounded-b-[26px]`.
  - Bordures : `border-x border-b border-white/[0.08] border-t-0` (continuité absolue avec le bandeau supérieur de l'OS).
  - Ombre portée diffuse vers le bas `shadow-2xl` avec confinement transparent (`backgroundColor: '#00000000'`).
  - Padding extérieur : `10px` (`p-2.5`).
- **Scène Unique Commune (Stage intérieur) :**
  - Fond unique `#141824` / `#161b26` surélevé et continu.
  - Rayon `rounded-2xl` (`16px`), bordure fine `border border-white/[0.08]` et ombre portée diffuse `shadow-inner`.
  - Hauteur calée sur l'espace disponible sous le header de 32 px (hauteur utile ~172 px en mode compact 230 px).
  - **Réceptacle commun unique :** Toutes les vues (`Welcome`, `Home`, `Chat`, `Echo`, `Settings`) s'insèrent directement dans ce Stage. Proscription des sous-cartes opaques empilées.

### 2.3 Bandeau Supérieur Permanent (Header Compact 32px)
Hauteur fixe de `32px` (`h-8`) assurant la navigation rapide et le contrôle de l'application :
- **À gauche (Navigation Principale) :**
  - Icônes Lucide nettes de `15px` (`size={15}`) dans des boîtes de clic ergonomiques `28×28px` (`w-7 h-7 rounded-lg`).
  - Onglet actif : fond dépoli subtil `bg-white/[0.08] text-sky-400`.
  - Onglet inactif : `text-slate-400 hover:text-slate-200 hover:bg-white/[0.06]`.
  - Accueil (💧) : vue principale Bento.
  - Chat (💬) : dialogue direct et assistant ReAct.
  - Écho (⚡) : consultation du flux des fiches distillées.
- **À droite (Système & Contrôle) :**
  - Réglages (⚙️) : panneau des veilleurs, profils BYOM et socket IPC.
  - Pastille d'état réseau : diamètre discret de `6px` (`w-1.5 h-1.5`, `#10b981` connecté, `#ef4444` hors ligne).
  - Fermer (✕) : bouton de repli immédiat de la fenêtre (`w-7 h-7 rounded-lg`).

---

## 3. Mascotte Vectorielle Ekko & Matrice des 7 Micro-Émotions

La mascotte incarne le tampon cognitif sous la forme d'une goutte d'eau fluide en poire :
1. **Silhouette principale :**
   - Tracé SVG continu avec courbe de Bézier : sommet fuselé (`M 50 10`) et base élargie bienveillante (`C 70 32, 92 64, 92 86...`).
   - Remplissage par dégradé vertical : Cyan `#00f2fe` (sommet) vers Bleu profond `#1e3a8a` (base).
2. **Mains satellites détachées :**
   - Deux disques de `14px` de diamètre flottant à `8px` de distance de part et d'autre du corps.
   - Micro-animations de flottaison en opposition de phase.
3. **Matrice des 7 Micro-Émotions Réactives :**
   - `idle` : repos et veille nominale, yeux fermés en courbes douces vers le haut (`‿ ‿`), respiration lente ($T = 3.2\text{s}$) et micro-particule de sommeil « z » flottante.
   - `welcome` : réveil bienveillant, coucou avec la main satellite droite et regard pétillant (déclenchée pendant les 1,8 s d'amorce).
   - `hover_drop` : réveil attentif, yeux écarquillés suivant la trajectoire du fichier, halo cyan intensifié ($0.35 \leftrightarrow 0.50$).
   - `ingesting` : déformation élastique squash & stretch ($T = 0.9\text{s}$), bouche en « O » absorbant un micro-document néon qui descend et se dissout dans l'orifice.
   - `ready` : sourire bienveillant avec halo émeraude `COLORS.emeraldOnline` validant l'arrivée de la note dans la base locale (persiste 2 s).
   - `alert` : réveil soudain avec micro-sursaut vertical ($y \in [0, -4, 0]$ sur 200 ms), regard naturellement orienté vers la droite (+3 px sur X) vers la carte de veille, sourcils interrogateurs et halo ambré chaleureux `COLORS.amberGlow`.
   - `error` : secousse de tête latérale vive (*head shake*, $x \in [0, -6, 6, -4, 4, 0]$ sur 350 ms), yeux plissés, moue contrariée et halo corail feutré (`rgba(244, 63, 94, 0.25)`). Rétablissement automatique à l'état `idle` après 2,5 s.
4. **Regard Interactif & Suivi Oculaire :**
   - En état `idle`, les paupières restent closes et le suivi est désactivé.
   - Lorsque la mascotte est éveillée (`hover_drop`, `ready`, ou survol du volet gauche), les pupilles suivent doucement les coordonnées du curseur utilisateur, avec un déplacement fluide borné dans un cercle de rayon $R = 3.5\text{px}$ (`dx, dy = clamp(delta * factor, -3.5, 3.5)`).

---

## 4. Organisation du Home & Métamorphose de Survol (Stage Unique)

À l'intérieur du Stage unique (620×230 px), l'espace est organisé en un layout split horizontal sans sous-boîtes opaques, structuré par la respiration de l'espace négatif (`gap-4`) sans barre de séparation verticale :

### 4.1 Volet Gauche — Mascotte Vectorielle Épurée (~36 % / ~215 px)
- Mascotte Ekko flottant au centre géométrique et optique du tiers gauche (`flex items-center justify-center h-full`).
- Halo d'ambiance cyan pulsé `#00f2fe` et mains satellites détachées sans aucun écrêtage ni bordure de contrainte.
- Gabarit SVG calibré (~88 px de hauteur) offrant une respiration élégante et équilibrée avec ~42 px de marge en haut et en bas.
- **Zéro étiquette textuelle :** La mascotte communique son état exclusivement par ses expressions vectorielles (regard, sourire, déglutition, pulsations vives). L'intégralité du retour textuel opérationnel est pris en charge par le volet droit.
- Zéro texte parasite, présence vivante pure et minimaliste.

### 4.2 Volet Droit — Espace Réactif Métamorphe (62 % / ~360 px)
Le volet droit bascule dynamiquement entre l'état de repos et l'état de capture :
1. **État 1 : Au repos (Option A — Split 65/35) :**
   - **Partie supérieure (~65 %) :** invitation au drop délimitée par un cadre en pointillés fins (`border border-dashed border-white/10 rounded-xl hover:border-sky-400/40 hover:bg-white/[0.02]`), icône discrète d'upload et libellé clair : *"Glisser un document ou une URL"*. Clic ouvrant l'explorateur de fichiers.
   - **Partie inférieure (~35 %) :** ligne "Dernier Écho" posée à plat (`bg-white/[0.02] hover:bg-white/[0.05] border border-white/[0.06] hover:border-sky-400/30`), surtitre compact "DERNIER ÉCHO", titre de note tronqué proprement et chevron de navigation (`ArrowRight`).
2. **État 2 : Au survol de fichier (Option B — Plein cadre 62 %) :**
   - Dès qu'un fichier survole la zone (dragenter/dragover), la séparation interne droite s'efface au profit d'une zone d'absorption plein cadre sur les 62 % du volet.
   - Contour illuminé en cyan doux (`border border-dashed border-sky-400/60 bg-sky-500/[0.04] rounded-xl`).
   - Mascotte en émotion `hover_drop`.
   - Message centré et aéré : *"Relâcher pour absorber"*.
3. **État 3 : En cours de distillation (async) :**
   - Affichage de l'état d'absorption sans déborder : troncature centrale du nom de fichier (ex. `Distillation de attention_is...need.pdf en cours...`), spinner et pulsation lumineuse.
   - Mascotte en émotion `ingesting`.
4. **État 4 : Succès réel (arrivée de la note dans SQLite) :**
   - Teinte d'ambiance émeraude subtile (`bg-emerald-500/[0.04] border border-emerald-500/30 rounded-xl`), mascotte souriante (`ready`).
   - Mise à jour instantanée de la ligne "Dernier Écho" et retour doux à l'état de repos.
5. **Déport Télémétrie :**
   - Les informations techniques (VRAM, `nice +10`, veilleurs, `/tmp/ekko.sock`) sont exclusivement affichées dans l'onglet Réglages (⚙️).

---

## 5. Physique d'Animation (Framer Motion Tokens)

```typescript
// Transitions vives pour les micro-interactions, onglets et boutons
export const SPRING_SNAPPY = {
  type: "spring" as const,
  stiffness: 400,
  damping: 30,
  mass: 0.8,
};

// Transitions douces avec rebond pour la mascotte, les ouvertures et le redimensionnement
export const SPRING_BOUNCY = {
  type: "spring" as const,
  stiffness: 260,
  damping: 20,
  mass: 1.0,
};

// Séquençage temporel de l'amorce
export const WELCOME_DURATION_MS = 1800;
```


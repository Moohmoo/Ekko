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

### 2.2 Conception à Double Coque (Surface Coucou)
- **Coque extérieure :**
  - Fond noir absolu `#0c0c0e`.
  - Courbure prononcée `rounded-[28px]`.
  - Bordure subtile `border border-white/[0.08]`.
  - Ombre portée diffuse `shadow-2xl` avec confinement transparent (`backgroundColor: '#00000000'`).
- **Cartouche intérieure (Panneau flottant) :**
  - Fond `#141824` / `#161b26` surélevé.
  - Rayon `rounded-2xl` (`16px`) créant un relief élégant et doux.
  - Padding interne calibré (12px à 16px) pour maximiser la densité sans effet d'étouffement.

### 2.3 Bandeau Supérieur Permanent (Header 40px)
Hauteur fixe de `40px` assurant la navigation rapide et le contrôle de l'application :
- **À gauche (Navigation Principale) :**
  - Accueil (💧) : retour à la vue Bento principale.
  - Chat (💬) : bascule vers le dialogue direct et l'assistant ReAct.
  - Écho (⚡) : consultation du flux des fiches distillées.
- **À droite (Système & Contrôle) :**
  - Réglages (⚙️) : panneau des veilleurs, profils BYOM et socket IPC.
  - Pastille d'état réseau : indicateur dynamique de liaison (`#10b981` connecté, `#ef4444` hors ligne).
  - Fermer (✕) : bouton de repli immédiat de la fenêtre.

---

## 3. Mascotte Vectorielle Ekko & Matrice des 5 Micro-Émotions

La mascotte incarne le tampon cognitif sous la forme d'une goutte d'eau fluide en poire :
1. **Silhouette principale :**
   - Tracé SVG continu avec courbe de Bézier : sommet fuselé (`M 50 10`) et base élargie bienveillante (`C 70 32, 92 64, 92 86...`).
   - Remplissage par dégradé vertical : Cyan `#00f2fe` (sommet) vers Bleu profond `#1e3a8a` (base).
2. **Mains satellites détachées :**
   - Deux disques de `14px` de diamètre flottant à `8px` de distance de part et d'autre du corps.
   - Micro-animations de flottaison en opposition de phase.
3. **Matrice des 5 Micro-Émotions Réactives :**
   - `welcome` : petit coucou avec la main satellite droite et regard joyeux (déclenchée pendant les 1,8 s d'amorce).
   - `idle` : respiration lente, yeux mi-clos apaisés, halo cyan doux en régime nominal.
   - `hover_drop` : yeux grands ouverts fixés sur le fichier, halo cyan intensifié dès le survol de la zone de glisser-déposer.
   - `ingesting` : absorption en cours (déglutition, pulsations vives et flux vers le bas).
   - `ready` : sourire bienveillant avec badge vert de succès à la fin d'une opération.

---

## 4. Spécification de la Grille Bento du Home (Layout Split)

En mode Home (620×230 px), l'espace est organisé en un layout split horizontal optimisé :

### 4.1 Volet Gauche — Capsule Mascotte (40 % / ~240 px)
- Conteneur vertical centré accueillant la mascotte vectorielle.
- Halo d'ambiance cyan pulsé `#00f2fe`.
- Indicateur textuel discret de statut sous la mascotte (ex. *"Prêt à absorber"*, *"Veille active"*).

### 4.2 Volet Droit — Grille Bento 2×2 (60 % / ~360 px)
Une matrice de 4 tuiles ultra-denses fournissant un tableau de bord immédiat :
1. **Tuile 1 (Drop & Forget in-place) :**
   - Cadre récepteur avec bordure en pointillés (`border-dashed border-sky-400/30`).
   - Glisser-déposer in-place : survol réactif animant la mascotte en `hover_drop`.
   - Pendant l'ingestion, le cadre se transforme directement en jauge de progression in-place (pourcentage puis badge de distillation) sans quitter la vue Home.
2. **Tuile 2 (Veilleurs) :**
   - Moniteur d'activité des flux déclarés : pastilles d'état compactes pour arXiv, HackerNews et flux RSS.
   - Indicateur visuel d'activité récente (dernier poll, items scannés).
3. **Tuile 3 (Dernier Écho) :**
   - Pill horizontal compact résumant la dernière fiche distillée stockée dans la base de connaissances (`knowledge_notes`).
   - Clic ouvrant directement le détail dans l'onglet Écho.
4. **Tuile 4 (Télémétrie & Ressources) :**
   - Badges système compacts : VRAM GPU déchargée (`VRAM 0M`), priorité CPU (`nice +10`), et socket IPC actif (`/tmp/ekko.sock`).

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


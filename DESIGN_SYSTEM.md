# Design System Ekko (Coucou / OLED Dark Mode)

Ce document formalise les tokens visuels, les conventions graphiques et la physique d'animation du Desktop Pod d'Ekko.

---

## 1. Palette Chromatique & Surfaces (OLED Dark Mode)

| Token | Valeur Hex / CSS | Usage |
|---|---|---|
| **Fond Principal** | `#0c0c0e` | Fond absolu du Pod (noir profond OLED) |
| **Surface Surélevée** | `#141824` / `#161a24` | Cartes, bulles de dialogue, en-tête |
| **Bordure Subtile** | `rgba(255, 255, 255, 0.08)` / `#14ffffff` | Contour structurel des conteneurs |
| **Bordure Active** | `rgba(56, 189, 248, 0.4)` / `#38bdf8` | Survol drag & drop, focus saisie |
| **Cyan Rayonnant** | `#00f2fe` | Halo de pulsation d'ambiance de la mascotte |
| **Bleu Électrique** | `#38bdf8` | Contour vectoriel, mains satellites, accents |
| **Bleu Profond** | `#0284c7` vers `#1e3a8a` | Dégradé bas de corps de la mascotte |
| **Succès Émeraude** | `#10b981` | Pastille daemon connecté, validation |
| **Alerte Écarlate** | `#ef4444` / `#f87171` | Pastille déconnectée, bannières d'erreur |

---

## 2. Géométrie & Structure du Pod

- **Dimensions fixes :** `440px` (largeur) × `560px` (hauteur).
- **Courbure des angles :** `rounded-[28px]` pour le conteneur principal, `rounded-2xl` (`16px`) pour les sous-cartes internes.
- **En-tête iconographique :** `40px` de hauteur, minimaliste et sans texte, comprenant uniquement les icônes vectorielles et la pastille de connectivité.

---

## 3. Mascotte Vectorielle Ekko

La mascotte incarne le tampon cognitif sous la forme d'une goutte d'eau fluide en poire :
1. **Silhouette principale :**
   - Tracé SVG continu avec courbe de Bézier : sommet fuselé (`M 50 10`) et base élargie bienveillante (`C 70 32, 92 64, 92 86...`).
   - Remplissage par dégradé vertical : Cyan `#00f2fe` (sommet) vers Bleu profond `#1e3a8a` (base).
2. **Mains satellites détachées :**
   - Deux disques de `14px` de diamètre flottant à `8px` de distance de part et d'autre du corps.
   - Micro-animations de flottaison en opposition de phase.
3. **Regard expressif :**
   - Yeux sombres `#040814` en amande avec reflets blancs directionnels, positionnés bas sur le visage pour un caractère bienveillant.
4. **Lueur cyan d'ambiance :**
   - Halo circulaire `#00f2fe` flouté en arrière-plan avec pulsation lente de l'opacité et de l'échelle.

---

## 4. Physique d'Animation (Framer Motion Tokens)

```typescript
// Transitions vives pour les micro-interactions et sélecteurs d'onglets
export const SPRING_SNAPPY = {
  type: "spring" as const,
  stiffness: 400,
  damping: 30,
  mass: 0.8,
};

// Transitions douces avec rebond pour la mascotte et les ouvertures
export const SPRING_BOUNCY = {
  type: "spring" as const,
  stiffness: 260,
  damping: 20,
  mass: 1.0,
};
```

import { test, expect, _electron, type ElectronApplication, type Page } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appPath = path.resolve(__dirname, '../../');

test.describe('Notch Lifecycle, Geometry & Mascot E2E Suite', () => {
  let app: ElectronApplication;
  let page: Page;

  test.beforeEach(async () => {
    app = await _electron.launch({
      args: ['--no-sandbox', '.'],
      cwd: appPath,
      env: {
        ...process.env,
        E2E_TEST: 'true',
        NODE_ENV: 'production',
      },
    });

    page = await app.firstWindow();
    await page.waitForLoadState('domcontentloaded');
  });

  test.afterEach(async () => {
    if (app) {
      await app.close();
    }
  });

  test('1. Test Géométrie & Mur transparent (Prévention de la régression 460px -> 230px)', async () => {
    // Mesurer les dimensions initiales de la fenêtre Electron (hauteur compacte 230px)
    const initialBounds = await app.evaluate(async ({ BrowserWindow }) => {
      const win = BrowserWindow.getAllWindows()[0];
      return win ? win.getBounds() : null;
    });

    expect(initialBounds).not.toBeNull();
    expect(initialBounds!.height).toBe(230);
    expect(initialBounds!.width).toBe(660);

    // Cliquer sur le bouton d'onglet Écho (icône éclair Zap)
    const echoTabButton = page.locator('button[title="Buffer"]');
    await echoTabButton.click();

    // Attendre que la hauteur s'étende à 460px
    await expect.poll(async () => {
      const bounds = await app.evaluate(async ({ BrowserWindow }) => {
        const win = BrowserWindow.getAllWindows()[0];
        return win ? win.getBounds().height : 0;
      });
      return bounds;
    }, { timeout: 5000 }).toBe(460);

    // Cliquer sur le bouton d'onglet Accueil (icône goutte)
    const homeTabButton = page.locator('button[title="Home"]');
    await homeTabButton.click();

    // Vérifier que la hauteur redescend immédiatement et strictement à 230px
    await expect.poll(async () => {
      const bounds = await app.evaluate(async ({ BrowserWindow }) => {
        const win = BrowserWindow.getAllWindows()[0];
        return win ? win.getBounds().height : 0;
      });
      return bounds;
    }, { timeout: 5000 }).toBe(230);

    // Cliquer sur l'onglet Radar et vérifier qu'il conserve la hauteur compacte 230px (zéro resize)
    const radarTabButton = page.locator('button[title="Radar"]');
    await radarTabButton.click();

    await expect.poll(async () => {
      const bounds = await app.evaluate(async ({ BrowserWindow }) => {
        const win = BrowserWindow.getAllWindows()[0];
        return win ? win.getBounds().height : 0;
      });
      return bounds;
    }, { timeout: 5000 }).toBe(230);
  });

  test('2. Test Cycle de Vie Sentinelle (Hide rather than Destroy)', async () => {
    // Vérifier que la fenêtre est visible au départ
    const initialVisible = await app.evaluate(async ({ BrowserWindow }) => {
      const win = BrowserWindow.getAllWindows()[0];
      return win ? win.isVisible() : false;
    });
    expect(initialVisible).toBe(true);

    // Attendre le montage du composant React #root
    await page.waitForSelector('#root', { state: 'attached' });

    // Simuler l'appui sur la touche Escape
    await page.keyboard.press('Escape');

    // Vérifier que la fenêtre est masquée sans que l'application ne quitte
    await expect.poll(async () => {
      return await app.evaluate(async ({ BrowserWindow }) => {
        const win = BrowserWindow.getAllWindows()[0];
        return win ? win.isVisible() : true;
      });
    }, { timeout: 5000 }).toBe(false);

    const isStillRunning = await app.evaluate(async ({ BrowserWindow }) => {
      const win = BrowserWindow.getAllWindows()[0];
      return win !== undefined && !win.isDestroyed();
    });
    expect(isStillRunning).toBe(true);

    // Émettre win.show() (comme le toggle du Tray)
    await app.evaluate(async ({ BrowserWindow }) => {
      const win = BrowserWindow.getAllWindows()[0];
      if (win) {
        win.show();
      }
    });

    // Vérifier que la fenêtre redevient visible
    await expect.poll(async () => {
      return await app.evaluate(async ({ BrowserWindow }) => {
        const win = BrowserWindow.getAllWindows()[0];
        return win ? win.isVisible() : false;
      });
    }, { timeout: 5000 }).toBe(true);
  });

  test('3. Test Neutralité Géométrique Mascotte (Zéro écrasement résiduel)', async () => {
    // Passer sur l'onglet Accueil si on est en transition welcome
    const homeTabButton = page.locator('button[title="Home"]');
    await homeTabButton.click();

    // Attendre que le corps de la mascotte soit présent dans le DOM
    const mascotBody = page.locator('#mascot-body');
    await expect(mascotBody).toBeVisible();

    // Invoquer via DevTools / ContextBridge l'émotion 'ingesting'
    await page.evaluate(async () => {
      window.ekkoAPI?.testMascotEmotion('ingesting');
    });

    // Attendre 200ms de manducation active
    await page.waitForTimeout(200);

    // Réinitialiser à l'état nominal (null)
    await page.evaluate(async () => {
      window.ekkoAPI?.testMascotEmotion(null);
    });

    // Attendre 500ms pour stabilisation du ressort spring
    await page.waitForTimeout(500);

    // Inspecter le style calculé de #mascot-body (transform: matrix(1, 0, 0, 1, 0, 0) ou none)
    const transform = await mascotBody.evaluate((el) => {
      return window.getComputedStyle(el).transform;
    });

    // Si le transform est une matrice 'matrix(a, b, c, d, tx, ty)', a = scaleX, d = scaleY
    if (transform && transform !== 'none') {
      const matrixMatch = transform.match(/^matrix\((.+)\)$/);
      if (matrixMatch) {
        const parts = matrixMatch[1].split(',').map((p) => parseFloat(p.trim()));
        const scaleX = parts[0];
        const scaleY = parts[3];
        // Tolérance ressort amorti de 0.035 (sécurisation précision flottante IEEE 754)
        expect(Math.abs(scaleX - 1)).toBeLessThanOrEqual(0.035);
        expect(Math.abs(scaleY - 1)).toBeLessThanOrEqual(0.035);
      }
    } else {
      expect(transform).toBe('none');
    }
  });

  test('4. Test Continuité du Regard sur PodHeader', async () => {
    // S'assurer d'être sur l'onglet Accueil
    const homeTabButton = page.locator('button[title="Home"]');
    await homeTabButton.click();

    await page.waitForSelector('#mascot-body', { state: 'visible' });

    // Simuler le déplacement du curseur sur le PodHeader (x: 330, y: 16)
    await page.mouse.move(330, 16);

    // Attendre 100ms que le handler pointermove mette à jour l'état
    await page.waitForTimeout(100);

    // Vérifier que la particule de sommeil « z » n'est PAS présente dans le DOM
    const sleepZ = page.locator('#mascot-body').getByText('z', { exact: true });
    await expect(sleepZ).toHaveCount(0);

    // Vérifier que les pupilles ouvertes (les cercles blancs de reflet dans les yeux) sont présentes
    const whitePupils = page.locator('#mascot-body svg circle[fill="#ffffff"]');
    await expect(whitePupils).toHaveCount(2);
  });

  test('5. Test Stabilité et Fluidité Framerate (Zéro Long Task & Zéro Re-render Parasite)', async () => {
    // S'assurer d'être sur l'onglet Accueil
    const homeTabButton = page.locator('button[title="Home"]');
    await homeTabButton.click();

    await page.waitForSelector('#mascot-body', { state: 'visible' });

    // Injecter un collecteur PerformanceObserver traquant les 'longtask' (> 50ms)
    await page.evaluate(() => {
      (window as any).__jankStats = { longTasks: 0 };
      try {
        const observer = new PerformanceObserver((list) => {
          (window as any).__jankStats.longTasks += list.getEntries().length;
        });
        observer.observe({ entryTypes: ['longtask'] });
      } catch {
        // Fallback si longtask n'est pas supporté dans l'environnement
      }
    });

    // Enregistrer le nombre initial de re-renders de Mascot
    const initialRenderCount = await page.evaluate(() => {
      return (window as any).__mascotRenderCount || 0;
    });

    // Simuler un balayage continu et intensif de la souris sur tout le notch pendant 2 secondes (40 points de passage)
    const points = 40;
    for (let i = 0; i < points; i++) {
      const x = 50 + (i * 14) % 550;
      const y = 10 + (i * 9) % 200;
      await page.mouse.move(x, y);
      await page.waitForTimeout(50); // 40 * 50ms = 2000ms
    }

    // Récupérer les métriques de jank et de re-render
    const finalMetrics = await page.evaluate(() => {
      return {
        longTasks: (window as any).__jankStats?.longTasks || 0,
        renderCount: (window as any).__mascotRenderCount || 0,
      };
    });

    // Assertion 1 : Zéro longtask (> 50ms) sur le thread principal pendant le mouvement continu
    expect(finalMetrics.longTasks).toBe(0);

    // Assertion 2 : Le composant Mascot n'a subi aucun re-render parasite pendant le déplacement continu
    // (le nombre de renders reste stable à +/- 1 max pour l'état d'éveil initial)
    const renderDelta = finalMetrics.renderCount - initialRenderCount;
    expect(renderDelta).toBeLessThanOrEqual(1);
  });

  test('6. Stress Test de Clics Rapides (Anti-Race Condition Géométrique)', async () => {
    const homeTabButton = page.locator('button[title="Home"]');
    const echoTabButton = page.locator('button[title="Buffer"]');

    // Alterner 15 clics rapides consécutifs avec un intervalle de 60ms
    for (let i = 0; i < 15; i++) {
      if (i % 2 === 0) {
        await echoTabButton.click();
      } else {
        await homeTabButton.click();
      }
      await page.waitForTimeout(60);
    }

    // Le dernier clic cible obligatoirement l'onglet Accueil (230px)
    await homeTabButton.click();

    // Attendre 400ms après le dernier clic
    await page.waitForTimeout(400);

    // Assertion stricte : la hauteur native de la fenêtre est redescendue strictement à 230px
    const bounds = await app.evaluate(async ({ BrowserWindow }) => {
      const win = BrowserWindow.getAllWindows()[0];
      return win ? win.getBounds() : null;
    });

    expect(bounds).not.toBeNull();
    expect(bounds!.height).toBe(230);
  });

  test('7. Soak Test & Détection de Fuites Mémoire (Stabilité du Heap JS)', async () => {
    const homeTabButton = page.locator('button[title="Home"]');
    const echoTabButton = page.locator('button[title="Buffer"]');

    await homeTabButton.click();
    await page.waitForTimeout(300);

    // Mesurer la mémoire initiale du renderer
    const initialHeapBytes = await page.evaluate(() => {
      return (performance as any).memory?.usedJSHeapSize || 0;
    });

    // Exécuter une boucle de 25 cycles complets
    for (let cycle = 0; cycle < 25; cycle++) {
      // 1. Forçage émotion 'ingesting' puis reset nominal
      await page.evaluate(() => window.ekkoAPI?.testMascotEmotion('ingesting'));
      await page.waitForTimeout(20);
      await page.evaluate(() => window.ekkoAPI?.testMascotEmotion(null));

      // 2. Bascule vers Écho (460px) puis retour à Home (230px)
      await echoTabButton.click();
      await page.waitForTimeout(30);
      await homeTabButton.click();
      await page.waitForTimeout(30);

      // 3. Masquage puis réaffichage de la fenêtre native
      await app.evaluate(async ({ BrowserWindow }) => {
        const win = BrowserWindow.getAllWindows()[0];
        if (win) win.hide();
      });
      await page.waitForTimeout(20);
      await app.evaluate(async ({ BrowserWindow }) => {
        const win = BrowserWindow.getAllWindows()[0];
        if (win) win.show();
      });
    }

    // Attendre 500ms de stabilisation et mesurer le heap final
    await page.waitForTimeout(500);

    const finalHeapBytes = await page.evaluate(() => {
      return (performance as any).memory?.usedJSHeapSize || 0;
    });

    // Assertion : Le delta de heap mémoire doit rester borné (< 15 Mo de croissance)
    const deltaBytes = finalHeapBytes - initialHeapBytes;
    const deltaMB = deltaBytes / (1024 * 1024);

    expect(deltaMB).toBeLessThan(15);
  });

  test('8. Test Ancrage Chromatique OS & Fusion Dégradé', async () => {
    // 1. Vérifier que l'API IPC renvoie la couleur d'ancrage de la barre système
    const anchorColor = await page.evaluate(async () => {
      return await window.ekkoAPI?.getSystemAnchorColor?.();
    });
    expect(anchorColor).toBeDefined();
    expect(anchorColor).toMatch(/^#[0-9a-fA-F]{6}$/);

    // 2. Vérifier que la variable CSS --notch-anchor est active sur la racine
    const cssAnchorVar = await page.evaluate(() => {
      return getComputedStyle(document.documentElement).getPropertyValue('--notch-anchor').trim();
    });
    expect(cssAnchorVar).toBe(anchorColor);

    // 3. Vérifier que les deux congés concaves utilisent l'ancrage chromatique
    const filletPaths = page.locator('svg path[fill*="--notch-anchor"]');
    await expect(filletPaths).toHaveCount(2);
  });

  test('9. Test Mode Capsule Rétractée (32px), Double Contrôle (- / X) & Anti-Spam', async () => {
    // 1. S'assurer d'être sur l'onglet Accueil (230px)
    const homeTabButton = page.locator('button[title="Home"]');
    await homeTabButton.click();

    // 2. Vérifier la présence conjointe des doubles contrôles (Repli [-] et Fermeture [X])
    const collapseButton = page.locator('button[title="Collapse"]');
    const closeButton = page.locator('button[title="Close"]');
    await expect(collapseButton).toBeVisible();
    await expect(closeButton).toBeVisible();

    // 3. Test Anti-Spam : le bouton de repli se désactive immédiatement pour verrouiller les clics concurrents
    await collapseButton.click();
    await expect(collapseButton).toBeDisabled();

    // 4. Vérifier que la fenêtre Electron rétrécit physiquement et proprement à 130x32px
    await expect.poll(async () => {
      const bounds = await app.evaluate(async ({ BrowserWindow }) => {
        const win = BrowserWindow.getAllWindows()[0];
        return win ? win.getBounds() : null;
      });
      return bounds ? { width: bounds.width, height: bounds.height } : null;
    }, { timeout: 5000 }).toEqual({ width: 130, height: 32 });

    // 5. Vérifier que la mascotte miniature est visible dans la capsule
    const mascotBody = page.locator('#mascot-body');
    await expect(mascotBody).toBeVisible();

    // 6. Cliquer sur la mini-capsule pour déclencher l'expansion
    const miniCapsule = page.locator('div[title*="expand Ekko"]');
    await expect(miniCapsule).toBeVisible();
    await miniCapsule.click();

    // 7. Vérifier que la fenêtre retrouve immédiatement ses dimensions nominales 660x230px
    await expect.poll(async () => {
      const bounds = await app.evaluate(async ({ BrowserWindow }) => {
        const win = BrowserWindow.getAllWindows()[0];
        return win ? win.getBounds() : null;
      });
      return bounds ? { width: bounds.width, height: bounds.height } : null;
    }, { timeout: 5000 }).toEqual({ width: 660, height: 230 });

    // 8. Vérifier la réapparition des deux boutons de contrôle
    await expect(page.locator('button[title="Collapse"]')).toBeVisible();
    await expect(page.locator('button[title="Close"]')).toBeVisible();

    // 9. Tester le bouton de fermeture complète [X]
    await closeButton.click();
    await expect.poll(async () => {
      return await app.evaluate(async ({ BrowserWindow }) => {
        const win = BrowserWindow.getAllWindows()[0];
        return win ? win.isVisible() : true;
      });
    }, { timeout: 5000 }).toBe(false);
  });
});

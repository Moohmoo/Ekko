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

    // Cliquer sur le bouton d'onglet Chat (icône bulle MessageSquare)
    const chatTabButton = page.locator('button[title="Assistant & Chat"]');
    await chatTabButton.click();

    // Attendre que la hauteur s'étende à 460px
    await expect.poll(async () => {
      const bounds = await app.evaluate(async ({ BrowserWindow }) => {
        const win = BrowserWindow.getAllWindows()[0];
        return win ? win.getBounds().height : 0;
      });
      return bounds;
    }, { timeout: 5000 }).toBe(460);

    // Cliquer sur le bouton d'onglet Accueil (icône goutte)
    const homeTabButton = page.locator('button[title="Accueil (Bento)"]');
    await homeTabButton.click();

    // Vérifier que la hauteur redescend immédiatement et strictement à 230px
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
    const homeTabButton = page.locator('button[title="Accueil (Bento)"]');
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
        // Tolérance ressort amorti de 0.02
        expect(Math.abs(scaleX - 1)).toBeLessThanOrEqual(0.03);
        expect(Math.abs(scaleY - 1)).toBeLessThanOrEqual(0.03);
      }
    } else {
      expect(transform).toBe('none');
    }
  });

  test('4. Test Continuité du Regard sur PodHeader', async () => {
    // S'assurer d'être sur l'onglet Accueil
    const homeTabButton = page.locator('button[title="Accueil (Bento)"]');
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
});

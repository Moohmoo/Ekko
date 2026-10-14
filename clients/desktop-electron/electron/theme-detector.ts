import { nativeTheme } from 'electron';
import { execSync } from 'node:child_process';

/**
 * Detects host OS system top bar / panel color for seamless chromatic notch integration.
 * Zero heavy dependencies, zero Wayland screen capture permissions.
 */
export function getSystemAnchorColor(): string {
  const platform = process.platform;

  if (platform === 'darwin') {
    // macOS: dark menu bar or native black notch
    return nativeTheme.shouldUseDarkColors ? '#000000' : '#1a1a1a';
  }

  if (platform === 'win32') {
    // Windows 10/11: dark taskbar mode
    return nativeTheme.shouldUseDarkColors ? '#1c1c1c' : '#2d2d2d';
  }

  if (platform === 'linux') {
    try {
      // 1. Inspect GNOME GTK theme via gsettings
      const gtkTheme = execSync('gsettings get org.gnome.desktop.interface gtk-theme', {
        encoding: 'utf-8',
        stdio: ['ignore', 'pipe', 'ignore'],
        timeout: 500,
      })
        .trim()
        .toLowerCase();

      if (gtkTheme.includes('yaru')) {
        return '#131313'; // Ubuntu Yaru dark panel
      }
      if (gtkTheme.includes('adwaita')) {
        return '#1e1e1e'; // GNOME Adwaita dark panel
      }

      // 2. Fallback check on XDG_CURRENT_DESKTOP environment variable
      const xdgDesktop = (process.env.XDG_CURRENT_DESKTOP || '').toLowerCase();
      if (xdgDesktop.includes('ubuntu') || xdgDesktop.includes('unity')) {
        return '#131313';
      }
    } catch {
      // Fallback if gsettings is unavailable in environment
    }

    return '#131313'; // Standard Linux dark top panel
  }

  return '#131313';
}

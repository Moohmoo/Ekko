/**
 * Pure presentation utilities for formatting and normalizing PKM entities.
 * Zero side-effects, strictly typed.
 */

export interface SourceDisplay {
  label: string;
  isUrl: boolean;
  isFile: boolean;
  raw: string;
}

/**
 * Format raw source string (URL, file path, signal ID) into a clean, human-readable label.
 *
 * Examples:
 * - "/home/user/Ekko/data/attention.pdf" -> { label: "PDF · attention.pdf", isUrl: false, isFile: true }
 * - "https://arxiv.org/abs/2301.00001" -> { label: "arxiv.org/abs/2301.00001", isUrl: true, isFile: false }
 * - "https://news.ycombinator.com/item?id=123" -> { label: "news.ycombinator.com", isUrl: true, isFile: false }
 * - "ekko" -> { label: "ekko", isUrl: false, isFile: false }
 */
export function formatSourceDisplay(source: string): SourceDisplay {
  const raw = (source || '').trim();
  if (!raw) {
    return { label: 'ekko', isUrl: false, isFile: false, raw: '' };
  }

  // 1. Web URLs (http:// or https://)
  if (raw.startsWith('http://') || raw.startsWith('https://')) {
    try {
      const parsed = new URL(raw);
      const host = parsed.hostname.replace(/^www\./, '');
      const pathname = parsed.pathname;

      // For arXiv or specific document repositories, keep concise path
      if (host.includes('arxiv.org') && pathname) {
        return {
          label: `${host}${pathname.slice(0, 24)}`,
          isUrl: true,
          isFile: false,
          raw,
        };
      }

      // Default web label: host + simplified pathname if short
      if (pathname && pathname !== '/' && pathname.length <= 16) {
        return {
          label: `${host}${pathname}`,
          isUrl: true,
          isFile: false,
          raw,
        };
      }

      return {
        label: host,
        isUrl: true,
        isFile: false,
        raw,
      };
    } catch {
      return { label: raw, isUrl: true, isFile: false, raw };
    }
  }

  // 2. Local File paths (contains slash or file extension)
  const isLikelyPath = raw.includes('/') || raw.includes('\\') || /\.(pdf|md|markdown|txt|epub)$/i.test(raw);
  if (isLikelyPath) {
    // Extract base filename
    const parts = raw.split(/[/\\]/);
    const basename = parts[parts.length - 1] || raw;

    const extMatch = basename.match(/\.([a-zA-Z0-9]+)$/);
    const ext = extMatch ? extMatch[1].toUpperCase() : 'DOC';

    return {
      label: `${ext} · ${basename}`,
      isUrl: false,
      isFile: true,
      raw,
    };
  }

  // 3. Fallback identifier (e.g. source_id "inbox", "hackernews")
  return {
    label: raw,
    isUrl: false,
    isFile: false,
    raw,
  };
}

/**
 * Normalize any tag string to strict kebab-case lowercase.
 * Strip leading '#' if present, remove accents and special characters.
 *
 * Example:
 * - "#Attention Mechanism" -> "attention-mechanism"
 * - "Quantum_Annealing" -> "quantum-annealing"
 */
export function normalizeTag(tag: string): string {
  if (!tag) return 'pkm';
  const clean = tag.replace(/^#+/, '').trim().toLowerCase();
  return clean
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // remove accents
    .replace(/[^a-z0-9_-]/g, '-')    // convert spaces/punctuation to dash
    .replace(/-+/g, '-')             // collapse duplicate dashes
    .replace(/^-|-$/g, '') || 'pkm'; // trim edge dashes
}

/**
 * Format score into an optional discrete relevance indicator,
 * replacing raw misleading percentage like "3%".
 */
export function formatRelevance(score?: number): string | null {
  if (typeof score !== 'number' || isNaN(score) || score <= 0) {
    return null;
  }
  // If score is a normalized RRF score, return a subtle badge
  return '✦ pertinent';
}

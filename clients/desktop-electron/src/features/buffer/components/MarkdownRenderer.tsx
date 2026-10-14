import React from 'react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/**
 * Lightweight, safe Markdown renderer for PKM notes.
 * Parses headers (h1-h4), bold/italic, unordered lists, blockquotes,
 * code blocks, inline code, and paragraphs without external dependency risks.
 */
export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className = '',
}) => {
  const renderedElements = React.useMemo(() => {
    if (!content) return null;

    const lines = content.split('\n');
    const elements: React.ReactNode[] = [];

    let inCodeBlock = false;
    let codeBuffer: string[] = [];
    let codeLang = '';
    let listBuffer: string[] = [];

    const flushList = (keyPrefix: number) => {
      if (listBuffer.length > 0) {
        elements.push(
          <ul key={`ul-${keyPrefix}`} className="list-disc list-inside space-y-1 my-2 text-slate-300 pl-1">
            {listBuffer.map((item, idx) => (
              <li key={`li-${idx}`} className="leading-relaxed">
                {renderInlineFormatting(item)}
              </li>
            ))}
          </ul>
        );
        listBuffer = [];
      }
    };

    const flushCodeBlock = (keyPrefix: number) => {
      if (inCodeBlock) {
        elements.push(
          <div key={`codeblock-${keyPrefix}`} className="my-2.5 rounded-lg bg-black/40 border border-white/10 p-3 font-mono text-[11px] overflow-x-auto text-emerald-300">
            {codeLang && (
              <div className="text-[9px] uppercase tracking-wider text-slate-500 pb-1 mb-1 border-b border-white/5">
                {codeLang}
              </div>
            )}
            <pre className="whitespace-pre">
              <code>{codeBuffer.join('\n')}</code>
            </pre>
          </div>
        );
        codeBuffer = [];
        inCodeBlock = false;
        codeLang = '';
      }
    };

    lines.forEach((line, lineIndex) => {
      // Check code block fence ```
      if (line.trim().startsWith('```')) {
        if (inCodeBlock) {
          flushCodeBlock(lineIndex);
        } else {
          flushList(lineIndex);
          inCodeBlock = true;
          codeLang = line.trim().slice(3).trim();
        }
        return;
      }

      if (inCodeBlock) {
        codeBuffer.push(line);
        return;
      }

      // Check unordered list item (* or -)
      const listMatch = line.match(/^(\s*)[*-]\s+(.+)$/);
      if (listMatch) {
        listBuffer.push(listMatch[2]);
        return;
      } else {
        flushList(lineIndex);
      }

      const trimmed = line.trim();

      // Empty line
      if (!trimmed) {
        return;
      }

      // Headings
      if (trimmed.startsWith('# ')) {
        elements.push(
          <h1 key={`h1-${lineIndex}`} className="text-base font-bold text-white mt-4 mb-2 pb-1 border-b border-white/10">
            {renderInlineFormatting(trimmed.slice(2))}
          </h1>
        );
        return;
      }
      if (trimmed.startsWith('## ')) {
        elements.push(
          <h2 key={`h2-${lineIndex}`} className="text-sm font-semibold text-sky-200 mt-3 mb-1.5 pb-0.5 border-b border-white/5">
            {renderInlineFormatting(trimmed.slice(3))}
          </h2>
        );
        return;
      }
      if (trimmed.startsWith('### ')) {
        elements.push(
          <h3 key={`h3-${lineIndex}`} className="text-xs font-semibold text-slate-200 mt-2.5 mb-1">
            {renderInlineFormatting(trimmed.slice(4))}
          </h3>
        );
        return;
      }
      if (trimmed.startsWith('#### ')) {
        elements.push(
          <h4 key={`h4-${lineIndex}`} className="text-xs font-medium text-slate-300 mt-2 mb-1">
            {renderInlineFormatting(trimmed.slice(5))}
          </h4>
        );
        return;
      }

      // Blockquotes (> text)
      if (trimmed.startsWith('> ')) {
        elements.push(
          <blockquote key={`bq-${lineIndex}`} className="border-l-2 border-sky-400/50 pl-3 py-1 my-2 italic text-slate-400 bg-white/[0.02] rounded-r-md">
            {renderInlineFormatting(trimmed.slice(2))}
          </blockquote>
        );
        return;
      }

      // Default paragraph
      elements.push(
        <p key={`p-${lineIndex}`} className="my-1.5 text-slate-300 leading-relaxed">
          {renderInlineFormatting(line)}
        </p>
      );
    });

    flushList(lines.length);
    flushCodeBlock(lines.length);

    return elements;
  }, [content]);

  return (
    <div className={`markdown-body select-text ${className}`}>
      {renderedElements}
    </div>
  );
};

/**
 * Helper parsing inline formatting: `code`, **bold**, *italic*, and [links](url).
 */
function renderInlineFormatting(text: string): React.ReactNode {
  // Regex splitting on code `...`, bold **...**, italic *...*
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let keyIdx = 0;

  while (remaining.length > 0) {
    // 1. Inline Code `...`
    const codeMatch = remaining.match(/^(.*?)`([^`]+)`(.*)$/);
    // 2. Bold **...**
    const boldMatch = remaining.match(/^(.*?)\*\*([^*]+)\*\*(.*)$/);
    // 3. Italic *...*
    const italicMatch = remaining.match(/^(.*?)\*([^*]+)\*(.*)$/);

    // Pick closest match
    let closestType: 'code' | 'bold' | 'italic' | null = null;
    let closestIndex = Infinity;

    if (codeMatch && codeMatch[1].length < closestIndex) {
      closestIndex = codeMatch[1].length;
      closestType = 'code';
    }
    if (boldMatch && boldMatch[1].length < closestIndex) {
      closestIndex = boldMatch[1].length;
      closestType = 'bold';
    }
    if (italicMatch && italicMatch[1].length < closestIndex) {
      closestIndex = italicMatch[1].length;
      closestType = 'italic';
    }

    if (!closestType) {
      parts.push(<React.Fragment key={`txt-${keyIdx++}`}>{remaining}</React.Fragment>);
      break;
    }

    if (closestType === 'code' && codeMatch) {
      if (codeMatch[1]) parts.push(<React.Fragment key={`pre-${keyIdx++}`}>{codeMatch[1]}</React.Fragment>);
      parts.push(
        <code key={`code-${keyIdx++}`} className="px-1.5 py-0.5 rounded bg-white/10 font-mono text-[10.5px] text-amber-300">
          {codeMatch[2]}
        </code>
      );
      remaining = codeMatch[3];
    } else if (closestType === 'bold' && boldMatch) {
      if (boldMatch[1]) parts.push(<React.Fragment key={`pre-${keyIdx++}`}>{boldMatch[1]}</React.Fragment>);
      parts.push(
        <strong key={`bold-${keyIdx++}`} className="font-semibold text-white">
          {boldMatch[2]}
        </strong>
      );
      remaining = boldMatch[3];
    } else if (closestType === 'italic' && italicMatch) {
      if (italicMatch[1]) parts.push(<React.Fragment key={`pre-${keyIdx++}`}>{italicMatch[1]}</React.Fragment>);
      parts.push(
        <em key={`em-${keyIdx++}`} className="italic text-slate-200">
          {italicMatch[2]}
        </em>
      );
      remaining = italicMatch[3];
    }
  }

  return parts;
}

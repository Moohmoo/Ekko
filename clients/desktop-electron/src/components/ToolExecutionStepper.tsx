import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Check, X, ChevronDown, ChevronRight, Terminal } from 'lucide-react';
import type { ToolCallStep } from '../core/types';

interface ToolExecutionStepperProps {
  toolCalls: ToolCallStep[];
  isStreaming?: boolean;
  maxSteps?: number;
}

function formatInputSummary(input?: Record<string, unknown>): string {
  if (!input || Object.keys(input).length === 0) return '';
  return Object.entries(input)
    .map(([k, v]) => `${k}: ${typeof v === 'string' ? `"${v}"` : JSON.stringify(v)}`)
    .join(', ');
}

export const ToolExecutionStepper: React.FC<ToolExecutionStepperProps> = ({
  toolCalls,
  isStreaming = false,
  maxSteps = 5,
}) => {
  // Explicit user toggle state: defaults to false (collapsed once complete)
  const [userExpanded, setUserExpanded] = useState(false);
  // Track expanded drawer for individual step results
  const [expandedStepId, setExpandedStepId] = useState<string | null>(null);

  if (!toolCalls || toolCalls.length === 0) {
    return null;
  }

  const anyRunning = toolCalls.some((tc) => tc.status === 'running');
  const allCompleted = toolCalls.every((tc) => tc.status === 'completed');
  const hasError = toolCalls.some((tc) => tc.status === 'error');

  // Active during streaming or tool run, auto-collapses on completion unless user explicitly expanded
  const isAccordionOpen = (isStreaming || anyRunning) ? true : userExpanded;

  const toggleAccordion = (e: React.MouseEvent) => {
    e.stopPropagation();
    setUserExpanded((prev) => !prev);
  };

  const toggleStepDrawer = (id: string, e: React.MouseEvent | React.KeyboardEvent) => {
    e.stopPropagation();
    setExpandedStepId((prev) => (prev === id ? null : id));
  };

  // Dynamic header label
  const toolCount = toolCalls.length;
  const headerLabel = anyRunning
    ? 'Exécution des outils en cours...'
    : toolCount === 1
    ? `>_ [${toolCalls[0].tool}]`
    : `>_ ${toolCount} outils exécutés`;

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-2.5 mb-2.5 select-none text-xs transition-all overflow-hidden">
      {/* Compact Accordion Header */}
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={toggleAccordion}
          className="flex items-center gap-2 text-left hover:text-white transition-colors focus:outline-none group min-w-0 flex-1"
          aria-expanded={isAccordionOpen}
        >
          <div className="text-zinc-400 group-hover:text-zinc-200 transition-colors shrink-0">
            {isAccordionOpen ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )}
          </div>
          <div className="flex items-center gap-1.5 font-mono text-[11px] text-zinc-300 truncate">
            <Terminal className="w-3 h-3 text-sky-400 shrink-0" />
            <span className="truncate">{headerLabel}</span>
          </div>
        </button>

        {/* Global Status Pill */}
        <div className="flex items-center gap-1.5 text-[10px] font-mono shrink-0">
          {anyRunning ? (
            <span className="flex items-center gap-1 text-sky-400 bg-sky-500/[0.1] px-2 py-0.5 rounded-full border border-sky-500/20">
              <Loader2 className="w-3 h-3 animate-spin shrink-0" />
              <span>en cours</span>
            </span>
          ) : hasError ? (
            <span className="flex items-center gap-1 text-rose-400 bg-rose-500/[0.1] px-2 py-0.5 rounded-full border border-rose-500/20">
              <X className="w-3 h-3 shrink-0" />
              <span>avertissement</span>
            </span>
          ) : allCompleted ? (
            <span className="flex items-center gap-1 text-emerald-400 bg-emerald-500/[0.1] px-2 py-0.5 rounded-full border border-emerald-500/20">
              <Check className="w-3 h-3 shrink-0" />
              <span>terminé</span>
            </span>
          ) : null}
        </div>
      </div>

      {/* Animated Collapsible Stepper Body */}
      <AnimatePresence initial={false}>
        {isAccordionOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-2.5 pt-2 border-t border-white/[0.04] space-y-1.5">
              {toolCalls.map((step, index) => {
                const stepNum = index + 1;
                const isStepRunning = step.status === 'running';
                const isStepError = step.status === 'error';
                const inputSummary = formatInputSummary(step.input);
                const isExpanded = expandedStepId === step.id;

                return (
                  <div key={step.id} className="flex flex-col">
                    <div
                      onClick={(e) => toggleStepDrawer(step.id, e)}
                      className="flex items-center gap-2 text-xs font-mono py-1 px-1.5 rounded-lg hover:bg-white/[0.03] cursor-pointer transition-colors"
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          toggleStepDrawer(step.id, e);
                        }
                      }}
                    >
                      {/* Status Icon */}
                      <div className="shrink-0 flex items-center justify-center w-4 h-4">
                        {isStepRunning ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-400" />
                        ) : isStepError ? (
                          <X className="w-3.5 h-3.5 text-rose-400" />
                        ) : (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        )}
                      </div>

                      {/* Step Progress Badge */}
                      <span className="text-zinc-400 bg-white/[0.05] px-1.5 py-0.5 rounded text-[10px] shrink-0 font-medium">
                        Étape {stepNum}/{maxSteps}
                      </span>

                      {/* Tool Name Tag */}
                      <span className="text-sky-300 font-semibold shrink-0">
                        [{step.tool}]
                      </span>

                      {/* Truncated Input Parameters with Tooltip */}
                      {inputSummary ? (
                        <span
                          title={inputSummary}
                          className="text-zinc-500 text-[11px] truncate max-w-[200px]"
                        >
                          {inputSummary}
                        </span>
                      ) : null}

                      {/* Duration if available */}
                      {step.duration_ms !== undefined && (
                        <span className="text-zinc-600 text-[10px] ml-auto shrink-0 font-mono">
                          {step.duration_ms}ms
                        </span>
                      )}
                    </div>

                    {/* Step Output Drawer with Animated Disclosure */}
                    <AnimatePresence>
                      {isExpanded && step.output && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.18, ease: 'easeOut' }}
                          className="overflow-hidden"
                        >
                          <div className="mt-1 ml-6 p-2 rounded-lg bg-black/30 border border-white/[0.04] text-[10px] font-mono text-zinc-400 select-text">
                            <span className="text-zinc-500 uppercase text-[9px] font-sans font-medium block mb-1">
                              Résultat retourné :
                            </span>
                            <pre className="whitespace-pre-wrap text-emerald-300/80 max-h-28 overflow-y-auto">
                              {step.output}
                            </pre>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

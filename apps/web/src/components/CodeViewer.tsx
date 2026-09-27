"use client";

import React, { useState } from "react";
import { Copy, Check, FileCode, ExternalLink } from "lucide-react";

interface CodeViewerProps {
  code: string;
  language?: string;
  filePath?: string;
  startLine?: number;
  endLine?: number;
  symbolName?: string;
  symbolType?: string;
  className?: string;
  maxHeight?: string;
}

export function CodeViewer({
  code,
  language = "python",
  filePath,
  startLine = 1,
  endLine,
  symbolName,
  symbolType,
  className = "",
  maxHeight = "max-h-96",
}: CodeViewerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = code.split("\n");

  return (
    <div className={`rounded-xl border border-border bg-surface-300 overflow-hidden font-mono text-xs ${className}`}>
      {/* Header Bar */}
      {(filePath || symbolName) && (
        <div className="px-4 py-2 bg-surface-200 border-b border-border flex items-center justify-between text-slate-400">
          <div className="flex items-center space-x-2 truncate">
            <FileCode className="h-3.5 w-3.5 text-brand-sky flex-shrink-0" />
            {filePath && (
              <span className="text-slate-200 font-bold truncate">
                {filePath}
                {startLine !== undefined && (
                  <span className="text-slate-500 font-normal">
                    :L{startLine}{endLine ? `-${endLine}` : ""}
                  </span>
                )}
              </span>
            )}
            {symbolName && (
              <span className="px-1.5 py-0.2 rounded bg-surface-100 text-brand-sky font-semibold border border-border text-[10px]">
                {symbolName} {symbolType ? `(${symbolType})` : ""}
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2 flex-shrink-0">
            <button
              onClick={handleCopy}
              className="p-1 px-2 rounded bg-surface-100 hover:bg-surface-50 text-slate-300 hover:text-white border border-border flex items-center space-x-1 transition text-[10px]"
              title="Copy code snippet"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 text-emerald-400" />
                  <span className="text-emerald-400 font-bold">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Code Area with Line Numbers */}
      <div className={`overflow-x-auto ${maxHeight} p-3 text-[12px] leading-relaxed select-text bg-[#06080d]`}>
        <div className="table w-full">
          {lines.map((line, idx) => {
            const lineNum = (startLine || 1) + idx;
            return (
              <div key={idx} className="table-row hover:bg-surface-200/50 transition-colors">
                <span className="table-cell pr-4 text-right select-none text-slate-600 font-mono text-[11px] w-8">
                  {lineNum}
                </span>
                <span className="table-cell text-slate-200 whitespace-pre font-mono">
                  {line || " "}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

"use client";

import { User, Bot, Loader2, RefreshCw, AlertCircle, Copy, Check } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { SourcePanel } from "./SourcePanel";
import type { ChatMessage } from "@/lib/types";

interface MessageBubbleProps {
  message: ChatMessage;
  onRetry?: (messageId: string) => void;
  isRetrying?: boolean;
}

// Typing cursor component
function TypingCursor() {
  return (
    <span 
      className="inline-block w-[3px] h-[1em] ml-0.5 bg-foreground/60 rounded-[1px] animate-cursor-blink align-text-bottom"
    />
  );
}

export function MessageBubble({ message, onRetry, isRetrying }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const showRetry = !isUser && !message.isStreaming && (message.isError || (!message.isLoading && message.content));
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(message.content);
      } else {
        // Fallback for older browsers or non-HTTPS
        const textArea = document.createElement("textarea");
        textArea.value = message.content;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  if (isUser) {
    // User message - simple right-aligned bubble
    return (
      <div className="flex justify-end py-4 group">
        <div className="flex items-start gap-3 max-w-[85%]">
          <div className="flex flex-col items-end">
            <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5">
              <p className="whitespace-pre-wrap break-words text-sm">{message.content}</p>
            </div>
            {/* Copy button - appears on hover */}
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 mt-1 text-xs text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={handleCopy}
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 mr-1" />
                  已复制
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3 mr-1" />
                  复制
                </>
              )}
            </Button>
          </div>
          <Avatar className="h-8 w-8 shrink-0">
            <AvatarFallback className="bg-primary text-primary-foreground">
              <User className="h-4 w-4" />
            </AvatarFallback>
          </Avatar>
        </div>
      </div>
    );
  }

  // Assistant message - full width, clean layout
  return (
    <div className="py-6 border-b border-border/50 last:border-0">
      <div className="flex gap-4">
        {/* Avatar */}
        <Avatar className="h-8 w-8 shrink-0 mt-0.5">
          <AvatarFallback className="bg-muted">
            <Bot className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-3">
          {/* Loading state */}
          {message.isLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm">正在检索知识图谱...</span>
            </div>
          ) : (
            <>
              {/* Error state */}
              {message.isError && (
                <div className="flex items-center gap-2 text-destructive bg-destructive/10 rounded-lg px-3 py-2 text-sm">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{message.content}</span>
                </div>
              )}

              {/* Main content */}
              {!message.isError && (
                <div className="prose prose-sm dark:prose-invert max-w-none 
                  prose-p:my-2 prose-p:leading-7
                  prose-headings:mt-4 prose-headings:mb-2
                  prose-ul:my-2 prose-ol:my-2
                  prose-li:my-0.5
                  prose-strong:text-foreground prose-strong:font-semibold
                  prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-normal prose-code:before:content-none prose-code:after:content-none
                  prose-pre:bg-muted prose-pre:border prose-pre:rounded-lg
                  prose-blockquote:border-l-primary prose-blockquote:bg-muted/50 prose-blockquote:py-1 prose-blockquote:not-italic
                  text-[15px] leading-7"
                >
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p>{children}</p>,
                      strong: ({ children }) => <strong>{children}</strong>,
                      code: ({ children, className }) => {
                        const isBlock = className?.includes('language-');
                        if (isBlock) {
                          return <code className={className}>{children}</code>;
                        }
                        return <code>{children}</code>;
                      },
                      a: ({ children, href }) => (
                        <a href={href} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
                          {children}
                        </a>
                      ),
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                  {message.isStreaming && <TypingCursor />}
                </div>
              )}

              {/* Source Panel - collapsible */}
              {(message.results || message.graph_context) && (
                <SourcePanel
                  results={message.results || []}
                  graphContext={message.graph_context || null}
                  searchType={message.search_type || "hybrid"}
                  timing={message.timing}
                />
              )}

              {/* Actions bar */}
              {!message.isStreaming && message.content && (
                <div className="flex items-center gap-1 pt-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                    onClick={handleCopy}
                  >
                    {copied ? (
                      <>
                        <Check className="h-3.5 w-3.5 mr-1" />
                        已复制
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5 mr-1" />
                        复制
                      </>
                    )}
                  </Button>
                  {showRetry && onRetry && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                      onClick={() => onRetry(message.id)}
                      disabled={isRetrying}
                    >
                      <RefreshCw className={cn("h-3.5 w-3.5 mr-1", isRetrying && "animate-spin")} />
                      {message.isError ? "重试" : "重新生成"}
                    </Button>
                  )}
                  <span className="text-xs text-muted-foreground ml-auto">
                    {message.timestamp.toLocaleTimeString("zh-CN", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

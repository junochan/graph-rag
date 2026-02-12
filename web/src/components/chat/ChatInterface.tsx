"use client";

import { useState, useCallback } from "react";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChatMessages } from "./ChatMessages";
import { ChatInput } from "./ChatInput";
import { ChatSettings } from "./ChatSettings";
import { useStreamQuery } from "@/hooks/useStreamQuery";
import { DEFAULT_CHAT_SETTINGS } from "@/lib/types";
import type { ChatSettings as ChatSettingsType } from "@/lib/types";

const SEARCH_TYPE_LABELS: Record<string, string> = {
  hybrid: "混合模式",
  vector: "向量模式",
  graph: "图模式",
};

export function ChatInterface() {
  const [input, setInput] = useState("");
  const [settings, setSettings] = useState<ChatSettingsType>(DEFAULT_CHAT_SETTINGS);
  const { messages, isLoading, retryingId, sendMessage, retryMessage, clearMessages } =
    useStreamQuery(settings);

  const handleSend = useCallback(() => {
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput("");
  }, [input, isLoading, sendMessage]);

  const handleSuggestionClick = useCallback(
    (text: string) => setInput(text),
    []
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold">知识对话</h2>
          <Badge
            variant={
              settings.searchType === "hybrid"
                ? "default"
                : settings.searchType === "vector"
                ? "secondary"
                : "outline"
            }
          >
            {SEARCH_TYPE_LABELS[settings.searchType]}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={clearMessages}
            disabled={messages.length === 0}
            title="清空对话"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
          <ChatSettings settings={settings} onChange={setSettings} />
        </div>
      </div>

      {/* Messages */}
      <ChatMessages
        messages={messages}
        retryingId={retryingId}
        onRetry={retryMessage}
        onSuggestionClick={handleSuggestionClick}
      />

      {/* Input */}
      <ChatInput
        value={input}
        onChange={setInput}
        onSend={handleSend}
        disabled={isLoading}
      />
    </div>
  );
}

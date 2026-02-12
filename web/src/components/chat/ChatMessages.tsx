"use client";

import { useEffect, useRef } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MessageBubble } from "./MessageBubble";
import type { ChatMessage } from "@/lib/types";

interface ChatMessagesProps {
  messages: ChatMessage[];
  retryingId: string | null;
  onRetry: (messageId: string) => void;
  onSuggestionClick: (text: string) => void;
}

const SUGGESTIONS = [
  "张三在哪家公司工作？",
  "阿里巴巴有什么产品？",
  "李四的朋友在哪个城市工作？",
];

export function ChatMessages({
  messages,
  retryingId,
  onRetry,
  onSuggestionClick,
}: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom when messages change (including streaming tokens)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="flex flex-col items-center justify-center h-full text-center py-12 px-4">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
            <Send className="h-8 w-8 text-primary" />
          </div>
          <h3 className="text-lg font-medium mb-2">开始对话</h3>
          <p className="text-muted-foreground max-w-sm">
            输入问题，系统会自动从知识图谱和向量库中检索相关信息并生成回答
          </p>
          <div className="flex flex-wrap gap-2 mt-4 justify-center">
            {SUGGESTIONS.map((text) => (
              <Button
                key={text}
                variant="outline"
                size="sm"
                onClick={() => onSuggestionClick(text)}
              >
                {text}
              </Button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4">
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            onRetry={onRetry}
            isRetrying={retryingId === message.id}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

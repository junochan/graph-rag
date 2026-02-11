"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Settings2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { MessageBubble } from "./MessageBubble";
import { retrieveStream, StreamContextEvent } from "@/lib/api";
import type { ChatMessage, ChatSettings, SearchType } from "@/lib/types";

const defaultSettings: ChatSettings = {
  searchType: "hybrid",
  topK: 10,
  expandGraph: true,
  graphDepth: 2,
  useLLM: true,
};

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [settings, setSettings] = useState<ChatSettings>(defaultSettings);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Generate unique ID
  const generateId = () => Math.random().toString(36).substring(2, 9);

  // Build chat history from messages (excluding current loading message)
  const buildHistory = useCallback((excludeId?: string) => {
    return messages
      .filter((msg) => msg.id !== excludeId && !msg.isLoading && msg.content)
      .slice(-10) // Keep last 10 messages for context
      .map((msg) => ({
        role: msg.role as "user" | "assistant",
        content: msg.content,
      }));
  }, [messages]);

  // Execute streaming query
  const executeStreamQuery = useCallback(
    async (query: string, assistantId: string) => {
      let hasError = false;
      const history = buildHistory(assistantId);

      try {
        await retrieveStream(
          {
            query,
            search_type: settings.searchType,
            top_k: settings.topK,
            expand_graph: settings.expandGraph,
            graph_depth: settings.graphDepth,
            use_llm: settings.useLLM,
            history,
          },
          {
            onContext: (context: StreamContextEvent) => {
              // Update with context (results, graph_context) and immediately show streaming cursor
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? {
                        ...msg,
                        results: context.results,
                        graph_context: context.graph_context,
                        sources: context.sources,
                        timing: context.timing,
                        content: "", // Start empty, cursor will show via isStreaming
                        isLoading: false,
                        isStreaming: true, // Show cursor immediately
                      }
                    : msg
                )
              );
            },
            onToken: (token: string) => {
              // Append token to content
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? {
                        ...msg,
                        content: msg.content + token,
                      }
                    : msg
                )
              );
            },
            onDone: () => {
              // Mark streaming complete
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? {
                        ...msg,
                        isStreaming: false,
                        isError: false,
                        originalQuery: query,
                      }
                    : msg
                )
              );
            },
            onError: (error: string) => {
              hasError = true;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? {
                        ...msg,
                        content: error,
                        isLoading: false,
                        isStreaming: false,
                        isError: true,
                        originalQuery: query,
                      }
                    : msg
                )
              );
            },
          }
        );

        return !hasError;
      } catch (error) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  content: `${error instanceof Error ? error.message : "未知错误"}`,
                  isLoading: false,
                  isStreaming: false,
                  isError: true,
                  originalQuery: query,
                }
              : msg
          )
        );
        return false;
      }
    },
    [settings, buildHistory]
  );

  // Handle send message
  const handleSend = useCallback(async () => {
    const trimmedInput = input.trim();
    if (!trimmedInput || isLoading) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content: trimmedInput,
      timestamp: new Date(),
    };

    // Add loading assistant message
    const assistantId = generateId();
    const loadingMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isLoading: true,
      search_type: settings.searchType,
      originalQuery: trimmedInput,
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setInput("");
    setIsLoading(true);

    await executeStreamQuery(trimmedInput, assistantId);
    setIsLoading(false);
  }, [input, isLoading, settings.searchType, executeStreamQuery]);

  // Handle retry
  const handleRetry = useCallback(
    async (messageId: string) => {
      // Find the message and its original query
      const message = messages.find((m) => m.id === messageId);
      if (!message || !message.originalQuery) return;

      const query = message.originalQuery;

      // Set loading state
      setRetryingId(messageId);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
                isLoading: true,
                isError: false,
                content: "",
                results: undefined,
                graph_context: undefined,
                timestamp: new Date(),
              }
            : msg
        )
      );

      await executeStreamQuery(query, messageId);
      setRetryingId(null);
    },
    [messages, executeStreamQuery]
  );

  // Handle key press
  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

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
            {settings.searchType === "hybrid"
              ? "混合模式"
              : settings.searchType === "vector"
              ? "向量模式"
              : "图模式"}
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

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" title="设置">
                <Settings2 className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>检索设置</DropdownMenuLabel>
              <DropdownMenuSeparator />

              <DropdownMenuLabel className="text-xs text-muted-foreground font-normal">
                检索模式
              </DropdownMenuLabel>
              <DropdownMenuRadioGroup
                value={settings.searchType}
                onValueChange={(value) =>
                  setSettings((s) => ({
                    ...s,
                    searchType: value as SearchType,
                  }))
                }
              >
                <DropdownMenuRadioItem value="hybrid">
                  混合检索 (推荐)
                </DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="vector">
                  向量检索
                </DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="graph">
                  图检索
                </DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>

              <DropdownMenuSeparator />
              <DropdownMenuLabel className="text-xs text-muted-foreground font-normal">
                图扩展深度
              </DropdownMenuLabel>
              <DropdownMenuRadioGroup
                value={settings.graphDepth.toString()}
                onValueChange={(value) =>
                  setSettings((s) => ({ ...s, graphDepth: parseInt(value) }))
                }
              >
                <DropdownMenuRadioItem value="1">1 跳</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="2">2 跳</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="3">3 跳</DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12 px-4">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Send className="h-8 w-8 text-primary" />
            </div>
            <h3 className="text-lg font-medium mb-2">开始对话</h3>
            <p className="text-muted-foreground max-w-sm">
              输入问题，系统会自动从知识图谱和向量库中检索相关信息并生成回答
            </p>
            <div className="flex flex-wrap gap-2 mt-4 justify-center">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setInput("张三在哪家公司工作？")}
              >
                张三在哪家公司工作？
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setInput("阿里巴巴有什么产品？")}
              >
                阿里巴巴有什么产品？
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setInput("李四的朋友在哪个城市工作？")}
              >
                李四的朋友在哪个城市工作？
              </Button>
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-4">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onRetry={handleRetry}
                isRetrying={retryingId === message.id}
              />
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Input Area */}
      <div className="border-t bg-background">
        <div className="max-w-3xl mx-auto p-4">
          <div className="relative flex items-end gap-2 bg-muted/50 rounded-2xl border border-border/50 focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20 transition-all">
            <Textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="输入问题..."
              rows={1}
              className="flex-1 min-h-[52px] max-h-40 resize-none border-0 bg-transparent px-4 py-3.5 text-[15px] placeholder:text-muted-foreground/60 focus-visible:ring-0 focus-visible:ring-offset-0"
              disabled={isLoading}
            />
            <div className="flex items-center gap-1 p-2">
              <Button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                size="icon"
                className="h-9 w-9 rounded-xl shrink-0"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground/70 mt-2 text-center">
            按 Enter 发送，Shift + Enter 换行
          </p>
        </div>
      </div>
    </div>
  );
}

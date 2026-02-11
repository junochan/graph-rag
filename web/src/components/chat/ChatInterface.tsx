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
import { retrieve } from "@/lib/api";
import type {
  ChatMessage,
  ChatSettings,
  SearchType,
  DEFAULT_CHAT_SETTINGS,
} from "@/lib/types";

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
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await retrieve({
        query: trimmedInput,
        search_type: settings.searchType,
        top_k: settings.topK,
        expand_graph: settings.expandGraph,
        graph_depth: settings.graphDepth,
        use_llm: settings.useLLM,
      });

      // Update assistant message with response
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? {
                ...msg,
                content:
                  response.answer ||
                  (response.errors.length > 0
                    ? `错误: ${response.errors.join(", ")}`
                    : "未找到相关信息"),
                results: response.results,
                graph_context: response.graph_context,
                sources: response.sources,
                isLoading: false,
              }
            : msg
        )
      );
    } catch (error) {
      // Update with error
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? {
                ...msg,
                content: `请求失败: ${
                  error instanceof Error ? error.message : "Unknown error"
                }`,
                isLoading: false,
              }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, settings]);

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
      <ScrollArea className="flex-1 px-4" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
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
          <div className="py-4">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Input Area */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <Textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="输入问题，按 Enter 发送..."
            rows={1}
            className="min-h-[44px] max-h-32 resize-none"
            disabled={isLoading}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            size="icon"
            className="h-11 w-11 shrink-0"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          按 Enter 发送，Shift + Enter 换行
        </p>
      </div>
    </div>
  );
}

"use client";

import { useState, useCallback } from "react";
import { retrieveStream, StreamContextEvent } from "@/lib/api";
import type { ChatMessage, ChatSettings } from "@/lib/types";

// Generate unique ID
function generateId() {
  return Math.random().toString(36).substring(2, 9);
}

export function useStreamQuery(settings: ChatSettings) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  // Build chat history from messages (excluding current loading message)
  const buildHistory = useCallback(
    (excludeId?: string) => {
      return messages
        .filter((msg) => msg.id !== excludeId && !msg.isLoading && msg.content)
        .slice(-10)
        .map((msg) => ({
          role: msg.role as "user" | "assistant",
          content: msg.content,
        }));
    },
    [messages]
  );

  // Execute streaming query against a specific assistant message
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
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? {
                        ...msg,
                        results: context.results,
                        graph_context: context.graph_context,
                        sources: context.sources,
                        timing: context.timing,
                        rewrittenQuery: context.rewritten_query,
                        content: "",
                        isLoading: false,
                        isStreaming: true,
                      }
                    : msg
                )
              );
            },
            onToken: (token: string) => {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, content: msg.content + token }
                    : msg
                )
              );
            },
            onDone: () => {
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

  // Send a new message
  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading) return;

      const userMessage: ChatMessage = {
        id: generateId(),
        role: "user",
        content: trimmed,
        timestamp: new Date(),
      };

      const assistantId = generateId();
      const loadingMessage: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isLoading: true,
        search_type: settings.searchType,
        originalQuery: trimmed,
      };

      setMessages((prev) => [...prev, userMessage, loadingMessage]);
      setIsLoading(true);

      await executeStreamQuery(trimmed, assistantId);
      setIsLoading(false);
    },
    [isLoading, settings.searchType, executeStreamQuery]
  );

  // Retry a failed message
  const retryMessage = useCallback(
    async (messageId: string) => {
      const message = messages.find((m) => m.id === messageId);
      if (!message?.originalQuery) return;

      const query = message.originalQuery;
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

  // Clear all messages
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isLoading,
    retryingId,
    sendMessage,
    retryMessage,
    clearMessages,
  };
}

"use client";

import { Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ChatSettings as ChatSettingsType, SearchType } from "@/lib/types";

interface ChatSettingsProps {
  settings: ChatSettingsType;
  onChange: (settings: ChatSettingsType) => void;
}

export function ChatSettings({ settings, onChange }: ChatSettingsProps) {
  return (
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
            onChange({ ...settings, searchType: value as SearchType })
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
            onChange({ ...settings, graphDepth: parseInt(value) })
          }
        >
          <DropdownMenuRadioItem value="1">1 跳</DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="2">2 跳</DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="3">3 跳</DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

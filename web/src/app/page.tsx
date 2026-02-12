"use client";

import Link from "next/link";
import { MessageSquare, Upload, Network, ArrowRight } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const features = [
  {
    title: "对话检索",
    description: "基于知识图谱的智能问答，支持多跳推理，清晰展示数据来源",
    icon: MessageSquare,
    href: "/chat",
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
  },
  {
    title: "构建知识库",
    description: "上传文档自动构建知识图谱，支持 PDF、Word、TXT 等格式",
    icon: Upload,
    href: "/build",
    color: "text-green-500",
    bgColor: "bg-green-500/10",
  },
  {
    title: "图谱可视化",
    description: "交互式知识图谱展示，直观查看实体关系网络",
    icon: Network,
    href: "/graph",
    color: "text-orange-500",
    bgColor: "bg-orange-500/10",
  },
];

export default function HomePage() {
  return (
    <div className="container mx-auto py-8 px-4">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold tracking-tight mb-4">
          知识图谱 RAG 系统
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          基于 NebulaGraph 的检索增强生成系统，结合向量检索与图数据库，
          实现精准的多跳知识推理
        </p>
      </div>

      {/* Feature Cards */}
      <div className="grid gap-6 md:grid-cols-3 mb-12">
        {features.map((feature) => {
          const Icon = feature.icon;
          return (
            <Link key={feature.href} href={feature.href} className="block">
              <Card className="group hover:shadow-lg transition-all hover:border-primary/30 cursor-pointer h-full">
                <CardHeader>
                  <div
                    className={`w-12 h-12 rounded-lg ${feature.bgColor} flex items-center justify-center mb-4`}
                  >
                    <Icon className={`h-6 w-6 ${feature.color}`} />
                  </div>
                  <CardTitle className="flex items-center justify-between">
                    {feature.title}
                    <ArrowRight className="h-5 w-5 text-muted-foreground opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                  </CardTitle>
                  <CardDescription>{feature.description}</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          );
        })}
      </div>

      {/* Architecture Info */}
      <Card>
        <CardHeader>
          <CardTitle>系统架构</CardTitle>
          <CardDescription>三种检索模式，灵活应对不同场景</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="p-4 rounded-lg border">
              <h3 className="font-semibold mb-2 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                Hybrid 混合模式
              </h3>
              <p className="text-sm text-muted-foreground">
                结合向量相似度搜索与知识图谱遍历，推荐使用
              </p>
            </div>
            <div className="p-4 rounded-lg border">
              <h3 className="font-semibold mb-2 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                Vector 向量模式
              </h3>
              <p className="text-sm text-muted-foreground">
                纯向量语义检索，适合模糊查询和相似度匹配
              </p>
            </div>
            <div className="p-4 rounded-lg border">
              <h3 className="font-semibold mb-2 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-orange-500" />
                Graph 图模式
              </h3>
              <p className="text-sm text-muted-foreground">
                纯图数据库查询，精确的实体关系推理
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

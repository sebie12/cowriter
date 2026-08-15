import type { Project } from "../types";

const now = new Date().toISOString();

export const mockProjects: Project[] = [
  {
    id: "project-ai-agents",
    title: "Research paper - AI agents",
    createdAt: now,
    updatedAt: now,
    messages: [
      {
        id: "message-ai-1",
        role: "user",
        content: "Help me shape a research paper about AI agents in knowledge work.",
        createdAt: now,
      },
      {
        id: "message-ai-2",
        role: "assistant",
        content:
          "# Research direction\n\nA strong paper could focus on how agentic systems change planning, delegation, and review in knowledge work.\n\n## Possible thesis\n\nAI agents are most useful when they operate as constrained collaborators rather than autonomous replacements.\n\n- Define the agent's scope clearly.\n- Compare single-agent and multi-agent workflows.\n- Evaluate human review as part of the system, not as an afterthought.\n\n> The key research question is not whether agents can complete tasks, but how reliably they can participate in accountable workflows.\n\nYou might use `workflow reliability` as a recurring analytical frame.",
        createdAt: now,
      },
    ],
  },
  {
    id: "project-history-essay",
    title: "History essay",
    createdAt: now,
    updatedAt: now,
    messages: [
      {
        id: "message-history-1",
        role: "user",
        content: "I need an outline for an essay about the printing press and social change.",
        createdAt: now,
      },
      {
        id: "message-history-2",
        role: "assistant",
        content:
          "## Draft outline\n\n1. Introduce the printing press as an infrastructure shift.\n2. Explain how reproduction costs changed.\n3. Connect printed materials to religious, scientific, and political networks.\n4. Address limits: literacy, censorship, and regional variation.\n\nA concise opening claim could be: `The printing press accelerated social change by making ideas cheaper to preserve, distribute, and contest.`",
        createdAt: now,
      },
    ],
  },
  {
    id: "project-distributed-systems",
    title: "Distributed systems notes",
    createdAt: now,
    updatedAt: now,
    messages: [
      {
        id: "message-distributed-1",
        role: "assistant",
        content:
          "## Notes to expand\n\n- Consensus protocols\n- Replication models\n- Failure detection\n- Tradeoffs between consistency and availability\n\n```text\nclient -> coordinator -> replicas\n```",
        createdAt: now,
      },
    ],
  },
  {
    id: "project-mcp-research",
    title: "MCP research",
    createdAt: now,
    updatedAt: now,
    messages: [],
  },
];

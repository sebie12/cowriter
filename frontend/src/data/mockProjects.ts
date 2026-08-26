import type { Project } from "../types";

const now = new Date().toISOString();

export const mockProjects: Project[] = [
  {
    id: "project-modernism",
    title: "Modernism research paper",
    createdAt: now,
    updatedAt: now,
    messages: [
      {
        id: "message-modernism-1",
        role: "user",
        content: "Help me shape a research paper about fragmented narration in modernist fiction.",
        createdAt: now,
      },
      {
        id: "message-modernism-2",
        role: "assistant",
        content:
          "# Research direction\n\nA strong paper could compare how two modernist novels use fragmented narration to represent memory and social change.\n\n## Possible thesis\n\nFragmented form does more than imitate private thought: it asks readers to reconstruct the social pressures surrounding each character.\n\n- Define fragmentation with close textual examples.\n- Compare shifts in time and point of view.\n- Connect formal choices to the novels' historical settings.\n\n> The key question is not only what the narrators remember, but how the novels make remembering difficult.\n\nYou might use `narrative reconstruction` as a recurring analytical frame.",
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
    id: "project-short-story",
    title: "Short story notes",
    createdAt: now,
    updatedAt: now,
    messages: [
      {
        id: "message-story-1",
        role: "assistant",
        content:
          "## Notes to expand\n\n- A train station just before dawn\n- Two siblings meeting after ten years\n- A letter neither one admits to reading\n- The departure announcement interrupts the truth\n\nThe scene should stay restrained and let the setting carry the tension.",
        createdAt: now,
      },
    ],
  },
  {
    id: "project-literature-review",
    title: "Literature review",
    createdAt: now,
    updatedAt: now,
    messages: [],
  },
];

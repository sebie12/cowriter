import type { ReactNode } from "react";

type Block =
  | { type: "code"; content: string }
  | { type: "heading"; level: 1 | 2 | 3; content: string }
  | { type: "quote"; content: string }
  | { type: "list"; items: string[]; ordered: boolean; start?: number }
  | { type: "paragraph"; content: string };

function parseBlocks(content: string): Block[] {
  const lines = content.split("\n");
  const blocks: Block[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    if (!line.trim()) {
      index += 1;
      continue;
    }

    if (line.startsWith("```")) {
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].startsWith("```")) {
        codeLines.push(lines[index]);
        index += 1;
      }
      blocks.push({ type: "code", content: codeLines.join("\n") });
      index += 1;
      continue;
    }

    const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
    if (headingMatch) {
      blocks.push({
        type: "heading",
        level: headingMatch[1].length as 1 | 2 | 3,
        content: headingMatch[2],
      });
      index += 1;
      continue;
    }

    if (line.startsWith("> ")) {
      blocks.push({ type: "quote", content: line.slice(2) });
      index += 1;
      continue;
    }

    if (/^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line)) {
      const items: string[] = [];
      const ordered = /^\d+\.\s+/.test(line);
      const itemPattern = ordered ? /^\d+\.\s+/ : /^[-*]\s+/;
      const start = ordered ? Number.parseInt(line, 10) : undefined;
      while (index < lines.length && itemPattern.test(lines[index])) {
        items.push(lines[index].replace(itemPattern, ""));
        index += 1;
      }
      blocks.push({ type: "list", items, ordered, start });
      continue;
    }

    const paragraphLines = [line];
    index += 1;
    while (index < lines.length && lines[index].trim() && !/^(#{1,3})\s+/.test(lines[index]) && !/^[-*]\s+/.test(lines[index]) && !/^\d+\.\s+/.test(lines[index]) && !lines[index].startsWith("> ") && !lines[index].startsWith("```")) {
      paragraphLines.push(lines[index]);
      index += 1;
    }
    blocks.push({ type: "paragraph", content: paragraphLines.join(" ") });
  }

  return blocks;
}

function renderInlineCode(content: string): ReactNode[] {
  return content.split(/(`[^`]+`)/g).map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={`${part}-${index}`}>{part.slice(1, -1)}</code>;
    }

    return part;
  });
}

export function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="markdown-content">
      {parseBlocks(content).map((block, index) => {
        if (block.type === "code") {
          return (
            <pre key={index}>
              <code>{block.content}</code>
            </pre>
          );
        }

        if (block.type === "heading") {
          const HeadingTag = `h${block.level}` as "h1" | "h2" | "h3";
          return <HeadingTag key={index}>{renderInlineCode(block.content)}</HeadingTag>;
        }

        if (block.type === "quote") {
          return <blockquote key={index}>{renderInlineCode(block.content)}</blockquote>;
        }

        if (block.type === "list") {
          const ListTag = block.ordered ? "ol" : "ul";
          return (
            <ListTag key={index} start={block.ordered ? block.start : undefined}>
              {block.items.map((item, itemIndex) => (
                <li key={`${item}-${itemIndex}`}>{renderInlineCode(item)}</li>
              ))}
            </ListTag>
          );
        }

        return <p key={index}>{renderInlineCode(block.content)}</p>;
      })}
    </div>
  );
}

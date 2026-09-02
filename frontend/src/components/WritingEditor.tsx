import { useEffect } from "react";
import Document from "@tiptap/extension-document";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

interface WritingEditorProps {
  content: string;
  onChange: (content: string) => void;
}

const LatexDocument = Document.extend({
  content: "codeBlock",
});

function createLatexDocument(content: string) {
  return {
    type: "doc",
    content: [
      {
        type: "codeBlock",
        content: content ? [{ type: "text", text: content }] : [],
      },
    ],
  };
}

export function WritingEditor({ content, onChange }: WritingEditorProps) {
  const editor = useEditor({
    extensions: [
      LatexDocument,
      StarterKit.configure({
        document: false,
        blockquote: false,
        bold: false,
        bulletList: false,
        code: false,
        codeBlock: {
          enableTabIndentation: true,
          exitOnArrowDown: false,
          exitOnArrowUp: false,
          exitOnTripleEnter: false,
          tabSize: 2,
        },
        dropcursor: false,
        gapcursor: false,
        hardBreak: false,
        heading: false,
        horizontalRule: false,
        italic: false,
        link: false,
        listItem: false,
        listKeymap: false,
        orderedList: false,
        paragraph: false,
        strike: false,
        trailingNode: false,
        underline: false,
      }),
    ],
    content: createLatexDocument(content),
    editorProps: {
      attributes: {
        "aria-label": "LaTeX source",
        "aria-multiline": "true",
        autocapitalize: "off",
        autocomplete: "off",
        autocorrect: "off",
        role: "textbox",
        spellcheck: "false",
      },
    },
    onUpdate: ({ editor: currentEditor }) => {
      onChange(currentEditor.state.doc.firstChild?.textContent ?? "");
    },
  });

  useEffect(() => {
    if (!editor) {
      return;
    }
    const editorContent = editor.state.doc.firstChild?.textContent ?? "";
    if (editorContent !== content) {
      editor.commands.setContent(createLatexDocument(content), { emitUpdate: false });
    }
  }, [content, editor]);

  const lineCount = content.length === 0 ? 1 : content.split("\n").length;

  return (
    <section className="writing-stage" aria-label="LaTeX editor">
      <div className="writing-document">
        <div className="writing-document-bar">
          <span>LaTeX source</span>
          <span>{lineCount} {lineCount === 1 ? "line" : "lines"}</span>
        </div>
        <EditorContent className="latex-editor" editor={editor} />
      </div>
    </section>
  );
}

import { useEffect, useMemo, useRef, useState } from "react";
import { EditorContent, useEditor, useEditorState, type JSONContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import type { ReferencesState } from "../../hooks/useReferences";
import type { CowriterApi } from "../../services/backend/types";
import type { DraftDocument, Project, ProofreadIssue, ProofreadIssueType, ProofreadTopic } from "../../types";
import type { ProviderModel } from "../../types/providers";
import { ModelSelector, type ProviderOption } from "../composer/ModelSelector";
import { FeedbackPanel, type ReviewStatus } from "./FeedbackPanel";
import {
  extractDraftText,
  issueRange,
  ProofreadHighlights,
  quoteAt,
  rangeForOffsets,
  removeHighlightedIssue,
  setActiveIssue,
  setHighlightedIssues,
  type HighlightedIssue,
} from "./proofreadHighlights";

export interface ProofreadTarget {
  connectionId: number;
  provider: string;
  model: string;
}

export interface ModelSelectionProps {
  providers: ProviderOption[];
  activeProviderId: number | null;
  models: ProviderModel[];
  selectedModelId: string | null;
  isModelsLoading: boolean;
  modelsError: string | null;
  onSelectProvider: (id: number) => void;
  onSelectModel: (id: string) => void;
  onOpenSettings: () => void;
}

interface WorkTabProps {
  api: CowriterApi;
  project: Project;
  isActive: boolean;
  references: ReferencesState;
  proofreadTarget: ProofreadTarget | null;
  modelSelection: ModelSelectionProps;
  onDraftChange: (projectId: string, draft: DraftDocument) => void;
}

const EMPTY_DOCUMENT: DraftDocument = { type: "doc", content: [{ type: "paragraph" }] };

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function WorkTab({
  api,
  project,
  isActive,
  references,
  proofreadTarget,
  modelSelection,
  onDraftChange,
}: WorkTabProps) {
  const [issues, setIssues] = useState<ProofreadIssue[]>([]);
  const [liveIds, setLiveIds] = useState<Set<string>>(() => new Set());
  const [status, setStatus] = useState<ReviewStatus>("idle");
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [filter, setFilter] = useState<ProofreadIssueType | null>(null);
  const [essay, setEssay] = useState<{ file: string; truncated: boolean } | null>(null);
  const [topic, setTopic] = useState<ProofreadTopic | null>(null);
  const reviewControllerRef = useRef<AbortController | null>(null);
  const onIssueClickRef = useRef<(id: string) => void>(() => undefined);
  const projectId = project.id;
  const onDraftChangeRef = useRef(onDraftChange);
  onDraftChangeRef.current = onDraftChange;

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        code: false,
        codeBlock: false,
        heading: { levels: [1, 2, 3] },
        link: false,
        underline: false,
      }),
      ProofreadHighlights.configure({
        onIssuesChange: (ids) => setLiveIds(new Set(ids)),
        onIssueClick: (id) => onIssueClickRef.current(id),
      }),
    ],
    content: (project.draft ?? EMPTY_DOCUMENT) as JSONContent,
    editorProps: {
      attributes: {
        "aria-label": "Draft",
        "aria-multiline": "true",
        role: "textbox",
        spellcheck: "false",
        class: "draft-prose",
      },
    },
    onUpdate: ({ editor: currentEditor }) => {
      onDraftChangeRef.current(projectId, currentEditor.getJSON() as DraftDocument);
    },
  });

  const editorState = useEditorState({
    editor,
    selector: ({ editor: currentEditor }) => {
      if (!currentEditor) {
        return null;
      }
      const words = currentEditor.state.doc.textBetween(0, currentEditor.state.doc.content.size, " ", " ")
        .split(/\s+/)
        .filter(Boolean).length;
      return {
        words,
        bold: currentEditor.isActive("bold"),
        italic: currentEditor.isActive("italic"),
        heading: currentEditor.isActive("heading", { level: 2 }),
        bulletList: currentEditor.isActive("bulletList"),
        orderedList: currentEditor.isActive("orderedList"),
        blockquote: currentEditor.isActive("blockquote"),
      };
    },
  });

  useEffect(() => () => reviewControllerRef.current?.abort(), []);

  const openIssues = useMemo(
    () => issues.filter((issue) => liveIds.has(issue.id)),
    [issues, liveIds],
  );

  const focusIssue = (id: string | null) => {
    setActiveId(id);
    if (editor) {
      setActiveIssue(editor, id);
    }
  };

  const scrollToIssue = (id: string) => {
    if (!editor) {
      return;
    }
    focusIssue(id);
    const element = editor.view.dom.querySelector(`[data-issue-id="${CSS.escape(id)}"]`);
    element?.scrollIntoView({ block: "center", behavior: prefersReducedMotion() ? "auto" : "smooth" });
  };

  onIssueClickRef.current = (id) => {
    setFilter((current) => {
      const issue = issues.find((candidate) => candidate.id === id);
      return current && issue && issue.type !== current ? null : current;
    });
    focusIssue(id);
  };

  const review = async () => {
    if (!editor || !proofreadTarget || status === "reviewing") {
      return;
    }
    const draftText = extractDraftText(editor.state.doc);
    if (!draftText.text.trim()) {
      setStatus("error");
      setReviewError("Write something before asking for a review.");
      return;
    }

    const controller = new AbortController();
    reviewControllerRef.current?.abort();
    reviewControllerRef.current = controller;
    setStatus("reviewing");
    setReviewError(null);
    setActiveId(null);
    // Offsets refer to this exact text, so edits are paused until the review returns.
    editor.setEditable(false, false);

    try {
      const result = await api.proofread({
        projectId,
        connectionId: proofreadTarget.connectionId,
        provider: proofreadTarget.provider,
        model: proofreadTarget.model,
        text: draftText.text,
      }, controller.signal);

      setEssay(result.essayFile ? { file: result.essayFile, truncated: result.essayTruncated } : null);
      setTopic(result.topic);
      const highlighted: HighlightedIssue[] = [];
      for (const issue of result.issues) {
        const range = rangeForOffsets(draftText, issue.start, issue.end);
        if (range) {
          highlighted.push({
            id: issue.id,
            type: issue.type,
            ...range,
            quote: quoteAt(editor.state.doc, range.from, range.to),
          });
        }
      }
      const highlightedIds = new Set(highlighted.map((issue) => issue.id));
      setIssues(result.issues.filter((issue) => highlightedIds.has(issue.id)));
      setHighlightedIssues(editor, highlighted);
      setStatus("reviewed");
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return;
      }
      setStatus("error");
      setReviewError(error instanceof Error ? error.message : "Could not review the draft.");
    } finally {
      if (reviewControllerRef.current === controller) {
        reviewControllerRef.current = null;
      }
      if (!editor.isDestroyed) {
        editor.setEditable(true, false);
      }
    }
  };

  const applyIssue = (issue: ProofreadIssue) => {
    if (!editor || issue.suggestion === null) {
      return;
    }
    const range = issueRange(editor.state, issue.id);
    if (!range) {
      return;
    }
    const transaction = issue.suggestion
      ? editor.state.tr.insertText(issue.suggestion, range.from, range.to)
      : editor.state.tr.delete(range.from, range.to);
    editor.view.dispatch(transaction);
  };

  const dismissIssue = (issue: ProofreadIssue) => {
    if (editor) {
      removeHighlightedIssue(editor, issue.id);
    }
  };

  const modelLabel = proofreadTarget
    ? modelSelection.models.find((model) => model.id === proofreadTarget.model)?.name ?? proofreadTarget.model
    : null;

  return (
    <div
      id="project-work-panel"
      className="workspace-body work-body"
      role="tabpanel"
      aria-labelledby="project-work-tab"
      hidden={!isActive}
    >
      <div className="work-layout">
        <section className="draft-column" aria-label="Draft">
          <div className="draft-toolbar" role="toolbar" aria-label="Formatting">
            <div className="draft-format-buttons">
              <button
                type="button"
                aria-label="Bold"
                aria-pressed={editorState?.bold ?? false}
                onClick={() => editor?.chain().focus().toggleBold().run()}
              ><strong>B</strong></button>
              <button
                type="button"
                aria-label="Italic"
                aria-pressed={editorState?.italic ?? false}
                onClick={() => editor?.chain().focus().toggleItalic().run()}
              ><em>I</em></button>
              <button
                type="button"
                aria-label="Heading"
                aria-pressed={editorState?.heading ?? false}
                onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
              >H</button>
              <button
                type="button"
                aria-label="Bulleted list"
                aria-pressed={editorState?.bulletList ?? false}
                onClick={() => editor?.chain().focus().toggleBulletList().run()}
              >•</button>
              <button
                type="button"
                aria-label="Numbered list"
                aria-pressed={editorState?.orderedList ?? false}
                onClick={() => editor?.chain().focus().toggleOrderedList().run()}
              >1.</button>
              <button
                type="button"
                aria-label="Quote"
                aria-pressed={editorState?.blockquote ?? false}
                onClick={() => editor?.chain().focus().toggleBlockquote().run()}
              >”</button>
            </div>
            <span className="draft-word-count">
              {editorState?.words ?? 0} {editorState?.words === 1 ? "word" : "words"}
            </span>
            <div className="draft-review-controls">
              <ModelSelector
                providers={modelSelection.providers}
                activeProviderId={modelSelection.activeProviderId}
                models={modelSelection.models}
                selectedModelId={modelSelection.selectedModelId}
                isLoading={modelSelection.isModelsLoading}
                error={modelSelection.modelsError}
                disabled={status === "reviewing"}
                onOpenSettings={modelSelection.onOpenSettings}
                onSelectProvider={modelSelection.onSelectProvider}
                onSelectModel={modelSelection.onSelectModel}
              />
              <button
                type="button"
                className="review-button"
                disabled={!proofreadTarget || status === "reviewing"}
                title={proofreadTarget ? `Review with ${modelLabel}` : "Connect a provider and select a model first"}
                onClick={() => void review()}
              >
                {status === "reviewing" && <span className="review-spinner" aria-hidden="true" />}
                {status === "reviewing" ? "Reviewing…" : "Review draft"}
              </button>
            </div>
          </div>
          <div className="draft-scroll">
            <div className="draft-page">
              <EditorContent editor={editor} className="draft-editor" />
            </div>
          </div>
        </section>
        <FeedbackPanel
          issues={openIssues}
          status={status}
          error={reviewError}
          activeId={activeId}
          filter={filter}
          references={references.references}
          hasReferences={references.references.length > 0}
          essay={essay}
          topic={topic}
          hasProjectFolder={Boolean(project.path)}
          onFilterChange={setFilter}
          onHover={(id) => {
            if (editor) {
              setActiveIssue(editor, id ?? activeId);
            }
          }}
          onSelect={scrollToIssue}
          onApply={applyIssue}
          onDismiss={dismissIssue}
        />
      </div>
    </div>
  );
}

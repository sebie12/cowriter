import { Extension, type Editor } from "@tiptap/react";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { Plugin, PluginKey, type EditorState } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { ProofreadIssueType } from "../../types";

/** Separator placed between text blocks in the plain text sent for review. */
export const BLOCK_SEPARATOR = "\n\n";

function leafText(node: ProseMirrorNode): string {
  return node.type.name === "hardBreak" ? "\n" : "";
}

export interface DraftText {
  text: string;
  /** `positions[i]` is the document position of `text[i]`. */
  positions: number[];
}

/**
 * Mirrors `doc.textBetween(0, size, BLOCK_SEPARATOR, leafText)` while recording
 * the document position of every character, so review offsets map back to the editor.
 */
export function extractDraftText(doc: ProseMirrorNode): DraftText {
  let text = "";
  const positions: number[] = [];
  let first = true;
  doc.descendants((node, pos) => {
    const nodeText = node.isText ? node.text ?? "" : node.isLeaf ? leafText(node) : "";
    if (node.isBlock && ((node.isLeaf && nodeText) || node.isTextblock)) {
      if (first) {
        first = false;
      } else {
        text += BLOCK_SEPARATOR;
        // Separator characters sit just inside the start of the following block.
        for (let index = 0; index < BLOCK_SEPARATOR.length; index += 1) {
          positions.push(pos + 1);
        }
      }
    }
    for (let index = 0; index < nodeText.length; index += 1) {
      positions.push(node.isText ? pos + index : pos);
    }
    text += nodeText;
    return true;
  });
  return { text, positions };
}

export function rangeForOffsets(
  draftText: DraftText,
  start: number,
  end: number,
): { from: number; to: number } | null {
  if (start < 0 || end > draftText.text.length || end <= start) {
    return null;
  }
  const from = draftText.positions[start];
  const to = draftText.positions[end - 1] + 1;
  return from < to ? { from, to } : null;
}

export interface HighlightedIssue {
  id: string;
  type: ProofreadIssueType;
  from: number;
  to: number;
  quote: string;
}

interface IssueSpec {
  id: string;
  quote: string;
}

interface HighlightState {
  decorations: DecorationSet;
  activeId: string | null;
}

type HighlightMeta =
  | { action: "set"; issues: HighlightedIssue[] }
  | { action: "remove"; id: string }
  | { action: "active"; id: string | null };

export const proofreadHighlightsKey = new PluginKey<HighlightState>("proofreadHighlights");

export function quoteAt(doc: ProseMirrorNode, from: number, to: number): string {
  return doc.textBetween(from, to, BLOCK_SEPARATOR, leafText);
}

function idsOf(decorations: DecorationSet): string[] {
  return decorations.find().map((decoration) => (decoration.spec as IssueSpec).id);
}

export interface ProofreadHighlightsOptions {
  /** Called with the ids still highlighted whenever the set changes (edits clear stale issues). */
  onIssuesChange: (ids: string[]) => void;
  onIssueClick: (id: string) => void;
}

export const ProofreadHighlights = Extension.create<ProofreadHighlightsOptions>({
  name: "proofreadHighlights",

  addOptions() {
    return {
      onIssuesChange: () => undefined,
      onIssueClick: () => undefined,
    };
  },

  addProseMirrorPlugins() {
    const options = this.options;
    return [
      new Plugin<HighlightState>({
        key: proofreadHighlightsKey,
        state: {
          init: () => ({ decorations: DecorationSet.empty, activeId: null }),
          apply(tr, value, _oldState, newState) {
            const meta = tr.getMeta(proofreadHighlightsKey) as HighlightMeta | undefined;
            let { decorations, activeId } = value;

            if (tr.docChanged) {
              decorations = decorations.map(tr.mapping, tr.doc);
              // An issue is stale once its text no longer matches what was reviewed.
              const stale = decorations.find().filter((decoration) => (
                quoteAt(newState.doc, decoration.from, decoration.to) !== (decoration.spec as IssueSpec).quote
              ));
              if (stale.length > 0) {
                decorations = decorations.remove(stale);
              }
            }

            if (meta?.action === "set") {
              decorations = DecorationSet.create(
                newState.doc,
                meta.issues.map((issue) => Decoration.inline(
                  issue.from,
                  issue.to,
                  { class: `issue issue--${issue.type}`, "data-issue-id": issue.id },
                  { id: issue.id, quote: issue.quote } satisfies IssueSpec,
                )),
              );
              activeId = null;
            } else if (meta?.action === "remove") {
              decorations = decorations.remove(
                decorations.find(undefined, undefined, (spec) => (spec as IssueSpec).id === meta.id),
              );
            } else if (meta?.action === "active") {
              activeId = meta.id;
            }

            if (activeId && !idsOf(decorations).includes(activeId)) {
              activeId = null;
            }
            return { decorations, activeId };
          },
        },
        props: {
          decorations(state) {
            const pluginState = proofreadHighlightsKey.getState(state);
            if (!pluginState) {
              return null;
            }
            if (!pluginState.activeId) {
              return pluginState.decorations;
            }
            const active = pluginState.decorations
              .find(undefined, undefined, (spec) => (spec as IssueSpec).id === pluginState.activeId)
              .map((decoration) => Decoration.inline(decoration.from, decoration.to, { class: "issue--active" }));
            return pluginState.decorations.add(state.doc, active);
          },
          handleClick(view, pos) {
            const pluginState = proofreadHighlightsKey.getState(view.state);
            const hit = pluginState?.decorations.find(pos, pos)[0];
            if (hit) {
              options.onIssueClick((hit.spec as IssueSpec).id);
            }
            return false;
          },
        },
        view() {
          let previousIds = "";
          return {
            update(view) {
              const pluginState = proofreadHighlightsKey.getState(view.state);
              const ids = pluginState ? idsOf(pluginState.decorations) : [];
              const key = ids.join("|");
              if (key !== previousIds) {
                previousIds = key;
                options.onIssuesChange(ids);
              }
            },
          };
        },
      }),
    ];
  },
});

function dispatchMeta(editor: Editor, meta: HighlightMeta) {
  editor.view.dispatch(editor.state.tr.setMeta(proofreadHighlightsKey, meta));
}

export function setHighlightedIssues(editor: Editor, issues: HighlightedIssue[]) {
  dispatchMeta(editor, { action: "set", issues });
}

export function removeHighlightedIssue(editor: Editor, id: string) {
  dispatchMeta(editor, { action: "remove", id });
}

export function setActiveIssue(editor: Editor, id: string | null) {
  const current = proofreadHighlightsKey.getState(editor.state)?.activeId ?? null;
  if (current !== id) {
    dispatchMeta(editor, { action: "active", id });
  }
}

export function issueRange(state: EditorState, id: string): { from: number; to: number } | null {
  const decoration = proofreadHighlightsKey.getState(state)?.decorations
    .find(undefined, undefined, (spec) => (spec as IssueSpec).id === id)[0];
  return decoration ? { from: decoration.from, to: decoration.to } : null;
}

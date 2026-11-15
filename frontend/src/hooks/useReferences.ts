import { useCallback, useEffect, useMemo, useState } from "react";
import type { CowriterApi } from "../services/backend/types";
import type { Paper, Reference } from "../types";

export interface ReferencesState {
  references: Reference[];
  referenceByPaperId: Map<string, Reference>;
  isLoading: boolean;
  error: string | null;
  pendingPaperIds: Set<string>;
  save: (paper: Paper) => Promise<void>;
  remove: (reference: Reference) => Promise<void>;
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function useReferences(api: CowriterApi, projectId: string | null): ReferencesState {
  const [references, setReferences] = useState<Reference[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingPaperIds, setPendingPaperIds] = useState<Set<string>>(() => new Set());

  const reload = useCallback((signal?: AbortSignal) => {
    if (!projectId) {
      return Promise.resolve();
    }
    return api.listReferences(projectId, signal).then((loaded) => {
      setReferences(loaded);
      setError(null);
    });
  }, [api, projectId]);

  useEffect(() => {
    setReferences([]);
    setError(null);
    if (!projectId) {
      return;
    }
    const controller = new AbortController();
    setIsLoading(true);
    reload(controller.signal)
      .catch((loadError) => {
        if (loadError instanceof Error && loadError.name === "AbortError") {
          return;
        }
        setError(errorMessage(loadError, "Could not load saved references."));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      });
    return () => controller.abort();
  }, [projectId, reload]);

  const markPending = (paperId: string, pending: boolean) => {
    setPendingPaperIds((current) => {
      const next = new Set(current);
      if (pending) {
        next.add(paperId);
      } else {
        next.delete(paperId);
      }
      return next;
    });
  };

  const save = async (paper: Paper) => {
    if (!projectId) {
      return;
    }
    markPending(paper.paperId, true);
    try {
      const reference = await api.saveReference(projectId, paper);
      setReferences((current) => [...current.filter((item) => item.id !== reference.id), reference]);
      setError(null);
    } catch (saveError) {
      // A 409 means it was saved elsewhere; refresh so the UI reflects the server.
      await reload().catch(() => undefined);
      setError(errorMessage(saveError, "Could not save the reference."));
    } finally {
      markPending(paper.paperId, false);
    }
  };

  const remove = async (reference: Reference) => {
    if (!projectId) {
      return;
    }
    markPending(reference.paperId, true);
    try {
      await api.deleteReference(projectId, reference.id);
      setReferences((current) => current.filter((item) => item.id !== reference.id));
      setError(null);
    } catch (removeError) {
      setError(errorMessage(removeError, "Could not remove the reference."));
    } finally {
      markPending(reference.paperId, false);
    }
  };

  const referenceByPaperId = useMemo(
    () => new Map(references.map((reference) => [reference.paperId, reference])),
    [references],
  );

  return { references, referenceByPaperId, isLoading, error, pendingPaperIds, save, remove };
}

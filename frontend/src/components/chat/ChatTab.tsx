import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Project } from "../../types";
import { Composer, type ComposerProps } from "../composer/Composer";
import { Conversation } from "../Conversation";

const NEAR_BOTTOM_THRESHOLD = 96;

interface ChatTabProps {
  project: Project;
  isActive: boolean;
  isThinking: boolean;
  canDeleteChat: boolean;
  onDeleteChat: () => Promise<void>;
  composer: ComposerProps;
}

export function ChatTab({
  project,
  isActive,
  isThinking,
  canDeleteChat,
  onDeleteChat,
  composer,
}: ChatTabProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const scrollContentRef = useRef<HTMLDivElement | null>(null);
  const isNearBottomRef = useRef(true);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const previousProjectIdRef = useRef<string | null>(null);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const hasChat = project.conversationItems.length > 0;

  useEffect(() => {
    setIsConfirmingDelete(false);
  }, [project.id, isActive]);

  const deleteChat = async () => {
    setIsDeleting(true);
    try {
      await onDeleteChat();
    } finally {
      setIsDeleting(false);
      setIsConfirmingDelete(false);
    }
  };

  const scrollToBottom = () => {
    const scrollContainer = scrollRef.current;
    if (scrollContainer) {
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
    }
  };

  useLayoutEffect(() => {
    if (project.id !== previousProjectIdRef.current) {
      previousProjectIdRef.current = project.id;
      isNearBottomRef.current = true;
      setIsNearBottom(true);
    }
    if (isActive && isNearBottomRef.current) {
      scrollToBottom();
    }
  }, [isActive, project.id, project.conversationItems, isThinking]);

  useEffect(() => {
    const scrollContainer = scrollRef.current;
    const scrollContent = scrollContentRef.current;
    if (!isActive || !scrollContainer || !scrollContent) {
      return;
    }

    const observer = new ResizeObserver(() => {
      if (isNearBottomRef.current) {
        scrollToBottom();
      }
    });
    observer.observe(scrollContainer);
    observer.observe(scrollContent);
    return () => observer.disconnect();
  }, [isActive]);

  return (
    <div
      id="project-chat-panel"
      ref={scrollRef}
      className="workspace-body"
      role="tabpanel"
      aria-labelledby="project-chat-tab"
      hidden={!isActive}
      data-conversation-scroll
      onScroll={(event) => {
        const scrollContainer = event.currentTarget;
        const distanceFromBottom = scrollContainer.scrollHeight
          - scrollContainer.clientHeight
          - scrollContainer.scrollTop;
        isNearBottomRef.current = distanceFromBottom <= NEAR_BOTTOM_THRESHOLD;
        setIsNearBottom(isNearBottomRef.current);
      }}
    >
      {hasChat && (
        <div className="chat-toolbar">
          {isConfirmingDelete ? (
            <div className="chat-delete-confirm" role="group" aria-label="Confirm chat deletion">
              <span>Delete this chat and its tool history?</span>
              <button
                className="chat-toolbar-button"
                type="button"
                disabled={isDeleting}
                onClick={() => setIsConfirmingDelete(false)}
              >
                Cancel
              </button>
              <button
                className="chat-toolbar-button chat-toolbar-danger"
                type="button"
                disabled={isDeleting}
                onClick={() => void deleteChat()}
              >
                {isDeleting ? "Deleting…" : "Delete"}
              </button>
            </div>
          ) : (
            <button
              className="chat-toolbar-button"
              type="button"
              disabled={!canDeleteChat}
              title={canDeleteChat ? undefined : "Wait for the reply to finish"}
              onClick={() => setIsConfirmingDelete(true)}
            >
              Delete chat
            </button>
          )}
        </div>
      )}
      <div ref={scrollContentRef} className="workspace-scroll-content">
        <Conversation items={project.conversationItems} isSending={isThinking} />
      </div>
      {!isNearBottom && (
        <div className="scroll-to-bottom-slot">
          <button
            className="scroll-to-bottom"
            type="button"
            aria-label="Jump to latest message"
            onClick={() => {
              isNearBottomRef.current = true;
              setIsNearBottom(true);
              scrollToBottom();
            }}
          >
            <span aria-hidden="true">↓</span>
          </button>
        </div>
      )}
      <div className="composer-seat">
        <Composer {...composer} />
      </div>
    </div>
  );
}

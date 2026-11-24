/**
 * Robotstudio - Visual Robot Framework Authoring Platform
 * BlocklyEditor Component
 *
 * Embeds a Blockly workspace for visual Robot Framework authoring. The canvas
 * document is the source of truth: the workspace is loaded from it when the
 * selected suite changes, and every edit is converted back into a document and
 * reported through `onChange`.
 *
 * @packageDocumentation
 */

import React, { useEffect, useMemo, useRef, useState } from "react";
import * as Blockly from "blockly";
import { allBlocks, blockCategories, expertCategories } from "../blocks/definitions";
import { emptyDocument, modelToWorkspace, workspaceToModel } from "../blocks/serialization";
import type { BlocklyState } from "../blocks/serialization";
import type { CanvasDocument } from "../types/canvas";

/** A keyword from the catalog, as shown in the toolbox. */
export interface KeywordOption {
  name: string;
  library: string;
  category: string;
  curated?: boolean;
}

interface BlocklyEditorProps {
  /** Document shown in the workspace; also the base for settings the canvas does not edit. */
  initialDocument?: CanvasDocument;
  /** Identifies the open suite. The workspace reloads only when this changes. */
  documentKey?: string;
  /** Called with the updated document after every edit. */
  onChange?: (document: CanvasDocument) => void;
  /** Make the workspace read-only. */
  readonly?: boolean;
  /** Offer every catalog keyword instead of the curated set. */
  expertMode?: boolean;
  /** Keywords from the catalog. */
  keywordOptions?: KeywordOption[];
}

// Blockly throws when a block type is registered twice, so registration happens
// once per page load, outside the React lifecycle.
let registered = false;

function ensureBlocklyRegistered(): void {
  if (registered) return;
  Blockly.defineBlocksWithJsonArray(allBlocks);
  registered = true;
}

/**
 * Builds the toolbox: the structural blocks, then keyword calls grouped by
 * category. Only curated keywords are listed unless expert mode is on.
 */
function buildToolbox(expertMode: boolean, keywordOptions: KeywordOption[]): Blockly.utils.toolbox.ToolboxInfo {
  const categories = expertMode ? expertCategories : blockCategories;

  const keywordGroups = new Map<string, KeywordOption[]>();
  for (const keyword of keywordOptions) {
    if (!expertMode && !keyword.curated) continue;
    const group = keyword.category || keyword.library;
    keywordGroups.set(group, [...(keywordGroups.get(group) ?? []), keyword]);
  }

  const contents: Blockly.utils.toolbox.ToolboxItemInfo[] = [
    {
      kind: "category",
      name: "Structure",
      colour: "#009688",
      contents: ["robot_test", "robot_keyword", "robot_library"].map((type) => ({ kind: "block", type })),
    },
    ...[...keywordGroups.entries()].map(([name, keywords]) => ({
      kind: "category",
      name,
      colour: "#4CAF50",
      contents: keywords.map((keyword) => ({
        kind: "block",
        type: "robot_call",
        fields: { KEYWORD: keyword.name },
      })),
    })),
    ...Object.entries(categories).map(([name, types]) => ({
      kind: "category",
      name,
      contents: types.map((type) => ({ kind: "block", type })),
    })),
  ];

  if (keywordGroups.size === 0) {
    contents.splice(1, 0, {
      kind: "category",
      name: "Keywords",
      colour: "#4CAF50",
      contents: [{ kind: "block", type: "robot_call" }],
    });
  }

  return { kind: "categoryToolbox", contents };
}

/** Embedded Blockly workspace for Robot Framework authoring. */
export const BlocklyEditor: React.FC<BlocklyEditorProps> = ({
  initialDocument,
  documentKey,
  onChange,
  readonly = false,
  expertMode = false,
  keywordOptions = [],
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const workspaceRef = useRef<Blockly.WorkspaceSvg | null>(null);
  const onChangeRef = useRef(onChange);
  const documentRef = useRef<CanvasDocument | undefined>(initialDocument);
  const loadedKeyRef = useRef<string | null>(null);
  const appliedToolboxRef = useRef<unknown>(null);
  const [ready, setReady] = useState(false);

  onChangeRef.current = onChange;
  if (initialDocument) documentRef.current = initialDocument;

  const toolbox = useMemo(() => buildToolbox(expertMode, keywordOptions), [expertMode, keywordOptions]);
  const toolboxRef = useRef(toolbox);
  toolboxRef.current = toolbox;

  useEffect(() => {
    if (!containerRef.current) return;

    ensureBlocklyRegistered();
    const workspace = Blockly.inject(containerRef.current, {
      toolbox: toolboxRef.current,
      trashcan: true,
      zoom: { controls: true, wheel: true, startScale: 1, maxScale: 3, minScale: 0.3, scaleSpeed: 1.2 },
      grid: { spacing: 20, length: 3, colour: "#ccc", snap: true },
      renderer: "zelos",
      theme: Blockly.Themes.Classic,
      readOnly: readonly,
      sounds: false,
    });
    appliedToolboxRef.current = toolboxRef.current;

    workspace.addChangeListener((event: Blockly.Events.Abstract) => {
      const notify = onChangeRef.current;
      // Selecting, scrolling or zooming does not change the document.
      if (!notify || event.isUiEvent || workspace.isDragging()) return;
      const state = Blockly.serialization.workspaces.save(workspace) as BlocklyState;
      notify(workspaceToModel(state, documentRef.current ?? emptyDocument()));
    });

    workspaceRef.current = workspace;
    loadedKeyRef.current = null;
    setReady(true);

    return () => {
      workspace.dispose();
      workspaceRef.current = null;
      setReady(false);
    };
  }, [readonly]);

  // Load the canvas only when the selected suite changes, never on the echo of
  // our own onChange.
  useEffect(() => {
    const workspace = workspaceRef.current;
    if (!workspace || !ready) return;

    const key = documentKey ?? "default";
    if (loadedKeyRef.current === key) return;
    loadedKeyRef.current = key;

    // Loading creates every block as an event; none of them is a user edit.
    Blockly.Events.disable();
    try {
      workspace.clear();
      Blockly.serialization.workspaces.load(modelToWorkspace(documentRef.current ?? emptyDocument()), workspace);
      workspace.cleanUp();
    } finally {
      Blockly.Events.enable();
    }
  }, [documentKey, ready]);

  useEffect(() => {
    const workspace = workspaceRef.current;
    if (!workspace || !ready || appliedToolboxRef.current === toolbox) return;
    workspace.updateToolbox(toolbox);
    appliedToolboxRef.current = toolbox;
  }, [toolbox, ready]);

  const downloadWorkspace = () => {
    const workspace = workspaceRef.current;
    if (!workspace) return;
    const json = Blockly.serialization.workspaces.save(workspace);
    const blob = new Blob([JSON.stringify(json, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "workspace.blockly.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="blockly-editor">
      <div className="blockly-toolbar">
        <button onClick={downloadWorkspace} disabled={!ready}>
          Download Workspace JSON
        </button>
        <span className="status">{ready ? "Ready" : "Initializing..."}</span>
      </div>
      <div ref={containerRef} className="blockly-workspace" />
    </div>
  );
};

export default BlocklyEditor;

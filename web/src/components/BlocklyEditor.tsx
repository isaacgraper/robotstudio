/**
 * Robotstudio - Visual Robot Framework Authoring Platform
 * BlocklyEditor Component
 *
 * A React component that embeds a Blockly workspace for visual Robot Framework
 * suite authoring. Handles block registration, mutator management, workspace
 * serialization, and dynamic keyword dropdowns from the catalog.
 *
 * @packageDocumentation
 */

import React, { useEffect, useMemo, useRef, useState } from "react";
import * as Blockly from "blockly";
import { allBlocks, containerBlocks, blockCategories, expertCategories } from "../blocks/definitions";
import { ifMutator, tryMutator, callMutator } from "../blocks/mutators";
import { modelToWorkspace, workspaceToModel } from "../blocks/serialization";
import { setTargetWorkspace } from "../blocks/definitions";
import type { CanvasDocument } from "../types/canvas";

/**
 * Props for the BlocklyEditor component.
 */
interface BlocklyEditorProps {
  /** Initial canvas document to load into the workspace. */
  initialDocument?: CanvasDocument;
  /** Key identifying the current document; change triggers workspace reload. */
  documentKey?: string;
  /** Callback fired when the workspace content changes. */
  onChange?: (document: CanvasDocument) => void;
  /** Whether the workspace should be read-only. */
  readonly?: boolean;
  /** Enable expert mode with full category set. */
  expertMode?: boolean;
  /** Keyword options for the dynamic call block dropdown. */
  keywordOptions?: Array<{ name: string; library: string; category: string }>;
}

// Blockly throws when a block or extension is registered twice, so registration
// happens exactly once per page load, outside the React lifecycle.
let registered = false;

/**
 * Registers all custom blocks and mutators with Blockly.
 * Called once per session on first workspace injection.
 */
function ensureBlocklyRegistered(): void {
  if (registered) return;
  Blockly.defineBlocksWithJsonArray(allBlocks);
  Blockly.defineBlocksWithJsonArray(Object.values(containerBlocks));
  Blockly.Extensions.registerMutator("if_mutator", ifMutator, undefined, [
    "robot_if_container",
    "robot_if_elseif",
    "robot_if_else",
  ]);
  Blockly.Extensions.registerMutator("try_mutator", tryMutator, undefined, [
    "robot_try_container",
    "robot_try_except",
    "robot_try_else",
    "robot_try_finally",
  ]);
  Blockly.Extensions.registerMutator("call_mutator", callMutator, undefined, [
    "robot_call_args_container",
  ]);
  registered = true;
}

/**
 * BlocklyEditor - Embedded Blockly workspace for Robot Framework authoring.
 *
 * Renders a Blockly workspace with custom Robot Framework blocks, dynamic
 * keyword dropdowns, and mutators for control flow structures.
 *
 * @param initialDocument - Canvas document to load initially
 * @param documentKey - Key that triggers workspace reload when changed
 * @param onChange - Callback receiving the updated CanvasDocument
 * @param readonly - If true, workspace is read-only
 * @param expertMode - If true, shows all block categories
 * @param keywordOptions - Keywords available in the call block dropdown
 * @returns React element containing the Blockly workspace
 */
export const BlocklyEditor: React.FC<BlocklyEditorProps> = ({
  initialDocument,
  documentKey,
  onChange,
  readonly = false,
  expertMode = false,
  keywordOptions = [],
}) => {
  const workspaceRef = useRef<HTMLDivElement>(null);
  const blocklyRef = useRef<Blockly.WorkspaceSvg | null>(null);
  const onChangeRef = useRef(onChange);
  const documentRef = useRef(initialDocument);
  const loadedKeyRef = useRef<string | null>(null);
  const [ready, setReady] = useState(false);

  onChangeRef.current = onChange;
  if (initialDocument) documentRef.current = initialDocument;

  const toolbox = useMemo(
    () => buildToolbox(expertMode, keywordOptions),
    [expertMode, keywordOptions]
  );
  const toolboxRef = useRef(toolbox);
  toolboxRef.current = toolbox;

  useEffect(() => {
    if (!workspaceRef.current) return;

    ensureBlocklyRegistered();
    const ws = Blockly.inject(workspaceRef.current, {
      toolbox: toolboxRef.current,
      trashcan: true,
      zoom: { controls: true, wheel: true, startScale: 1, maxScale: 3, minScale: 0.3, scaleSpeed: 1.2 },
      grid: { spacing: 20, length: 3, colour: "#ccc", snap: true },
      renderer: "zelos",
      theme: Blockly.Themes.Classic,
      readOnly: readonly,
      sounds: false,
    });

    // Attach keyword options to the workspace for dynamic dropdowns
    (ws as any).targetKeywords = keywordOptions;
    setTargetWorkspace(ws);

    blocklyRef.current = ws;
    loadedKeyRef.current = null;

    ws.addChangeListener(() => {
      const notify = onChangeRef.current;
      if (!notify || ws.isDragging()) return;
      const workspaceJson = Blockly.serialization.workspaces.save(ws);
      notify(workspaceToModel(workspaceJson as any, documentRef.current?.name || "Untitled"));
    });

    setReady(true);

    return () => {
      ws.dispose();
      blocklyRef.current = null;
      setReady(false);
    };
  }, [readonly]);

  // Reload the canvas only when the selected suite changes, never on the echo of
  // our own onChange callback.
  useEffect(() => {
    const ws = blocklyRef.current;
    if (!ws || !ready) return;

    const key = documentKey ?? "default";
    if (loadedKeyRef.current === key) return;
    loadedKeyRef.current = key;

    ws.clear();
    const document = documentRef.current;
    if (document) {
      Blockly.serialization.workspaces.load(modelToWorkspace(document) as any, ws);
    } else {
      const suiteBlock = ws.newBlock("robot_suite");
      suiteBlock.initSvg();
      suiteBlock.moveBy(50, 50);
    }
  }, [documentKey, ready, initialDocument]);

  useEffect(() => {
    blocklyRef.current?.updateToolbox(toolbox);
    if (blocklyRef.current) {
      (blocklyRef.current as any).targetKeywords = keywordOptions;
    }
    setTargetWorkspace(blocklyRef.current);
  }, [toolbox]);

  const downloadWorkspace = () => {
    const ws = blocklyRef.current;
    if (!ws) return;
    const json = Blockly.serialization.workspaces.save(ws);
    const blob = new Blob([JSON.stringify(json, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "workspace.blockly.json";
    a.click();
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
      <div ref={workspaceRef} className="blockly-workspace" />
    </div>
  );
};

/**
 * Builds the Blockly toolbox configuration.
 *
 * @param expertMode - Whether to use expert categories
 * @param keywordOptions - Keywords for the dynamic call block dropdown
 * @returns Toolbox configuration object
 */
function buildToolbox(expertMode: boolean, keywordOptions: Array<{ name: string; library: string; category: string }>): any {
  const categories = expertMode ? expertCategories : blockCategories;

  const keywordBlocks = keywordOptions.map((kw) => ({
    kind: "block",
    type: "robot_call",
    fields: { KEYWORD: kw.name },
  }));

  const suiteBlock = {
    kind: "block",
    type: "robot_suite",
  };

  const testBlock = {
    kind: "block",
    type: "robot_test",
  };

  const keywordBlock = {
    kind: "block",
    type: "robot_keyword",
  };

  const libraryBlock = {
    kind: "block",
    type: "robot_library",
  };

  const categoriesXml: any[] = [
    { kind: "category", name: "Suite", contents: [suiteBlock, testBlock, keywordBlock, libraryBlock] },
    { kind: "category", name: "Keywords", contents: keywordBlocks.length > 0 ? keywordBlocks : [{ kind: "label", text: "Load a catalog to see keywords" }] },
  ];

  Object.entries(categories).forEach(([catName, blocks]) => {
    categoriesXml.push({
      kind: "category",
      name: catName,
      contents: blocks.map((type) => ({ kind: "block", type })),
    });
  });

  return { kind: "categoryToolbox", contents: categoriesXml };
}

export default BlocklyEditor;

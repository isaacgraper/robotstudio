import React, { useEffect, useRef, useState, useCallback } from "react";
import * as Blockly from "blockly";
import { allBlocks, containerBlocks, blockCategories, expertCategories } from "../blocks/definitions";
import { mutators } from "../blocks/mutators";
import { modelToWorkspace, workspaceToModel } from "../blocks/serialization";
import type { CanvasDocument } from "../types/canvas";

interface BlocklyEditorProps {
  initialDocument?: CanvasDocument;
  onChange?: (document: CanvasDocument) => void;
  readonly?: boolean;
  expertMode?: boolean;
  keywordOptions?: Array<{ name: string; library: string; category: string }>;
}

export const BlocklyEditor: React.FC<BlocklyEditorProps> = ({
  initialDocument,
  onChange,
  readonly = false,
  expertMode = false,
  keywordOptions = [],
}) => {
  const workspaceRef = useRef<HTMLDivElement>(null);
  const blocklyWorkspaceRef = useRef<Blockly.WorkspaceSvg | null>(null);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (!workspaceRef.current || initialized) return;

    const ws = Blockly.inject(workspaceRef.current, {
      toolbox: buildToolbox(expertMode, keywordOptions),
      trashcan: true,
      zoom: { controls: true, wheel: true, startScale: 1, maxScale: 3, minScale: 0.3, scaleSpeed: 1.2 },
      grid: { spacing: 20, length: 3, colour: "#ccc", snap: true },
      renderer: "zelos",
      theme: Blockly.Themes.Classic,
      readOnly: readonly,
      sounds: false,
    });

    registerBlocks();
    registerMutators();
    blocklyWorkspaceRef.current = ws;

    if (initialDocument) {
      loadDocument(ws, initialDocument);
    } else {
      createDefaultStructure(ws);
    }

    ws.addChangeListener(() => {
      if (onChange && !ws.isDragging()) {
        const workspaceJson = Blockly.serialization.workspaces.save(ws);
        const doc = workspaceToModel(workspaceJson as any, initialDocument?.name || "Untitled");
        onChange(doc);
      }
    });

    setInitialized(true);

    return () => {
      ws.dispose();
      blocklyWorkspaceRef.current = null;
      setInitialized(false);
    };
  }, [initialized, readonly, expertMode, keywordOptions]);

  const registerBlocks = () => {
    Blockly.defineBlocksWithJsonArray(allBlocks);
    Blockly.defineBlocksWithJsonArray(Object.values(containerBlocks));
  };

  const registerMutators = () => {
    Object.entries(mutators).forEach(([name, mutator]) => {
      Blockly.Extensions.register(name, mutator as any);
    });
  };

  const loadDocument = (ws: Blockly.WorkspaceSvg, document: CanvasDocument) => {
    const workspaceJson = modelToWorkspace(document);
    Blockly.serialization.workspaces.load(workspaceJson as any, ws);
  };

  const createDefaultStructure = (ws: Blockly.WorkspaceSvg) => {
    const suiteBlock = ws.newBlock("robot_suite");
    suiteBlock.initSvg();
    suiteBlock.moveBy(50, 50);
  };

  const getWorkspaceJson = useCallback(() => {
    if (!blocklyWorkspaceRef.current) return null;
    return Blockly.serialization.workspaces.save(blocklyWorkspaceRef.current);
  }, []);

  const downloadWorkspace = useCallback(() => {
    const json = getWorkspaceJson();
    if (!json) return;
    const blob = new Blob([JSON.stringify(json, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "workspace.blockly.json";
    a.click();
    URL.revokeObjectURL(url);
  }, [getWorkspaceJson]);

  return (
    <div className="blockly-editor">
      <div className="blockly-toolbar">
        <button onClick={downloadWorkspace} disabled={!initialized}>
          Download Workspace JSON
        </button>
        <span className="status">{initialized ? "Ready" : "Initializing..."}</span>
      </div>
      <div ref={workspaceRef} className="blockly-workspace" />
    </div>
  );
};

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
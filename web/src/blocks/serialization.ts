/**
 * Robotstudio - Visual Robot Framework Authoring Platform
 * Workspace Serialization
 *
 * Converts between the canonical `CanvasDocument` and Blockly's workspace JSON
 * (`Blockly.serialization.workspaces`). Blockly nests statements: a block's
 * `inputs.X.block` is the first block of a statement input and `next.block`
 * chains the blocks after it. IF/ELSE IF/ELSE and TRY/EXCEPT/ELSE/FINALLY are
 * sibling blocks in that chain, grouped back together when reading.
 *
 * Lists typed into a single text field use fixed separators: commas for tags,
 * assignment targets, EXCEPT patterns and FOR variables, and two spaces (Robot
 * Framework's own cell separator) for FOR values, RETURN values and keyword
 * arguments.
 *
 * @packageDocumentation
 */

import type {
  Argument,
  CallStep,
  CanvasDocument,
  ExceptClause,
  ForStep,
  IfStep,
  KeywordDefinition,
  LibraryImport,
  Step,
  TestCase,
  TryStep,
  WhileStep,
} from "../types/canvas";

/** Blockly workspace state as produced by `serialization.workspaces.save`. */
export interface BlocklyState {
  blocks?: {
    languageVersion?: number;
    blocks?: BlocklyBlock[];
  };
}

/** One serialized Blockly block. */
export interface BlocklyBlock {
  type: string;
  id?: string;
  x?: number;
  y?: number;
  fields?: Record<string, string | number | boolean>;
  inputs?: Record<string, { block?: BlocklyBlock }>;
  next?: { block?: BlocklyBlock };
  data?: string;
}

const CELL_SEPARATOR = "  ";
/**
 * Blockly's core has no multi-line text field, so line breaks inside a single
 * text field are shown as this marker and restored when reading.
 */
const LINE_BREAK = " \u23ce ";
const SCOPES = new Set(["TEST", "TASK", "SUITE", "GLOBAL"]);

/** An empty document, used when nothing has been loaded yet. */
export function emptyDocument(name = "Untitled"): CanvasDocument {
  return {
    version: 1,
    name,
    settings: {
      documentation: "",
      libraries: [],
      resources: [],
      variables: [],
      suite_setup: null,
      suite_teardown: null,
      test_setup: null,
      test_teardown: null,
      force_tags: [],
      default_tags: [],
      test_timeout: null,
      metadata: {},
    },
    tests: [],
    keywords: [],
  };
}

// ---------------------------------------------------------------------------
// Reading helpers
// ---------------------------------------------------------------------------

function field(block: BlocklyBlock, name: string): string {
  return String(block.fields?.[name] ?? "");
}

function flag(block: BlocklyBlock, name: string): boolean {
  const value = block.fields?.[name];
  return value === true || value === "TRUE" || value === "true";
}

/** The block followed by everything chained after it with `next`. */
function chain(first: BlocklyBlock | undefined): BlocklyBlock[] {
  const blocks: BlocklyBlock[] = [];
  for (let current = first; current; current = current.next?.block) {
    blocks.push(current);
  }
  return blocks;
}

function statements(block: BlocklyBlock, input: string): Step[] {
  return parseSteps(chain(block.inputs?.[input]?.block));
}

function encodeLines(text: string): string {
  return text.split("\n").join(LINE_BREAK);
}

function decodeLines(text: string): string {
  return text.split(LINE_BREAK).join("\n");
}

function commaList(text: string): string[] {
  return text.split(",").map((item) => item.trim()).filter(Boolean);
}

function cellList(text: string): string[] {
  return text.split(/\s{2,}|\t/).map((item) => item.trim()).filter(Boolean);
}

// ---------------------------------------------------------------------------
// Workspace -> model
// ---------------------------------------------------------------------------

function parseArguments(first: BlocklyBlock | undefined): Argument[] {
  const args: Argument[] = [];
  for (const block of chain(first)) {
    if (block.type === "robot_argument") {
      args.push({ name: field(block, "NAME") || null, value: field(block, "VALUE") });
    } else if (block.type === "robot_positional_argument") {
      args.push({ name: null, value: field(block, "VALUE") });
    }
  }
  return args;
}

function parseCall(block: BlocklyBlock): CallStep {
  return {
    type: "call",
    // The name field already holds the resolved keyword name, so nothing is left
    // to substitute and `embedded` stays empty.
    keyword: { name: field(block, "KEYWORD"), source: null, embedded: {} },
    args: parseArguments(block.inputs?.ARGS?.block),
    assign: commaList(field(block, "ASSIGN")),
    comment: block.data || null,
  };
}

function parseSteps(blocks: BlocklyBlock[]): Step[] {
  const steps: Step[] = [];
  let i = 0;
  while (i < blocks.length) {
    const block = blocks[i++];
    switch (block.type) {
      case "robot_call":
        steps.push(parseCall(block));
        break;
      case "robot_if": {
        const branches: IfStep[] = [];
        while (blocks[i]?.type === "robot_elseif") {
          const branch = blocks[i++];
          branches.push({
            type: "if",
            condition: field(branch, "CONDITION"),
            steps: statements(branch, "THEN"),
            branches: [],
            else_steps: [],
          });
        }
        let elseSteps: Step[] = [];
        if (blocks[i]?.type === "robot_else") {
          elseSteps = statements(blocks[i++], "DO");
        }
        steps.push({
          type: "if",
          condition: field(block, "CONDITION"),
          steps: statements(block, "THEN"),
          branches,
          else_steps: elseSteps,
        });
        break;
      }
      case "robot_for":
        steps.push({
          type: "for",
          variables: field(block, "VAR").split(/[\s,]+/).filter(Boolean),
          values: cellList(field(block, "VALUES")),
          flavor: (field(block, "FLAVOR") || "in") as ForStep["flavor"],
          steps: statements(block, "DO"),
        });
        break;
      case "robot_while":
        steps.push({
          type: "while",
          condition: field(block, "CONDITION"),
          limit: field(block, "LIMIT") || null,
          until: flag(block, "UNTIL"),
          steps: statements(block, "DO"),
        } satisfies WhileStep);
        break;
      case "robot_try": {
        const excepts: ExceptClause[] = [];
        while (blocks[i]?.type === "robot_except") {
          const clause = blocks[i++];
          excepts.push({
            patterns: commaList(field(clause, "PATTERNS")),
            variable: field(clause, "VAR").trim() || null,
            steps: statements(clause, "DO"),
          });
        }
        let elseSteps: Step[] = [];
        if (blocks[i]?.type === "robot_try_else") {
          elseSteps = statements(blocks[i++], "DO");
        }
        let finallySteps: Step[] = [];
        if (blocks[i]?.type === "robot_finally") {
          finallySteps = statements(blocks[i++], "DO");
        }
        steps.push({
          type: "try",
          steps: statements(block, "DO"),
          excepts,
          else_steps: elseSteps,
          finally_steps: finallySteps,
        } satisfies TryStep);
        break;
      }
      case "robot_var":
        steps.push({
          type: "var",
          name: field(block, "NAME"),
          value: field(block, "VALUE"),
          scope: field(block, "SCOPE") || null,
        });
        break;
      case "robot_return":
        steps.push({ type: "return", values: cellList(field(block, "VALUES")) });
        break;
      case "robot_break":
        steps.push({ type: "break" });
        break;
      case "robot_continue":
        steps.push({ type: "continue" });
        break;
      case "robot_comment":
        steps.push({ type: "comment", text: field(block, "TEXT") });
        break;
      case "robot_raw":
        steps.push({ type: "raw", lines: field(block, "LINES").split(LINE_BREAK) });
        break;
      default:
        // A branch block with no block to attach to, or a block this editor does
        // not know. Dropping it silently would lose work, so keep it as a comment.
        steps.push({ type: "comment", text: `Unsupported block: ${block.type}` });
    }
  }
  return steps;
}

function parseSingleCall(block: BlocklyBlock | undefined): CallStep | null {
  return block?.type === "robot_call" ? parseCall(block) : null;
}

function parseTest(block: BlocklyBlock, base: CanvasDocument): TestCase {
  const name = field(block, "NAME");
  return {
    id: base.tests.find((test) => test.name === name)?.id ?? "",
    name,
    documentation: decodeLines(field(block, "DOC")),
    tags: commaList(field(block, "TAGS")),
    setup: parseSingleCall(block.inputs?.SETUP?.block),
    teardown: parseSingleCall(block.inputs?.TEARDOWN?.block),
    timeout: field(block, "TIMEOUT") || null,
    template: field(block, "TEMPLATE") || null,
    steps: statements(block, "STEPS"),
  };
}

function parseKeyword(block: BlocklyBlock): KeywordDefinition {
  return {
    name: field(block, "NAME"),
    arguments: cellList(field(block, "ARGS")),
    documentation: decodeLines(field(block, "DOC")),
    tags: commaList(field(block, "TAGS")),
    teardown: parseSingleCall(block.inputs?.TEARDOWN?.block),
    steps: statements(block, "STEPS"),
  };
}

/**
 * Builds a document from a Blockly workspace.
 *
 * Only tests, keywords and library imports live on the canvas. Every other
 * suite setting (documentation, resources, variables, suite setup and teardown,
 * tags, timeout, metadata) is carried over from `base` unchanged, so editing
 * blocks never discards it.
 */
export function workspaceToModel(state: BlocklyState, base: CanvasDocument): CanvasDocument {
  const tests: TestCase[] = [];
  const keywords: KeywordDefinition[] = [];
  const libraries: LibraryImport[] = [];

  for (const top of state.blocks?.blocks ?? []) {
    for (const block of chain(top)) {
      if (block.type === "robot_test") {
        tests.push(parseTest(block, base));
      } else if (block.type === "robot_keyword") {
        keywords.push(parseKeyword(block));
      } else if (block.type === "robot_library") {
        const name = field(block, "NAME");
        const alias = field(block, "ALIAS") || null;
        const known = base.settings.libraries.find((lib) => lib.name === name && lib.alias === alias);
        libraries.push({ name, alias, args: known?.args ?? [] });
      }
    }
  }

  return { ...base, settings: { ...base.settings, libraries }, tests, keywords };
}

// ---------------------------------------------------------------------------
// Model -> workspace
// ---------------------------------------------------------------------------

/** Nests blocks through `next`, returning the first one. */
function link(blocks: BlocklyBlock[]): BlocklyBlock | undefined {
  for (let i = blocks.length - 2; i >= 0; i--) {
    blocks[i].next = { block: blocks[i + 1] };
  }
  return blocks[0];
}

function input(blocks: BlocklyBlock[]): { block: BlocklyBlock } | undefined {
  const first = link(blocks);
  return first ? { block: first } : undefined;
}

function inputs(entries: Record<string, BlocklyBlock[]>): BlocklyBlock["inputs"] {
  const result: NonNullable<BlocklyBlock["inputs"]> = {};
  for (const [name, blocks] of Object.entries(entries)) {
    const value = input(blocks);
    if (value) result[name] = value;
  }
  return result;
}

function resolveKeywordName(step: CallStep): string {
  let name = step.keyword.name;
  for (const [key, value] of Object.entries(step.keyword.embedded ?? {})) {
    name = name.split("${" + key + "}").join(value);
  }
  return name;
}

function buildCall(step: CallStep): BlocklyBlock {
  const args = step.args.map((arg): BlocklyBlock =>
    arg.name
      ? { type: "robot_argument", fields: { NAME: arg.name, VALUE: arg.value } }
      : { type: "robot_positional_argument", fields: { VALUE: arg.value } }
  );
  return {
    type: "robot_call",
    fields: { ASSIGN: step.assign.join(", "), KEYWORD: resolveKeywordName(step) },
    inputs: inputs({ ARGS: args }),
    ...(step.comment ? { data: step.comment } : {}),
  };
}

/** One model step becomes one block, or several for IF and TRY branches. */
function buildStep(step: Step): BlocklyBlock[] {
  switch (step.type) {
    case "call":
      return [buildCall(step)];
    case "if": {
      const blocks: BlocklyBlock[] = [
        {
          type: "robot_if",
          fields: { CONDITION: step.condition },
          inputs: inputs({ THEN: buildSteps(step.steps) }),
        },
      ];
      for (const branch of step.branches) {
        blocks.push({
          type: "robot_elseif",
          fields: { CONDITION: branch.condition },
          inputs: inputs({ THEN: buildSteps(branch.steps) }),
        });
      }
      if (step.else_steps.length > 0) {
        blocks.push({ type: "robot_else", inputs: inputs({ DO: buildSteps(step.else_steps) }) });
      }
      return blocks;
    }
    case "for":
      return [
        {
          type: "robot_for",
          fields: {
            VAR: step.variables.join(", "),
            FLAVOR: step.flavor,
            VALUES: step.values.join(CELL_SEPARATOR),
          },
          inputs: inputs({ DO: buildSteps(step.steps) }),
        },
      ];
    case "while":
      return [
        {
          type: "robot_while",
          fields: { CONDITION: step.condition, LIMIT: step.limit ?? "", UNTIL: step.until },
          inputs: inputs({ DO: buildSteps(step.steps) }),
        },
      ];
    case "try": {
      const blocks: BlocklyBlock[] = [
        { type: "robot_try", inputs: inputs({ DO: buildSteps(step.steps) }) },
      ];
      for (const clause of step.excepts) {
        blocks.push({
          type: "robot_except",
          fields: { PATTERNS: clause.patterns.join(", "), VAR: clause.variable ?? "" },
          inputs: inputs({ DO: buildSteps(clause.steps) }),
        });
      }
      if (step.else_steps.length > 0) {
        blocks.push({ type: "robot_try_else", inputs: inputs({ DO: buildSteps(step.else_steps) }) });
      }
      if (step.finally_steps.length > 0) {
        blocks.push({ type: "robot_finally", inputs: inputs({ DO: buildSteps(step.finally_steps) }) });
      }
      return blocks;
    }
    case "var": {
      const scope = (step.scope ?? "").toUpperCase();
      return [
        {
          type: "robot_var",
          fields: { NAME: step.name, VALUE: step.value, SCOPE: SCOPES.has(scope) ? scope : "" },
        },
      ];
    }
    case "return":
      return [{ type: "robot_return", fields: { VALUES: step.values.join(CELL_SEPARATOR) } }];
    case "break":
      return [{ type: "robot_break" }];
    case "continue":
      return [{ type: "robot_continue" }];
    case "comment":
      return [{ type: "robot_comment", fields: { TEXT: step.text } }];
    case "raw":
      return [{ type: "robot_raw", fields: { LINES: step.lines.join(LINE_BREAK) } }];
  }
}

function buildSteps(steps: Step[]): BlocklyBlock[] {
  return steps.flatMap(buildStep);
}

/**
 * Builds Blockly workspace state from a document.
 *
 * Library imports form one stack; each test and keyword is its own top-level
 * block. Positions are left to `Workspace.cleanUp()`.
 */
export function modelToWorkspace(document: CanvasDocument): BlocklyState {
  const top: BlocklyBlock[] = [];

  const libraries = link(
    document.settings.libraries.map<BlocklyBlock>((lib) => ({
      type: "robot_library",
      fields: { NAME: lib.name, ALIAS: lib.alias ?? "" },
    }))
  );
  if (libraries) top.push({ ...libraries, x: 20, y: 20 });

  for (const test of document.tests) {
    top.push({
      type: "robot_test",
      x: 20,
      y: 20,
      fields: {
        NAME: test.name,
        DOC: encodeLines(test.documentation),
        TAGS: test.tags.join(", "),
        TIMEOUT: test.timeout ?? "",
        TEMPLATE: test.template ?? "",
      },
      inputs: inputs({
        SETUP: test.setup ? [buildCall(test.setup)] : [],
        TEARDOWN: test.teardown ? [buildCall(test.teardown)] : [],
        STEPS: buildSteps(test.steps),
      }),
    });
  }

  for (const keyword of document.keywords) {
    top.push({
      type: "robot_keyword",
      x: 20,
      y: 20,
      fields: {
        NAME: keyword.name,
        ARGS: keyword.arguments.join(CELL_SEPARATOR),
        DOC: encodeLines(keyword.documentation),
        TAGS: keyword.tags.join(", "),
      },
      inputs: inputs({
        TEARDOWN: keyword.teardown ? [buildCall(keyword.teardown)] : [],
        STEPS: buildSteps(keyword.steps),
      }),
    });
  }

  return { blocks: { languageVersion: 0, blocks: top } };
}

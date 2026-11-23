import {
  CanvasDocument,
  TestCase,
  KeywordDefinition,
  CallStep,
  IfStep,
  ForStep,
  WhileStep,
  TryStep,
  VarStep,
  ReturnStep,
  Step,
  Argument,
  KeywordRef,
  LibraryImport,
  ExceptClause,
} from "../types/canvas";

interface BlocklyWorkspace {
  blocks: Record<string, BlocklyBlock>;
}

interface BlocklyBlock {
  type: string;
  id: string;
  x?: number;
  y?: number;
  fields?: Record<string, string | number | boolean>;
  inputs?: Record<string, BlocklyInput>;
  next?: BlocklyNext;
  extraState?: Record<string, unknown>;
}

interface BlocklyInput {
  block?: BlocklyBlock;
}

interface BlocklyNext {
  block?: BlocklyBlock;
}

const STEP_TYPE_MAP: Record<string, string> = {
  robot_call: "call",
  robot_if: "if",
  robot_for: "for",
  robot_while: "while",
  robot_try: "try",
  robot_var: "var",
  robot_return: "return",
  robot_break: "break",
  robot_continue: "continue",
  robot_comment: "comment",
  robot_raw: "raw",
};

function getField(block: BlocklyBlock, name: string): string {
  return String(block.fields?.[name] ?? "");
}

function getInputBlock(block: BlocklyBlock, name: string): BlocklyBlock | undefined {
  return block.inputs?.[name]?.block;
}

function getStatementBlocks(block: BlocklyBlock, name: string): BlocklyBlock[] {
  const input = block.inputs?.[name];
  if (!input?.block) return [];
  const blocks: BlocklyBlock[] = [];
  let current: BlocklyBlock | undefined = input.block;
  while (current) {
    blocks.push(current);
    current = current.next?.block;
  }
  return blocks;
}

function getValueBlocks(block: BlocklyBlock, name: string): BlocklyBlock[] {
  const input = block.inputs?.[name];
  if (!input?.block) return [];
  const blocks: BlocklyBlock[] = [];
  let current: BlocklyBlock | undefined = input.block;
  while (current) {
    blocks.push(current);
    current = current.next?.block;
  }
  return blocks;
}

function parseArguments(argBlocks: BlocklyBlock[]): Argument[] {
  const args: Argument[] = [];
  for (const argBlock of argBlocks) {
    if (argBlock.type === "robot_argument") {
      args.push({ name: getField(argBlock, "NAME") || null, value: getField(argBlock, "VALUE") || "" });
    } else if (argBlock.type === "robot_positional_argument") {
      args.push({ name: null, value: getField(argBlock, "VALUE") || "" });
    }
  }
  return args;
}

function parseAssign(assignBlocks: BlocklyBlock[]): string[] {
  return assignBlocks.map((b) => getField(b, "NAME")).filter(Boolean);
}

function parseKeywordRef(callBlock: BlocklyBlock): KeywordRef {
  const keywordName = getField(callBlock, "KEYWORD");
  const embedded: Record<string, string> = {};
  const matches = keywordName.match(/\$\{([^}]+)\}/g);
  if (matches) {
    for (const match of matches) {
      const key = match.slice(2, -1);
      embedded[key] = "";
    }
  }
  return { name: keywordName, source: null, embedded };
}

function parseCallStep(block: BlocklyBlock): CallStep {
  const keyword = parseKeywordRef(block);
  const argBlocks = getStatementBlocks(block, "ARGS");
  return {
    type: "call",
    keyword,
    args: parseArguments(argBlocks),
    assign: parseAssign(getValueBlocks(block, "ASSIGN")),
    comment: null,
  };
}

function parseIfStep(block: BlocklyBlock): IfStep {
  const condition = getField(block, "CONDITION");
  const thenBlocks = getStatementBlocks(block, "THEN");
  const steps = thenBlocks.map(parseStep);
  const extraState = block.extraState as { elseifCount?: number; hasElse?: boolean } | undefined;
  const elseifCount = extraState?.elseifCount || 0;
  const hasElse = extraState?.hasElse || false;

  const branches: IfStep[] = [];
  for (let i = 0; i < elseifCount; i++) {
    const elseifCondition = getField(block, `ELSEIF_CONDITION_${i}`);
    const elseifBlocks = getStatementBlocks(block, `ELSEIF_THEN_${i}`);
    branches.push({
      type: "if",
      condition: elseifCondition,
      steps: elseifBlocks.map(parseStep),
      branches: [],
      else_steps: [],
    });
  }

  const elseSteps = hasElse ? getStatementBlocks(block, "ELSE").map(parseStep) : [];

  return { type: "if", condition, steps, branches, else_steps: elseSteps };
}

function parseForStep(block: BlocklyBlock): ForStep {
  const variables = [getField(block, "VAR")].filter(Boolean);
  const flavor = getField(block, "FLAVOR");
  const valueBlocks = getValueBlocks(block, "VALUES");
  const values = valueBlocks.map((b) => getField(b, "VALUE") || getField(b, "NAME") || "");
  const steps = getStatementBlocks(block, "DO").map(parseStep);
  return { type: "for", variables, values, flavor: flavor as ForStep["flavor"], steps };
}

function parseWhileStep(block: BlocklyBlock): WhileStep {
  const condition = getField(block, "CONDITION");
  const limit = getField(block, "LIMIT");
  const until = getField(block, "UNTIL") === "true";
  const steps = getStatementBlocks(block, "DO").map(parseStep);
  return { type: "while", condition, limit: limit || null, until, steps };
}

function parseTryStep(block: BlocklyBlock): TryStep {
  const tryBlocks = getStatementBlocks(block, "TRY");
  const steps = tryBlocks.map(parseStep);
  const extraState = block.extraState as { exceptCount?: number; hasElse?: boolean; hasFinally?: boolean } | undefined;
  const exceptCount = extraState?.exceptCount || 1;
  const hasElse = extraState?.hasElse || false;
  const hasFinally = extraState?.hasFinally || false;

  const excepts: ExceptClause[] = [];
  for (let i = 0; i < exceptCount; i++) {
    const patterns = getField(block, `EXCEPT_PATTERNS_${i}`).split(",").map((p) => p.trim()).filter(Boolean);
    const variable = getField(block, `EXCEPT_VAR_FIELD_${i}`) || getField(block, `EXCEPT_VAR_${i}`) || "error";
    const exceptBlocks = getStatementBlocks(block, `EXCEPT_DO_${i}`);
    excepts.push({ patterns, variable: variable || null, steps: exceptBlocks.map(parseStep) });
  }

  const elseSteps = hasElse ? getStatementBlocks(block, "ELSE").map(parseStep) : [];
  const finallySteps = hasFinally ? getStatementBlocks(block, "FINALLY").map(parseStep) : [];

  return { type: "try", steps, excepts, else_steps: elseSteps, finally_steps: finallySteps };
}

function parseVarStep(block: BlocklyBlock): VarStep {
  return {
    type: "var",
    name: getField(block, "NAME"),
    value: getField(block, "VALUE"),
    scope: getField(block, "SCOPE") || null,
  };
}

function parseReturnStep(block: BlocklyBlock): ReturnStep {
  const valueBlocks = getStatementBlocks(block, "VALUES");
  return { type: "return", values: valueBlocks.map((b) => getField(b, "VALUE") || getField(b, "NAME") || "") };
}

function parseStep(block: BlocklyBlock): Step {
  const stepType = STEP_TYPE_MAP[block.type];
  switch (stepType) {
    case "call":
      return parseCallStep(block);
    case "if":
      return parseIfStep(block);
    case "for":
      return parseForStep(block);
    case "while":
      return parseWhileStep(block);
    case "try":
      return parseTryStep(block);
    case "var":
      return parseVarStep(block);
    case "return":
      return parseReturnStep(block);
    case "break":
      return { type: "break" };
    case "continue":
      return { type: "continue" };
    case "comment":
      return { type: "comment", text: getField(block, "TEXT") };
    case "raw":
      return { type: "raw", lines: getField(block, "LINES").split("\n") };
    default:
      return { type: "raw", lines: [`# Unknown block: ${block.type}`] };
  }
}

function parseTestCase(block: BlocklyBlock): TestCase {
  const name = getField(block, "NAME");
  const steps = getStatementBlocks(block, "STEPS").map(parseStep);
  return {
    id: "",
    name,
    documentation: getField(block, "DOC"),
    tags: getField(block, "TAGS").split(",").map((t) => t.trim()).filter(Boolean),
    setup: getInputBlock(block, "SETUP") ? parseCallStep(getInputBlock(block, "SETUP")!) : null,
    teardown: getInputBlock(block, "TEARDOWN") ? parseCallStep(getInputBlock(block, "TEARDOWN")!) : null,
    timeout: getField(block, "TIMEOUT") || null,
    template: getField(block, "TEMPLATE") || null,
    steps,
  };
}

function parseKeywordDef(block: BlocklyBlock): KeywordDefinition {
  const name = getField(block, "NAME");
  const args = getField(block, "ARGS").split(",").map((a) => a.trim()).filter(Boolean);
  const steps = getStatementBlocks(block, "STEPS").map(parseStep);
  return {
    name,
    arguments: args,
    documentation: getField(block, "DOC"),
    tags: getField(block, "TAGS").split(",").map((t) => t.trim()).filter(Boolean),
    teardown: getInputBlock(block, "TEARDOWN") ? parseCallStep(getInputBlock(block, "TEARDOWN")!) : null,
    steps,
  };
}

export function workspaceToModel(workspace: BlocklyWorkspace, name: string): CanvasDocument {
  const topBlocks = Object.values(workspace.blocks).filter((b) => !b.next && !b.inputs?.STACK?.block?.next);
  const tests: TestCase[] = [];
  const keywords: KeywordDefinition[] = [];
  const libraries: LibraryImport[] = [];

  for (const block of topBlocks) {
    if (block.type === "robot_test") {
      tests.push(parseTestCase(block));
    } else if (block.type === "robot_keyword") {
      keywords.push(parseKeywordDef(block));
    } else if (block.type === "robot_library") {
      libraries.push({ name: getField(block, "NAME"), alias: getField(block, "ALIAS") || null, args: [] });
    }
  }

  return {
    version: 1,
    name,
    settings: { documentation: "", libraries, resources: [], variables: [], suite_setup: null, suite_teardown: null, test_setup: null, test_teardown: null, force_tags: [], default_tags: [], test_timeout: null, metadata: {} },
    tests,
    keywords,
  };
}

function buildCallStep(step: CallStep, idPrefix: string): BlocklyBlock {
  const keywordName = step.keyword.embedded && Object.keys(step.keyword.embedded).length > 0
    ? Object.entries(step.keyword.embedded).reduce((name, [key, value]) => name.replace(`\${${key}}`, value), step.keyword.name)
    : step.keyword.name;
  const blocks: BlocklyBlock[] = [];
  let lastId = `${idPrefix}_call`;

  blocks.push({
    type: "robot_call",
    id: lastId,
    fields: { KEYWORD: keywordName },
    extraState: { argCount: step.args.length },
  });

  for (let i = 0; i < step.args.length; i++) {
    const arg = step.args[i];
    const argId = `${idPrefix}_arg_${i}`;
    blocks.push({
      type: arg.name ? "robot_argument" : "robot_positional_argument",
      id: argId,
      fields: { NAME: arg.name || "", VALUE: arg.value },
      next: i < step.args.length - 1 ? { block: { id: `${idPrefix}_arg_${i + 1}`, type: "" } } : undefined,
    });
  }

  return blocks[0];
}

function buildStep(step: Step, idPrefix: string): BlocklyBlock {
  switch (step.type) {
    case "call":
      return buildCallStep(step, idPrefix);
    case "if": {
      const ifId = `${idPrefix}_if`;
      const blocks: BlocklyBlock[] = [];
      blocks.push({
        type: "robot_if",
        id: ifId,
        fields: { CONDITION: step.condition },
        extraState: { elseifCount: step.branches.length, hasElse: step.else_steps.length > 0 },
      });
      step.steps.forEach((s, i) => {
        buildStep(s, `${idPrefix}_then_${i}`);
      });
      return blocks[0];
    }
    case "for": {
      const forId = `${idPrefix}_for`;
      return {
        type: "robot_for",
        id: forId,
        fields: { VAR: step.variables[0] || "item", FLAVOR: step.flavor },
        inputs: { VALUES: { block: { type: "robot_text", id: `${idPrefix}_values`, fields: { TEXT: step.values.join(" ") } } } },
      };
    }
    case "while": {
      const whileId = `${idPrefix}_while`;
      return {
        type: "robot_while",
        id: whileId,
        fields: { CONDITION: step.condition, LIMIT: step.limit || "", UNTIL: step.until },
      };
    }
    case "try": {
      const tryId = `${idPrefix}_try`;
      return {
        type: "robot_try",
        id: tryId,
        extraState: { exceptCount: step.excepts.length, hasElse: step.else_steps.length > 0, hasFinally: step.finally_steps.length > 0 },
      };
    }
    case "var": {
      return {
        type: "robot_var",
        id: `${idPrefix}_var`,
        fields: { NAME: step.name, VALUE: step.value, SCOPE: step.scope || "TEST" },
      };
    }
    case "return": {
      return {
        type: "robot_return",
        id: `${idPrefix}_return`,
      };
    }
    case "break":
      return { type: "robot_break", id: `${idPrefix}_break` };
    case "continue":
      return { type: "robot_continue", id: `${idPrefix}_continue` };
    case "comment":
      return { type: "robot_comment", id: `${idPrefix}_comment`, fields: { TEXT: step.text } };
    case "raw":
      return { type: "robot_raw", id: `${idPrefix}_raw`, fields: { LINES: step.lines.join("\n") } };
  }
}

export function modelToWorkspace(document: CanvasDocument): BlocklyWorkspace {
  const blocks: Record<string, BlocklyBlock> = {};
  let idCounter = 0;
  const nextId = (prefix: string) => `${prefix}_${idCounter++}`;

  if (document.settings.libraries.length > 0) {
    document.settings.libraries.forEach((lib) => {
      blocks[nextId("lib")] = {
        type: "robot_library",
        id: nextId("lib"),
        fields: { NAME: lib.name, ALIAS: lib.alias || "" },
      };
    });
  }

  document.tests.forEach((test) => {
    const testId = nextId("test");
    const stepBlocks = test.steps.map((step, i) => buildStep(step, `${testId}_step_${i}`));
    blocks[testId] = {
      type: "robot_test",
      id: testId,
      fields: { NAME: test.name, DOC: test.documentation, TAGS: test.tags.join(", "), TIMEOUT: test.timeout || "", TEMPLATE: test.template || "" },
      inputs: { STEPS: { block: stepBlocks[0] } },
    };
  });

  document.keywords.forEach((kw) => {
    const kwId = nextId("kw");
    const stepBlocks = kw.steps.map((step, i) => buildStep(step, `${kwId}_step_${i}`));
    blocks[kwId] = {
      type: "robot_keyword",
      id: kwId,
      fields: { NAME: kw.name, ARGS: kw.arguments.join(", "), DOC: kw.documentation, TAGS: kw.tags.join(", ") },
      inputs: { STEPS: { block: stepBlocks[0] } },
    };
  });

  return { blocks };
}
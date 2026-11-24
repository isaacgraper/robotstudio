/**
 * Robotstudio - Visual Robot Framework Authoring Platform
 * Block Definitions
 *
 * Custom Blockly blocks for Robot Framework authoring, in Blockly's JSON block
 * format. Every value a user types is a text field, so the workspace maps
 * one-to-one onto the canvas document (see `serialization.ts`).
 *
 * Statement blocks carry a connection check so that only sensible stacks can be
 * built: steps stack with steps, arguments with arguments, and the branch
 * blocks (ELSE IF, ELSE, EXCEPT, FINALLY) can only follow the block they belong
 * to.
 *
 * @packageDocumentation
 */

/** Connection check shared by every executable step. */
const STEP = "STEP";
/** Connection check for call arguments. */
const ARG = "ARG";
/** Connection check for library imports. */
const LIBRARY = "LIBRARY";

/** A block that may be followed by a branch block of the same construct. */
const BRANCH_IF = "IF";
const BRANCH_TRY = "TRY";
const BRANCH_FINALLY = "FINALLY";

export const callBlock = {
  type: "robot_call",
  message0: "%1 = %2 %3",
  args0: [
    { type: "field_input", name: "ASSIGN", text: "" },
    { type: "field_input", name: "KEYWORD", text: "Log" },
    { type: "input_statement", name: "ARGS", check: ARG },
  ],
  previousStatement: STEP,
  nextStatement: STEP,
  colour: "#4CAF50",
  tooltip: "Call a keyword. Optional variables on the left receive the return value.",
  helpUrl: "",
};

export const ifBlock = {
  type: "robot_if",
  message0: "IF %1",
  args0: [{ type: "field_input", name: "CONDITION", text: "${value} > 0" }],
  message1: "DO %1",
  args1: [{ type: "input_statement", name: "THEN", check: STEP }],
  previousStatement: STEP,
  nextStatement: [STEP, BRANCH_IF],
  colour: "#2196F3",
  tooltip: "Conditional. Follow it with ELSE IF and ELSE blocks.",
  helpUrl: "",
};

export const elseIfBlock = {
  type: "robot_elseif",
  message0: "ELSE IF %1",
  args0: [{ type: "field_input", name: "CONDITION", text: "${value} < 0" }],
  message1: "DO %1",
  args1: [{ type: "input_statement", name: "THEN", check: STEP }],
  previousStatement: BRANCH_IF,
  nextStatement: [STEP, BRANCH_IF],
  colour: "#2196F3",
  tooltip: "Another branch of the IF block above.",
  helpUrl: "",
};

export const elseBlock = {
  type: "robot_else",
  message0: "ELSE",
  message1: "DO %1",
  args1: [{ type: "input_statement", name: "DO", check: STEP }],
  previousStatement: BRANCH_IF,
  nextStatement: STEP,
  colour: "#2196F3",
  tooltip: "Final branch of the IF block above.",
  helpUrl: "",
};

export const forBlock = {
  type: "robot_for",
  message0: "FOR %1 %2 %3",
  args0: [
    { type: "field_input", name: "VAR", text: "item" },
    {
      type: "field_dropdown",
      name: "FLAVOR",
      options: [
        ["IN", "in"],
        ["IN RANGE", "in_range"],
        ["IN ENUMERATE", "in_enumerate"],
        ["IN ZIP", "in_zip"],
      ],
    },
    { type: "field_input", name: "VALUES", text: "@{items}" },
  ],
  message1: "DO %1",
  args1: [{ type: "input_statement", name: "DO", check: STEP }],
  previousStatement: STEP,
  nextStatement: STEP,
  colour: "#FF9800",
  tooltip: "For loop. Separate several variables with commas and several values with two spaces.",
  helpUrl: "",
};

export const whileBlock = {
  type: "robot_while",
  message0: "WHILE %1",
  args0: [{ type: "field_input", name: "CONDITION", text: "${count} < 10" }],
  message1: "limit %1 negate %2",
  args1: [
    { type: "field_input", name: "LIMIT", text: "" },
    { type: "field_checkbox", name: "UNTIL", checked: false },
  ],
  message2: "DO %1",
  args2: [{ type: "input_statement", name: "DO", check: STEP }],
  previousStatement: STEP,
  nextStatement: STEP,
  colour: "#FF5722",
  tooltip: "While loop. Negate runs the loop until the condition becomes true.",
  helpUrl: "",
};

export const tryBlock = {
  type: "robot_try",
  message0: "TRY",
  message1: "DO %1",
  args1: [{ type: "input_statement", name: "DO", check: STEP }],
  previousStatement: STEP,
  nextStatement: [STEP, BRANCH_TRY],
  colour: "#9C27B0",
  tooltip: "Try block. Follow it with EXCEPT, ELSE and FINALLY blocks.",
  helpUrl: "",
};

export const exceptBlock = {
  type: "robot_except",
  message0: "EXCEPT %1 AS %2",
  args0: [
    { type: "field_input", name: "PATTERNS", text: "" },
    { type: "field_input", name: "VAR", text: "error" },
  ],
  message1: "DO %1",
  args1: [{ type: "input_statement", name: "DO", check: STEP }],
  previousStatement: BRANCH_TRY,
  nextStatement: [STEP, BRANCH_TRY],
  colour: "#9C27B0",
  tooltip: "Handles errors from the TRY block above. Separate patterns with commas.",
  helpUrl: "",
};

export const tryElseBlock = {
  type: "robot_try_else",
  message0: "ELSE",
  message1: "DO %1",
  args1: [{ type: "input_statement", name: "DO", check: STEP }],
  previousStatement: BRANCH_TRY,
  nextStatement: [STEP, BRANCH_FINALLY],
  colour: "#9C27B0",
  tooltip: "Runs when the TRY block did not fail.",
  helpUrl: "",
};

export const finallyBlock = {
  type: "robot_finally",
  message0: "FINALLY",
  message1: "DO %1",
  args1: [{ type: "input_statement", name: "DO", check: STEP }],
  previousStatement: [BRANCH_TRY, BRANCH_FINALLY],
  nextStatement: STEP,
  colour: "#9C27B0",
  tooltip: "Always runs after the TRY block.",
  helpUrl: "",
};

export const varBlock = {
  type: "robot_var",
  message0: "VAR %1 = %2",
  args0: [
    { type: "field_input", name: "NAME", text: "name" },
    { type: "field_input", name: "VALUE", text: "" },
  ],
  message1: "scope %1",
  args1: [
    {
      type: "field_dropdown",
      name: "SCOPE",
      options: [
        ["LOCAL", ""],
        ["TEST", "TEST"],
        ["TASK", "TASK"],
        ["SUITE", "SUITE"],
        ["GLOBAL", "GLOBAL"],
      ],
    },
  ],
  previousStatement: STEP,
  nextStatement: STEP,
  colour: "#607D8B",
  tooltip: "Set a variable",
  helpUrl: "",
};

export const returnBlock = {
  type: "robot_return",
  message0: "RETURN %1",
  args0: [{ type: "field_input", name: "VALUES", text: "" }],
  previousStatement: STEP,
  nextStatement: STEP,
  colour: "#795548",
  tooltip: "Return from a keyword. Separate several values with two spaces.",
  helpUrl: "",
};

export const breakBlock = {
  type: "robot_break",
  message0: "BREAK",
  previousStatement: STEP,
  nextStatement: STEP,
  colour: "#E91E63",
  tooltip: "Break out of loop",
  helpUrl: "",
};

export const continueBlock = {
  type: "robot_continue",
  message0: "CONTINUE",
  previousStatement: STEP,
  nextStatement: STEP,
  colour: "#E91E63",
  tooltip: "Continue to next iteration",
  helpUrl: "",
};

export const commentBlock = {
  type: "robot_comment",
  message0: "# %1",
  args0: [{ type: "field_input", name: "TEXT", text: "comment" }],
  previousStatement: STEP,
  nextStatement: STEP,
  colour: "#9E9E9E",
  tooltip: "Comment",
  helpUrl: "",
};

export const rawBlock = {
  type: "robot_raw",
  message0: "RAW %1",
  args0: [{ type: "field_input", name: "LINES", text: "" }],
  previousStatement: STEP,
  nextStatement: STEP,
  colour: "#37474F",
  tooltip: "Raw Robot Framework lines (preserved from import). Line breaks show as ⏎.",
  helpUrl: "",
};

export const argumentBlock = {
  type: "robot_argument",
  message0: "%1 = %2",
  args0: [
    { type: "field_input", name: "NAME", text: "name" },
    { type: "field_input", name: "VALUE", text: "" },
  ],
  previousStatement: ARG,
  nextStatement: ARG,
  colour: "#FFC107",
  tooltip: "Named argument",
  helpUrl: "",
};

export const positionalArgumentBlock = {
  type: "robot_positional_argument",
  message0: "%1",
  args0: [{ type: "field_input", name: "VALUE", text: "" }],
  previousStatement: ARG,
  nextStatement: ARG,
  colour: "#FFC107",
  tooltip: "Positional argument",
  helpUrl: "",
};

export const testBlock = {
  type: "robot_test",
  message0: "TEST %1",
  args0: [{ type: "field_input", name: "NAME", text: "Test Case" }],
  message1: "Doc %1",
  args1: [{ type: "field_input", name: "DOC", text: "" }],
  message2: "Tags %1",
  args2: [{ type: "field_input", name: "TAGS", text: "" }],
  message3: "Timeout %1",
  args3: [{ type: "field_input", name: "TIMEOUT", text: "" }],
  message4: "Template %1",
  args4: [{ type: "field_input", name: "TEMPLATE", text: "" }],
  message5: "Setup %1",
  args5: [{ type: "input_statement", name: "SETUP", check: STEP }],
  message6: "Teardown %1",
  args6: [{ type: "input_statement", name: "TEARDOWN", check: STEP }],
  message7: "Steps %1",
  args7: [{ type: "input_statement", name: "STEPS", check: STEP }],
  colour: "#009688",
  tooltip: "Test case",
  helpUrl: "",
};

export const keywordBlock = {
  type: "robot_keyword",
  message0: "KEYWORD %1",
  args0: [{ type: "field_input", name: "NAME", text: "My Keyword" }],
  message1: "Args %1",
  args1: [{ type: "field_input", name: "ARGS", text: "" }],
  message2: "Doc %1",
  args2: [{ type: "field_input", name: "DOC", text: "" }],
  message3: "Tags %1",
  args3: [{ type: "field_input", name: "TAGS", text: "" }],
  message4: "Teardown %1",
  args4: [{ type: "input_statement", name: "TEARDOWN", check: STEP }],
  message5: "Steps %1",
  args5: [{ type: "input_statement", name: "STEPS", check: STEP }],
  colour: "#673AB7",
  tooltip: "User keyword. Separate arguments with two spaces.",
  helpUrl: "",
};

export const libraryBlock = {
  type: "robot_library",
  message0: "LIBRARY %1 AS %2",
  args0: [
    { type: "field_input", name: "NAME", text: "BuiltIn" },
    { type: "field_input", name: "ALIAS", text: "" },
  ],
  previousStatement: LIBRARY,
  nextStatement: LIBRARY,
  colour: "#00BCD4",
  tooltip: "Import a library",
  helpUrl: "",
};

/** Every block registered with Blockly. */
export const allBlocks = [
  callBlock,
  ifBlock,
  elseIfBlock,
  elseBlock,
  forBlock,
  whileBlock,
  tryBlock,
  exceptBlock,
  tryElseBlock,
  finallyBlock,
  varBlock,
  returnBlock,
  breakBlock,
  continueBlock,
  commentBlock,
  rawBlock,
  argumentBlock,
  positionalArgumentBlock,
  testBlock,
  keywordBlock,
  libraryBlock,
];

/** Toolbox categories shown by default. Keyword blocks are added separately. */
export const blockCategories: Record<string, string[]> = {
  Control: [
    "robot_if",
    "robot_elseif",
    "robot_else",
    "robot_for",
    "robot_while",
    "robot_try",
    "robot_except",
    "robot_try_else",
    "robot_finally",
    "robot_break",
    "robot_continue",
    "robot_return",
  ],
  Variables: ["robot_var"],
  Arguments: ["robot_positional_argument", "robot_argument"],
  Comments: ["robot_comment", "robot_raw"],
};

/** Expert mode shows the same blocks, plus every keyword from the catalog. */
export const expertCategories = blockCategories;

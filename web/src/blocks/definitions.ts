import * as Blockly from "blockly";

export const callBlock = {
  type: "robot_call",
  message0: "%1 %2",
  args0: [
    {
      type: "field_dropdown",
      name: "KEYWORD",
      options: () => {
        // This function will be called by Blockly when rendering the dropdown.
        // It reads the current keyword options from the global registry.
        const ws = Blockly.getMainWorkspace();
        if (ws) {
          const keywords = (ws as any).targetKeywords || [];
          return keywords.map((kw: any) => [kw.name, kw.name]);
        }
        return [];
      },
    },
    { type: "input_statement", name: "ARGS" },
  ],
  previousStatement: null,
  nextStatement: null,
  colour: "#4CAF50",
  tooltip: "Call a keyword",
  helpUrl: "",
  mutator: "call_mutator",
};

export const ifBlock = {
  type: "robot_if",
  message0: "IF %1",
  args0: [{ type: "input_value", name: "CONDITION" }],
  message1: "DO %1",
  args1: [{ type: "input_statement", name: "THEN" }],
  message2: "ELSEIF %1",
  args2: [{ type: "input_value", name: "ELSEIF_CONDITION" }],
  message3: "DO %1",
  args3: [{ type: "input_statement", name: "ELSEIF_THEN" }],
  message4: "ELSE %1",
  args4: [{ type: "input_statement", name: "ELSE" }],
  previousStatement: null,
  nextStatement: null,
  colour: "#2196F3",
  tooltip: "Conditional block",
  helpUrl: "",
  mutator: "if_mutator",
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
        ["IN", "IN"],
        ["IN RANGE", "IN_RANGE"],
        ["IN ENUMERATE", "IN_ENUMERATE"],
        ["IN ZIP", "IN_ZIP"],
      ],
    },
    { type: "input_value", name: "VALUES" },
  ],
  message1: "DO %1",
  args1: [{ type: "input_statement", name: "DO" }],
  previousStatement: null,
  nextStatement: null,
  colour: "#FF9800",
  tooltip: "For loop",
  helpUrl: "",
};

export const whileBlock = {
  type: "robot_while",
  message0: "WHILE %1",
  args0: [{ type: "input_value", name: "CONDITION" }],
  message1: "limit %1",
  args1: [{ type: "input_value", name: "LIMIT" }],
  message2: "until %1",
  args2: [{ type: "field_checkbox", name: "UNTIL", checked: false }],
  message3: "DO %1",
  args3: [{ type: "input_statement", name: "DO" }],
  previousStatement: null,
  nextStatement: null,
  colour: "#FF5722",
  tooltip: "While loop",
  helpUrl: "",
};

export const tryBlock = {
  type: "robot_try",
  message0: "TRY",
  message1: "DO %1",
  args1: [{ type: "input_statement", name: "TRY" }],
  message2: "EXCEPT %1 AS %2",
  args2: [
    { type: "input_value", name: "EXCEPT_PATTERNS" },
    { type: "field_input", name: "EXCEPT_VAR", text: "error" },
  ],
  message3: "DO %1",
  args3: [{ type: "input_statement", name: "EXCEPT_DO" }],
  message4: "ELSE %1",
  args4: [{ type: "input_statement", name: "ELSE" }],
  message5: "FINALLY %1",
  args5: [{ type: "input_statement", name: "FINALLY" }],
  previousStatement: null,
  nextStatement: null,
  colour: "#9C27B0",
  tooltip: "Try/Except/Else/Finally",
  helpUrl: "",
  mutator: "try_mutator",
};

export const varBlock = {
  type: "robot_var",
  message0: "VAR %1 = %2",
  args0: [
    { type: "field_input", name: "NAME", text: "var" },
    { type: "input_value", name: "VALUE" },
  ],
  message1: "scope %1",
  args1: [
    {
      type: "field_dropdown",
      name: "SCOPE",
      options: [
        ["TEST", "TEST"],
        ["TASK", "TASK"],
        ["SUITE", "SUITE"],
        ["GLOBAL", "GLOBAL"],
      ],
    },
  ],
  previousStatement: null,
  nextStatement: null,
  colour: "#607D8B",
  tooltip: "Set a variable",
  helpUrl: "",
};

export const returnBlock = {
  type: "robot_return",
  message0: "RETURN %1",
  args0: [{ type: "input_statement", name: "VALUES" }],
  previousStatement: null,
  nextStatement: null,
  colour: "#795548",
  tooltip: "Return from keyword",
  helpUrl: "",
};

export const breakBlock = {
  type: "robot_break",
  message0: "BREAK",
  previousStatement: null,
  nextStatement: null,
  colour: "#E91E63",
  tooltip: "Break out of loop",
  helpUrl: "",
};

export const continueBlock = {
  type: "robot_continue",
  message0: "CONTINUE",
  previousStatement: null,
  nextStatement: null,
  colour: "#E91E63",
  tooltip: "Continue to next iteration",
  helpUrl: "",
};

export const commentBlock = {
  type: "robot_comment",
  message0: "# %1",
  args0: [{ type: "field_input", name: "TEXT", text: "comment" }],
  previousStatement: null,
  nextStatement: null,
  colour: "#9E9E9E",
  tooltip: "Comment",
  helpUrl: "",
};

export const rawBlock = {
  type: "robot_raw",
  message0: "RAW %1",
  args0: [{ type: "field_multilinetext", name: "LINES", text: "" }],
  previousStatement: null,
  nextStatement: null,
  colour: "#37474F",
  tooltip: "Raw Robot Framework lines (preserved from import)",
  helpUrl: "",
};

export const argumentBlock = {
  type: "robot_argument",
  message0: "%1 = %2",
  args0: [
    { type: "field_input", name: "NAME", text: "" },
    { type: "input_value", name: "VALUE" },
  ],
  output: "ARGUMENT",
  colour: "#FFC107",
  tooltip: "Named argument",
  helpUrl: "",
};

export const positionalArgumentBlock = {
  type: "robot_positional_argument",
  message0: "%1",
  args0: [{ type: "input_value", name: "VALUE" }],
  output: "ARGUMENT",
  colour: "#FFC107",
  tooltip: "Positional argument",
  helpUrl: "",
};

export const assignBlock = {
  type: "robot_assign",
  message0: "%1 =",
  args0: [{ type: "field_input", name: "NAME", text: "var" }],
  output: "ASSIGN",
  colour: "#FFEB3B",
  tooltip: "Assignment target",
  helpUrl: "",
};

export const suiteBlock = {
  type: "robot_suite",
  message0: "SUITE %1",
  args0: [{ type: "field_input", name: "NAME", text: "My Suite" }],
  message1: "Settings",
  message2: "%1",
  args2: [{ type: "input_statement", name: "SETTINGS" }],
  message3: "Test Cases",
  message4: "%1",
  args4: [{ type: "input_statement", name: "TESTS" }],
  message5: "Keywords",
  message6: "%1",
  args6: [{ type: "input_statement", name: "KEYWORDS" }],
  colour: "#3F51B5",
  tooltip: "Root suite block",
  helpUrl: "",
};

export const testBlock = {
  type: "robot_test",
  message0: "TEST %1",
  args0: [{ type: "field_input", name: "NAME", text: "Test Case" }],
  message1: "Doc %1",
  args1: [{ type: "field_multilinetext", name: "DOC", text: "" }],
  message2: "Tags %1",
  args2: [{ type: "field_input", name: "TAGS", text: "" }],
  message3: "Timeout %1",
  args3: [{ type: "field_input", name: "TIMEOUT", text: "" }],
  message4: "Template %1",
  args4: [{ type: "field_input", name: "TEMPLATE", text: "" }],
  message5: "Setup",
  message6: "%1",
  args6: [{ type: "input_statement", name: "SETUP" }],
  message7: "Teardown",
  message8: "%1",
  args8: [{ type: "input_statement", name: "TEARDOWN" }],
  message9: "Steps",
  message10: "%1",
  args10: [{ type: "input_statement", name: "STEPS" }],
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
  args2: [{ type: "field_multilinetext", name: "DOC", text: "" }],
  message3: "Tags %1",
  args3: [{ type: "field_input", name: "TAGS", text: "" }],
  message4: "Teardown",
  message5: "%1",
  args5: [{ type: "input_statement", name: "TEARDOWN" }],
  message6: "Steps",
  message7: "%1",
  args7: [{ type: "input_statement", name: "STEPS" }],
  colour: "#673AB7",
  tooltip: "User keyword",
  helpUrl: "",
};

export const libraryBlock = {
  type: "robot_library",
  message0: "LIBRARY %1",
  args0: [{ type: "field_input", name: "NAME", text: "BuiltIn" }],
  message1: "AS %1",
  args1: [{ type: "field_input", name: "ALIAS", text: "" }],
  previousStatement: null,
  nextStatement: null,
  colour: "#00BCD4",
  tooltip: "Import a library",
  helpUrl: "",
};

export const allBlocks = [
  callBlock,
  ifBlock,
  forBlock,
  whileBlock,
  tryBlock,
  varBlock,
  returnBlock,
  breakBlock,
  continueBlock,
  commentBlock,
  rawBlock,
  argumentBlock,
  positionalArgumentBlock,
  assignBlock,
  suiteBlock,
  testBlock,
  keywordBlock,
  libraryBlock,
];

export const blockCategories = {
  Flow: [
    "robot_call",
    "robot_if",
    "robot_for",
    "robot_while",
    "robot_try",
    "robot_return",
    "robot_break",
    "robot_continue",
  ],
  Variables: ["robot_var", "robot_assign"],
  Comments: ["robot_comment", "robot_raw"],
};

export const expertCategories = {
  "Flow Control": [
    "robot_call",
    "robot_if",
    "robot_for",
    "robot_while",
    "robot_try",
    "robot_return",
    "robot_break",
    "robot_continue",
  ],
  Variables: ["robot_var", "robot_assign"],
  Comments: ["robot_comment", "robot_raw"],
};

export const containerBlocks = {
  robot_if_container: {
    type: "robot_if_container",
    message0: "IF branches",
    message1: "%1",
    args1: [{ type: "input_statement", name: "STACK" }],
    colour: "#2196F3",
    tooltip: "IF/ELSEIF/ELSE structure",
    helpUrl: "",
  },
  robot_if_elseif: {
    type: "robot_if_elseif",
    message0: "ELSE IF",
    previousStatement: null,
    nextStatement: null,
    colour: "#2196F3",
    tooltip: "Else-if branch",
    helpUrl: "",
  },
  robot_if_else: {
    type: "robot_if_else",
    message0: "ELSE",
    previousStatement: null,
    nextStatement: null,
    colour: "#2196F3",
    tooltip: "Else branch",
    helpUrl: "",
  },
  robot_try_container: {
    type: "robot_try_container",
    message0: "TRY structure",
    message1: "%1",
    args1: [{ type: "input_statement", name: "STACK" }],
    colour: "#9C27B0",
    tooltip: "TRY/EXCEPT/ELSE/FINALLY structure",
    helpUrl: "",
  },
  robot_try_except: {
    type: "robot_try_except",
    message0: "EXCEPT",
    previousStatement: null,
    nextStatement: null,
    colour: "#9C27B0",
    tooltip: "Except branch",
    helpUrl: "",
  },
  robot_try_else: {
    type: "robot_try_else",
    message0: "ELSE",
    previousStatement: null,
    nextStatement: null,
    colour: "#9C27B0",
    tooltip: "Else branch",
    helpUrl: "",
  },
  robot_try_finally: {
    type: "robot_try_finally",
    message0: "FINALLY",
    previousStatement: null,
    nextStatement: null,
    colour: "#9C27B0",
    tooltip: "Finally branch",
    helpUrl: "",
  },
  robot_call_args_container: {
    type: "robot_call_args_container",
    message0: "Arguments",
    message1: "%1",
    args1: [{ type: "input_statement", name: "STACK" }],
    colour: "#4CAF50",
    tooltip: "Call arguments",
    helpUrl: "",
  },
};
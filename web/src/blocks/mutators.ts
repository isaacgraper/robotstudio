import * as Blockly from "blockly";

const ifMutator = {
  saveExtraState: function (this: Blockly.Block) {
    return {
      elseifCount: (this as any).elseifCount_ || 0,
      hasElse: (this as any).hasElse_ || false,
    };
  },
  loadExtraState: function (this: Blockly.Block, state: { elseifCount: number; hasElse: boolean }) {
    (this as any).elseifCount_ = state.elseifCount || 0;
    (this as any).hasElse_ = state.hasElse || false;
    (this as any).updateShape_();
  },
  decompose: function (this: Blockly.Block, workspace: Blockly.Workspace) {
    const containerBlock = workspace.newBlock("robot_if_container");
    (containerBlock as any).initSvg?.();
    let connection = containerBlock.getInput("STACK")?.connection;
    for (let i = 0; i < ((this as any).elseifCount_ || 0); i++) {
      const elseifBlock = workspace.newBlock("robot_if_elseif");
      (elseifBlock as any).initSvg?.();
      if (connection && elseifBlock.previousConnection) {
        connection.connect(elseifBlock.previousConnection);
      }
      connection = elseifBlock.nextConnection;
    }
    if ((this as any).hasElse_) {
      const elseBlock = workspace.newBlock("robot_if_else");
      (elseBlock as any).initSvg?.();
      if (connection && elseBlock.previousConnection) {
        connection.connect(elseBlock.previousConnection);
      }
    }
    return containerBlock;
  },
  compose: function (this: Blockly.Block, containerBlock: Blockly.Block) {
    let clauseBlock = containerBlock.getInputTargetBlock("STACK") as Blockly.Block | null;
    (this as any).elseifCount_ = 0;
    (this as any).hasElse_ = false;
    while (clauseBlock) {
      if (clauseBlock.type === "robot_if_elseif") {
        (this as any).elseifCount_++;
      } else if (clauseBlock.type === "robot_if_else") {
        (this as any).hasElse_ = true;
      }
      clauseBlock = clauseBlock.nextConnection?.targetBlock() as Blockly.Block | null;
    }
    (this as any).updateShape_();
  },
  updateShape_: function (this: Blockly.Block) {
    const self = this as any;
    for (let i = 0; i < (self.elseifCount_ || 0); i++) {
      const conditionInput = self.getInput("ELSEIF_CONDITION_" + i);
      const thenInput = self.getInput("ELSEIF_THEN_" + i);
      if (conditionInput && thenInput) {
        conditionInput.setVisible(true);
        thenInput.setVisible(true);
      } else if (!conditionInput) {
        self.appendValueInput("ELSEIF_CONDITION_" + i)
          .setCheck(null)
          .appendField("ELSE IF");
        self.appendStatementInput("ELSEIF_THEN_" + i).appendField("DO");
      }
    }
    for (let i = self.elseifCount_ || 0; self.getInput("ELSEIF_CONDITION_" + i); i++) {
      self.removeInput("ELSEIF_CONDITION_" + i);
      self.removeInput("ELSEIF_THEN_" + i);
    }
    const elseInput = self.getInput("ELSE");
    if (self.hasElse_) {
      if (!elseInput) {
        self.appendStatementInput("ELSE").appendField("ELSE");
      } else {
        elseInput.setVisible(true);
      }
    } else if (elseInput) {
      elseInput.setVisible(false);
    }
  },
};

const tryMutator = {
  saveExtraState: function (this: Blockly.Block) {
    return {
      exceptCount: (this as any).exceptCount_ || 1,
      hasElse: (this as any).hasElse_ || false,
      hasFinally: (this as any).hasFinally_ || false,
    };
  },
  loadExtraState: function (
    this: Blockly.Block,
    state: { exceptCount: number; hasElse: boolean; hasFinally: boolean }
  ) {
    (this as any).exceptCount_ = state.exceptCount || 1;
    (this as any).hasElse_ = state.hasElse || false;
    (this as any).hasFinally_ = state.hasFinally || false;
    (this as any).updateShape_();
  },
  decompose: function (this: Blockly.Block, workspace: Blockly.Workspace) {
    const containerBlock = workspace.newBlock("robot_try_container");
    (containerBlock as any).initSvg?.();
    let connection = containerBlock.getInput("STACK")?.connection;
    for (let i = 0; i < ((this as any).exceptCount_ || 1); i++) {
      const exceptBlock = workspace.newBlock("robot_try_except");
      (exceptBlock as any).initSvg?.();
      if (connection && exceptBlock.previousConnection) {
        connection.connect(exceptBlock.previousConnection);
      }
      connection = exceptBlock.nextConnection;
    }
    if ((this as any).hasElse_) {
      const elseBlock = workspace.newBlock("robot_try_else");
      (elseBlock as any).initSvg?.();
      if (connection && elseBlock.previousConnection) {
        connection.connect(elseBlock.previousConnection);
      }
      connection = elseBlock.nextConnection;
    }
    if ((this as any).hasFinally_) {
      const finallyBlock = workspace.newBlock("robot_try_finally");
      (finallyBlock as any).initSvg?.();
      if (connection && finallyBlock.previousConnection) {
        connection.connect(finallyBlock.previousConnection);
      }
    }
    return containerBlock;
  },
  compose: function (this: Blockly.Block, containerBlock: Blockly.Block) {
    let clauseBlock = containerBlock.getInputTargetBlock("STACK") as Blockly.Block | null;
    (this as any).exceptCount_ = 0;
    (this as any).hasElse_ = false;
    (this as any).hasFinally_ = false;
    while (clauseBlock) {
      if (clauseBlock.type === "robot_try_except") {
        (this as any).exceptCount_++;
      } else if (clauseBlock.type === "robot_try_else") {
        (this as any).hasElse_ = true;
      } else if (clauseBlock.type === "robot_try_finally") {
        (this as any).hasFinally_ = true;
      }
      clauseBlock = clauseBlock.nextConnection?.targetBlock() as Blockly.Block | null;
    }
    (this as any).updateShape_();
  },
  updateShape_: function (this: Blockly.Block) {
    const self = this as any;
    for (let i = 0; i < (self.exceptCount_ || 1); i++) {
      const patternsInput = self.getInput("EXCEPT_PATTERNS_" + i);
      const varInput = self.getInput("EXCEPT_VAR_" + i);
      const doInput = self.getInput("EXCEPT_DO_" + i);
      if (patternsInput && varInput && doInput) {
        patternsInput.setVisible(true);
        varInput.setVisible(true);
        doInput.setVisible(true);
      } else if (!patternsInput) {
        self.appendValueInput("EXCEPT_PATTERNS_" + i)
          .setCheck(null)
          .appendField("EXCEPT");
        self.appendDummyInput("EXCEPT_VAR_" + i).appendField("AS").appendField(
          new Blockly.FieldTextInput("error", (value: string) => value.trim() || "error"),
          "EXCEPT_VAR_FIELD_" + i
        );
        self.appendStatementInput("EXCEPT_DO_" + i).appendField("DO");
      }
    }
    for (let i = self.exceptCount_ || 1; self.getInput("EXCEPT_PATTERNS_" + i); i++) {
      self.removeInput("EXCEPT_PATTERNS_" + i);
      self.removeInput("EXCEPT_VAR_" + i);
      self.removeInput("EXCEPT_DO_" + i);
    }
    const elseInput = self.getInput("ELSE");
    if (self.hasElse_) {
      if (!elseInput) {
        self.appendStatementInput("ELSE").appendField("ELSE");
      } else {
        elseInput.setVisible(true);
      }
    } else if (elseInput) {
      elseInput.setVisible(false);
    }
    const finallyInput = self.getInput("FINALLY");
    if (self.hasFinally_) {
      if (!finallyInput) {
        self.appendStatementInput("FINALLY").appendField("FINALLY");
      } else {
        finallyInput.setVisible(true);
      }
    } else if (finallyInput) {
      finallyInput.setVisible(false);
    }
  },
};

const callMutator = {
  saveExtraState: function (this: Blockly.Block) {
    return { argCount: (this as any).argCount_ || 0 };
  },
  loadExtraState: function (this: Blockly.Block, state: { argCount: number }) {
    (this as any).argCount_ = state.argCount || 0;
    (this as any).updateShape_();
  },
  decompose: function (this: Blockly.Block, workspace: Blockly.Workspace) {
    const containerBlock = workspace.newBlock("robot_call_args_container");
    (containerBlock as any).initSvg?.();
    let connection = containerBlock.getInput("STACK")?.connection;
    for (let i = 0; i < ((this as any).argCount_ || 0); i++) {
      const argBlock = workspace.newBlock("robot_argument");
      (argBlock as any).initSvg?.();
      if (connection && argBlock.previousConnection) {
        connection.connect(argBlock.previousConnection);
      }
      connection = argBlock.nextConnection;
    }
    return containerBlock;
  },
  compose: function (this: Blockly.Block, containerBlock: Blockly.Block) {
    let argBlock = containerBlock.getInputTargetBlock("STACK") as Blockly.Block | null;
    (this as any).argCount_ = 0;
    while (argBlock) {
      (this as any).argCount_++;
      argBlock = argBlock.nextConnection?.targetBlock() as Blockly.Block | null;
    }
    (this as any).updateShape_();
  },
  updateShape_: function (this: Blockly.Block) {
    const self = this as any;
    const argsInput = self.getInput("ARGS");
    if (argsInput) {
      argsInput.connection?.targetBlock()?.dispose();
    }
    self.removeInput("ARGS");
    self.appendStatementInput("ARGS").appendField("WITH");
    const connection = self.getInput("ARGS")?.connection;
    if (connection) {
      let lastBlock: Blockly.Block | null = null;
      for (let i = 0; i < (self.argCount_ || 0); i++) {
        const argBlock = self.workspace.newBlock("robot_argument");
        (argBlock as any).initSvg?.();
        if (lastBlock) {
          lastBlock.nextConnection?.connect(argBlock.previousConnection);
        } else {
          connection.connect(argBlock.previousConnection);
        }
        lastBlock = argBlock;
      }
    }
  },
};

export const mutators = {
  if_mutator: ifMutator,
  try_mutator: tryMutator,
  call_mutator: callMutator,
};
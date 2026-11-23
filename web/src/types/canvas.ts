export interface CanvasDocument {
  version: number;
  name: string;
  settings: SuiteSettings;
  tests: TestCase[];
  keywords: KeywordDefinition[];
}

export interface SuiteSettings {
  documentation: string;
  libraries: LibraryImport[];
  resources: ResourceImport[];
  variables: Variable[];
  suite_setup: CallStep | null;
  suite_teardown: CallStep | null;
  test_setup: CallStep | null;
  test_teardown: CallStep | null;
  force_tags: string[];
  default_tags: string[];
  test_timeout: string | null;
  metadata: Record<string, string>;
}

export interface LibraryImport {
  name: string;
  alias: string | null;
  args: string[];
}

export interface ResourceImport {
  path: string;
}

export interface Variable {
  name: string;
  value: string;
}

export interface TestCase {
  id: string;
  name: string;
  documentation: string;
  tags: string[];
  setup: CallStep | null;
  teardown: CallStep | null;
  timeout: string | null;
  template: string | null;
  steps: Step[];
}

export interface KeywordDefinition {
  name: string;
  arguments: string[];
  documentation: string;
  tags: string[];
  teardown: CallStep | null;
  steps: Step[];
}

export interface CallStep {
  type: "call";
  keyword: KeywordRef;
  args: Argument[];
  assign: string[];
  comment: string | null;
}

export interface IfStep {
  type: "if";
  condition: string;
  steps: Step[];
  branches: IfStep[];
  else_steps: Step[];
}

export interface ForStep {
  type: "for";
  variables: string[];
  values: string[];
  flavor: "in" | "in_range" | "in_enumerate" | "in_zip";
  steps: Step[];
}

export interface WhileStep {
  type: "while";
  condition: string;
  limit: string | null;
  until: boolean;
  steps: Step[];
}

export interface TryStep {
  type: "try";
  steps: Step[];
  excepts: ExceptClause[];
  else_steps: Step[];
  finally_steps: Step[];
}

export interface ExceptClause {
  patterns: string[];
  variable: string | null;
  steps: Step[];
}

export interface VarStep {
  type: "var";
  name: string;
  value: string;
  scope: string | null;
}

export interface ReturnStep {
  type: "return";
  values: string[];
}

export interface BreakStep {
  type: "break";
}

export interface ContinueStep {
  type: "continue";
}

export interface CommentStep {
  type: "comment";
  text: string;
}

export interface RawStep {
  type: "raw";
  lines: string[];
}

export type Step =
  | CallStep
  | IfStep
  | ForStep
  | WhileStep
  | TryStep
  | VarStep
  | ReturnStep
  | BreakStep
  | ContinueStep
  | CommentStep
  | RawStep;

export interface Argument {
  name: string | null;
  value: string;
}

export interface KeywordRef {
  name: string;
  source: string | null;
  embedded: Record<string, string>;
}
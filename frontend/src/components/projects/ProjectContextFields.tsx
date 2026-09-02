export interface ProjectContextValue {
  tone:
    | "Academic"
    | "Neutral"
    | "Persuasive"
    | "Analytical"
    | "Conversational";

  writingStyle:
    | "Formal"
    | "Clear"
    | "Concise"
    | "Descriptive"
    | "Creative";

  academicLevel:
    | "MiddleSchool"
    | "HighSchool"
    | "Undergraduate"
    | "Graduate";

  language: "Portuguese" | "English";

  essayType:
    | "Argumentative"
    | "Expository"
    | "Descriptive"
    | "Narrative"
    | "Analytical";

  additionalInstructions?: string;
}

export const DEFAULT_PROJECT_CONTEXT: ProjectContextValue = {
  tone: "Academic",
  writingStyle: "Formal",
  academicLevel: "Graduate",
  language: "English",
  essayType: "Argumentative",
  additionalInstructions: "",
};

const TONE_OPTIONS: ProjectContextValue["tone"][] = [
  "Academic",
  "Neutral",
  "Persuasive",
  "Analytical",
  "Conversational",
];
const WRITING_STYLE_OPTIONS: ProjectContextValue["writingStyle"][] = [
  "Formal",
  "Clear",
  "Concise",
  "Descriptive",
  "Creative",
];
const ACADEMIC_LEVEL_OPTIONS: Array<{ value: ProjectContextValue["academicLevel"]; label: string }> = [
  { value: "MiddleSchool", label: "Middle school" },
  { value: "HighSchool", label: "High school" },
  { value: "Undergraduate", label: "Undergraduate" },
  { value: "Graduate", label: "Graduate" },
];
const LANGUAGE_OPTIONS: ProjectContextValue["language"][] = ["Portuguese", "English"];
const ESSAY_TYPE_OPTIONS: ProjectContextValue["essayType"][] = [
  "Argumentative",
  "Expository",
  "Descriptive",
  "Narrative",
  "Analytical",
];

interface ProjectContextFieldsProps {
  value: ProjectContextValue;
  disabled: boolean;
  onChange: (value: ProjectContextValue) => void;
}

export function ProjectContextFields({ value, disabled, onChange }: ProjectContextFieldsProps) {
  return (
    <fieldset className="project-context-fields" disabled={disabled}>
      <legend>Writing context</legend>
      <p>Set a lightweight starting point for Cowriter&apos;s project-specific guidance.</p>
      <div className="project-context-selects">
        <label>
          <span>Tone</span>
          <select
            value={value.tone}
            onChange={(event) => onChange({ ...value, tone: event.target.value as ProjectContextValue["tone"] })}
          >
            {TONE_OPTIONS.map((option) => <option key={option}>{option}</option>)}
          </select>
        </label>
        <label>
          <span>Style</span>
          <select
            value={value.writingStyle}
            onChange={(event) => onChange({ ...value, writingStyle: event.target.value as ProjectContextValue["writingStyle"] })}
          >
            {WRITING_STYLE_OPTIONS.map((option) => <option key={option}>{option}</option>)}
          </select>
        </label>
        <label>
          <span>Academic level</span>
          <select
            value={value.academicLevel}
            onChange={(event) => onChange({ ...value, academicLevel: event.target.value as ProjectContextValue["academicLevel"] })}
          >
            {ACADEMIC_LEVEL_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Language</span>
          <select
            value={value.language}
            onChange={(event) => onChange({ ...value, language: event.target.value as ProjectContextValue["language"] })}
          >
            {LANGUAGE_OPTIONS.map((option) => <option key={option}>{option}</option>)}
          </select>
        </label>
        <label>
          <span>Essay type</span>
          <select
            value={value.essayType}
            onChange={(event) => onChange({ ...value, essayType: event.target.value as ProjectContextValue["essayType"] })}
          >
            {ESSAY_TYPE_OPTIONS.map((option) => <option key={option}>{option}</option>)}
          </select>
        </label>
      </div>
      <label>
        <span>Additional instructions</span>
        <textarea
          value={value.additionalInstructions}
          rows={3}
          maxLength={110}
          placeholder="Citation expectations, structural preferences, or other writing rules"
          onChange={(event) => onChange({ ...value, additionalInstructions: event.target.value })}
        />
      </label>
    </fieldset>
  );
}

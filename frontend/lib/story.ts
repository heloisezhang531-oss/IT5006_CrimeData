export type StorySectionConfig = {
  id: string;
  chapter: string;
  title: string;
  subtitle: string;
  duration: string;
  sourceRef: string;
};

export type NarrativeKPI = {
  label: string;
  value: number;
  unit?: string;
  precision?: number;
  tone?: "neutral" | "accent" | "positive" | "warning";
};

export type EvidencePanel = {
  title: string;
  summary: string;
  sourceRef: string;
};

export const launchSections: StorySectionConfig[] = [
  {
    id: "opening",
    chapter: "00:00-05:00",
    title: "Problem Definition & Value Proposition",
    subtitle: "Predict next-month high-risk communities using a 75th-percentile binary target.",
    duration: "5 min",
    sourceRef: "Phase2 §1",
  },
  {
    id: "data-foundation",
    chapter: "05:00-15:00",
    title: "Data Foundation & Trust",
    subtitle: "Chicago + FBI NIBRS harmonization pipeline with reproducible preprocessing.",
    duration: "10 min",
    sourceRef: "Phase1 Dataset + Phase2 §2",
  },
  {
    id: "eda-space-time",
    chapter: "15:00-27:00",
    title: "EDA Story I: Space & Time",
    subtitle: "West/South concentration, 2020 structural break, and hourly pattern shifts.",
    duration: "12 min",
    sourceRef: "Phase1 §2-§3",
  },
  {
    id: "eda-crime-domestic",
    chapter: "27:00-35:00",
    title: "EDA Story II: Crime Mix & Domestic",
    subtitle: "Rising offense categories and domestic burden for stratified prevention.",
    duration: "8 min",
    sourceRef: "Phase1 §4-§6",
  },
  {
    id: "modeling-core",
    chapter: "35:00-47:00",
    title: "Modeling Core Results",
    subtitle: "Logistic Regression vs Random Forest vs XGBoost on Chicago holdout.",
    duration: "12 min",
    sourceRef: "Phase2 §3-§4",
  },
  {
    id: "hardship-ablation",
    chapter: "47:00-54:00",
    title: "Hardship Ablation Insight",
    subtitle: "Hardship adds meaningful lift in nonlinear models.",
    duration: "7 min",
    sourceRef: "Phase2 §4.6",
  },
  {
    id: "generalization",
    chapter: "54:00-58:00",
    title: "External Generalization",
    subtitle: "Strong temporal transfer within Chicago, partial robustness on NIBRS.",
    duration: "4 min",
    sourceRef: "Phase2 §4.7",
  },
  {
    id: "roadmap",
    chapter: "58:00-60:00",
    title: "Limitations & Roadmap",
    subtitle: "Move toward multi-tier risk, dynamic context, and fairness auditing.",
    duration: "2 min",
    sourceRef: "Phase2 §5.1-§6",
  },
];

export const openingKpis: NarrativeKPI[] = [
  { label: "Chicago Crime Records", value: 1048576, unit: "events", tone: "accent" },
  { label: "Communities Covered", value: 77, unit: "areas", tone: "neutral" },
  { label: "Forecast Horizon", value: 1, unit: "month", tone: "positive" },
  { label: "Domestic Share", value: 19.3, unit: "%", precision: 1, tone: "warning" },
];

export const reportAnchors = {
  phase1: "docs/Team16_Phase1_IT5006_AY2526Sem2.pdf",
  phase2: "docs/Team16_Phase2_IT5006_AY2526Sem2.pdf.pdf",
} as const;

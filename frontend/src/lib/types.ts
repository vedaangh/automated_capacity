export type SessionStatus = "running" | "completed" | "failed" | "idle";

export type CardType = "user" | "research" | "engineering" | "simulation" | "experiment";

export type ExperimentStatus = "kept" | "discarded" | "crash" | "running" | "baseline";

export interface Session {
  id: string;
  name: string;
  date: string;
  status: SessionStatus;
  domain: string;
  cards: Card[];
}

export interface Card {
  id: string;
  type: CardType;
  timestamp: string;
  content: UserCard | ResearchCard | EngineeringCard | SimulationCard | ExperimentCard;
}

export interface UserCard {
  message: string;
}

export interface ResearchAgentOutput {
  name: string;
  query: string;
  findings: string;
  status: "done" | "running";
}

export interface ResearchCard {
  summary: string;
  agents: ResearchAgentOutput[];
}

export interface EngineeringCard {
  summary: string;
  status: "building" | "validating" | "streaming" | "done";
  trace: string[];
  simSpec?: {
    name: string;
    metric: string;
    direction: "minimize" | "maximize";
    timeoutSeconds: number;
  };
}

export interface SimulationCard {
  windowCount: number;
  maxWindows: number;
  connected: boolean;
}

export interface ExperimentCard {
  experiments: Experiment[];
}

export interface Experiment {
  id: number;
  status: ExperimentStatus;
  metric?: number;
  prevMetric?: number;
  description: string;
  reasoning?: string;
  diff?: string;
  elapsed?: number;
  budget?: number;
}

export type SessionStatus = "research" | "deciding" | "engineering" | "science" | "complete" | "failed" | "idle";

export type CardType = "user" | "research" | "engineering" | "simulation" | "experiment" | "status" | "findings" | "error";

export type ExperimentStatus = "kept" | "discarded" | "crash" | "running" | "baseline";

export interface Session {
  id: string;
  name: string;
  date: string;
  status: SessionStatus;
  cards: Card[];
  /** If connected to a live run, the backend run ID */
  runId?: string;
}

export interface Card {
  id: string;
  type: CardType;
  timestamp: string;
  content: UserCard | ResearchCard | EngineeringCard | SimulationCard | ExperimentCard | StatusCard | FindingsCard | ErrorCard;
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
  streamIds: string[];
}

export interface ExperimentCard {
  experiments: Experiment[];
}

export interface StatusCard {
  phase: string;
  message: string;
}

export interface FindingsCard {
  text: string;
}

export interface ErrorCard {
  message: string;
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

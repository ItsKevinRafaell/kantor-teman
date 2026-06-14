// Shared types for chat module

export interface ChatProject {
  id: string;
  name: string;
  description?: string;
  system_prompt?: string;
  default_model: string;
  context_window_size: number;
  created_at: string;
}

export interface ChatConversation {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  tokens_used: number;
  model_used?: string;
  created_at: string;
}

export interface ChatMemory {
  id: string;
  project_id: string;
  content: string;
  created_at: string;
}

export interface ChatModel {
  id: string;
  name: string;
  description: string;
}

export const DEFAULT_MODELS: ChatModel[] = [
  { id: "combo-genflow", name: "combo-genflow", description: "Combo default 9router" },
  { id: "combo-clarifie", name: "combo-clarifie", description: "Combo analisis 9router" },
  { id: "combo-databytes", name: "combo-databytes", description: "Combo data 9router" },
];

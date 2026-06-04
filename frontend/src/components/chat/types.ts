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
  { id: "glm-5", name: "GLM-5", description: "Model cepat dan efisien" },
  { id: "gpt-4o-mini", name: "GPT-4o Mini", description: "Model ringan OpenAI" },
  { id: "deepseek-chat", name: "DeepSeek Chat", description: "Model cepat dan murah" },
];

export interface Message {
  role: "user" | "assistant";
  content: string;
  cypher?: string | null;
}

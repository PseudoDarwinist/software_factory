// Block system core types for the new PRD editor

export type BlockType =
  | 'paragraph'
  | 'header'
  | 'bullet-list'
  | 'numbered-list'
  | 'code'
  | 'mermaid-diagram'
  | 'table'
  | 'hr';

export interface ParagraphContent {
  text: string;
}

export interface HeaderContent {
  level: 1 | 2 | 3 | 4 | 5 | 6;
  text: string;
}

export interface ListContent {
  items: string[];
}

export interface CodeContent {
  language?: string;
  code: string;
}

export interface MermaidContent {
  code: string;
  diagramType?: 'flowchart' | 'class' | 'sequence' | 'state' | 'gantt' | 'pie' | 'er' | 'user-journey' | 'other';
}

export interface TableContent {
  header?: string[];
  rows: string[][];
}

export type BlockContent =
  | ParagraphContent
  | HeaderContent
  | ListContent
  | CodeContent
  | MermaidContent
  | TableContent
  | null;

export interface BlockMetadata {
  orderIndex?: number;
  parentId?: string | null;
  derivedFrom?: 'markdown' | 'editorjs' | 'ai' | 'manual';
  errors?: string[];
  createdAt?: string; // ISO
  updatedAt?: string; // ISO
}

export interface Block {
  id: string;
  type: BlockType;
  content: BlockContent;
  meta?: BlockMetadata;
}

export interface BlockDocumentMeta {
  id?: string;
  title?: string;
  outline?: { id: string; text: string; level: number }[];
}

export interface BlockDocument {
  meta?: BlockDocumentMeta;
  blocks: Block[];
}


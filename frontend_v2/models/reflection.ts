import { BaseEntity, ID, Emotion } from './common';

export interface CBTSession extends BaseEntity {
  userId: ID;
  emotion: Emotion;
  situation: string;
  thoughts: string;
  evidence: string;
  alternativeThoughts?: string;
  actionPlan?: string;
  aiAnalysis?: string;
  isComplete: boolean;
}

export interface Reflection extends BaseEntity {
  userId: ID;
  content: string;
  primaryEmotion: Emotion;
  relatedEmotions?: Emotion[];
  cbtSession?: CBTSession;
  insights?: string[];
  aiSummary?: string;
}

export interface ReflectionStep {
  id: number;
  title: string;
  description: string;
  field: keyof CBTSession;
  placeholder: string;
}

export const REFLECTION_STEPS: ReflectionStep[] = [
  {
    id: 1,
    title: 'How are you feeling?',
    description: 'Start by identifying the emotion you want to explore.',
    field: 'emotion',
    placeholder: 'Select your primary emotion...',
  },
  {
    id: 2,
    title: 'What happened?',
    description: 'Describe the situation that triggered this feeling.',
    field: 'situation',
    placeholder: 'Describe the situation...',
  },
  {
    id: 3,
    title: 'What are you thinking?',
    description: 'What thoughts are running through your mind?',
    field: 'thoughts',
    placeholder: 'Share your thoughts...',
  },
  {
    id: 4,
    title: 'What is the evidence?',
    description: 'What facts support or challenge your thoughts?',
    field: 'evidence',
    placeholder: 'Describe the evidence...',
  },
];

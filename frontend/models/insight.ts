import { BaseEntity, ID } from './common';

export type InsightType = 'communication' | 'emotional' | 'stress' | 'social' | 'wellbeing';
export type TrendDirection = 'improving' | 'declining' | 'stable';

export interface Pattern {
  name: string;
  frequency: number;
  trend: TrendDirection;
  description: string;
}

export interface Insight extends BaseEntity {
  userId: ID;
  type: InsightType;
  title: string;
  description: string;
  patterns: Pattern[];
  trends: {
    period: 'week' | 'month' | 'quarter';
    values: number[];
    labels: string[];
  };
  recommendations?: string[];
  dataPoints: number;
  confidence: number; // 0-100
}

export interface InsightSnapshot {
  timestamp: number;
  insights: Insight[];
  summary: string;
}

export interface GenerateInsightRequest {
  startDate?: number;
  endDate?: number;
  types?: InsightType[];
}

export interface InsightExportRequest {
  format: 'pdf' | 'json' | 'csv';
  includeCharts: boolean;
  dateRange: {
    start: number;
    end: number;
  };
}

export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: any;
}

export interface Activity {
  id: number;
  name: string;
  category: string;
  goal: number;
  active: boolean;
}

export interface Entry {
  id: number;
  date: string;
  activity: string;
  value: number;
  note?: string;
}

export interface ActivityDistributionBucket {
  category: string;
  count: number;
  percent: number;
}

export interface AverageGoalFulfilment {
  last_7_days: number;
  last_30_days: number;
}

export interface CategoryAverageGoalFulfilment extends AverageGoalFulfilment {
  category: string;
}

export interface ActiveDaysRatio {
  active_days: number;
  total_days: number;
  percent: number;
}

export interface PositiveNegativeSummary {
  positive: number;
  negative: number;
  ratio: number;
}

export interface ConsistentActivity {
  name: string;
  consistency_percent: number;
}

export interface ConsistentActivitiesByCategory {
  category: string;
  activities: ConsistentActivity[];
}

export interface StatsSnapshot {
  goal_completion_today: number;
  streak_length: number;
  activity_distribution: ActivityDistributionBucket[];
  avg_goal_fulfillment: AverageGoalFulfilment;
  avg_goal_fulfillment_by_category: CategoryAverageGoalFulfilment[];
  active_days_ratio: ActiveDaysRatio;
  positive_vs_negative: PositiveNegativeSummary;
  top_consistent_activities_by_category: ConsistentActivitiesByCategory[];
}

export {};

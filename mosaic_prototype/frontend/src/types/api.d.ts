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

export interface StatsSnapshot {
  completion: number;
  streak: number;
  fulfilment: number;
  polarity: Record<string, number>;
  consistency: number;
}

export {};

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

export interface ApiError {
  message: string;
  code?: number;
}

export {};

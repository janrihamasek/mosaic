import type { CanonicalWearableReading, ReadOptions } from './types';

export interface HealthConnectAgentReadResult {
  readings: CanonicalWearableReading[];
}

export interface HealthConnectAgentPlugin {
  readSteps(options?: ReadOptions): Promise<HealthConnectAgentReadResult>;
  readHeartRate(options?: ReadOptions): Promise<HealthConnectAgentReadResult>;
  readSleepSessions(options?: ReadOptions): Promise<HealthConnectAgentReadResult>;
}

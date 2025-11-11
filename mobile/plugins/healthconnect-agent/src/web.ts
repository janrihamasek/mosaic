import type { HealthConnectAgentPlugin, HealthConnectAgentReadResult } from './definitions';

const NOOP_RESULT: HealthConnectAgentReadResult = { readings: [] };

export class HealthConnectAgentWeb implements HealthConnectAgentPlugin {
  async readSteps(): Promise<HealthConnectAgentReadResult> {
    return NOOP_RESULT;
  }

  async readHeartRate(): Promise<HealthConnectAgentReadResult> {
    return NOOP_RESULT;
  }

  async readSleepSessions(): Promise<HealthConnectAgentReadResult> {
    return NOOP_RESULT;
  }
}

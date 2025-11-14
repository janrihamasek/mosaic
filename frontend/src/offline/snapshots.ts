import { readSnapshot, saveSnapshot } from "./db";
import type { TodayRow } from "../types/store";
import type { Activity } from "../types/api";

const TODAY_PREFIX = "today::";
const ACTIVITIES_ALL_KEY = "activities::all";
const ACTIVITIES_ACTIVE_KEY = "activities::active";

export const snapshotKeys = {
  today: (date: string) => `${TODAY_PREFIX}${date}`,
  activitiesAll: ACTIVITIES_ALL_KEY,
  activitiesActive: ACTIVITIES_ACTIVE_KEY,
};

export async function saveTodaySnapshot(date: string, rows: TodayRow[]): Promise<void> {
  await saveSnapshot(snapshotKeys.today(date), rows);
}

export async function readTodaySnapshot(date: string): Promise<TodayRow[] | null> {
  const snapshot = await readSnapshot<TodayRow[]>(snapshotKeys.today(date));
  return snapshot?.data ?? null;
}

export async function saveActivitiesSnapshot(active: Activity[], all: Activity[]): Promise<void> {
  await Promise.all([
    saveSnapshot<Activity[]>(snapshotKeys.activitiesActive, active),
    saveSnapshot<Activity[]>(snapshotKeys.activitiesAll, all),
  ]);
}

export async function readActivitiesSnapshot(): Promise<{ active: Activity[]; all: Activity[] } | null> {
  const activeSnapshot = await readSnapshot<Activity[]>(snapshotKeys.activitiesActive);
  const allSnapshot = await readSnapshot<Activity[]>(snapshotKeys.activitiesAll);
  if (!activeSnapshot && !allSnapshot) {
    return null;
  }
  return {
    active: activeSnapshot?.data ?? [],
    all: allSnapshot?.data ?? [],
  };
}

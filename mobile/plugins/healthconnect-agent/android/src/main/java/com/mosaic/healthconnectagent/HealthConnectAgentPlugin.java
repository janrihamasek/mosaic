package com.mosaic.healthconnectagent;

import android.content.Context;

import androidx.annotation.NonNull;
import androidx.health.connect.client.HealthConnectClient;
import androidx.health.connect.client.records.HeartRateRecord;
import androidx.health.connect.client.records.Record;
import androidx.health.connect.client.records.SleepSessionRecord;
import androidx.health.connect.client.records.StepsRecord;
import androidx.health.connect.client.request.ReadRecordsRequest;
import androidx.health.connect.client.time.TimeRangeFilter;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.time.Duration;
import java.time.Instant;
import java.util.List;

@CapacitorPlugin(name = "HealthConnectAgent")
public class HealthConnectAgentPlugin extends Plugin {
  private static final int DEFAULT_LIMIT = 120;

  private HealthConnectClient healthConnectClient() {
    Context context = getContext();
    return HealthConnectClient.getOrCreate(context);
  }

  @PluginMethod
  public void readSteps(@NonNull PluginCall call) {
    Instant fallbackStart = Instant.now().minus(Duration.ofDays(1));
    queryRecords(call, StepsRecord.class, "steps", fallbackStart);
  }

  @PluginMethod
  public void readHeartRate(@NonNull PluginCall call) {
    Instant fallbackStart = Instant.now().minus(Duration.ofHours(2));
    queryRecords(call, HeartRateRecord.class, "heart_rate", fallbackStart);
  }

  @PluginMethod
  public void readSleepSessions(@NonNull PluginCall call) {
    Instant fallbackStart = Instant.now().minus(Duration.ofDays(1));
    queryRecords(call, SleepSessionRecord.class, "sleep", fallbackStart);
  }

  private <T extends Record> void queryRecords(
      PluginCall call,
      Class<T> recordType,
      String type,
      Instant fallbackStart) {
    long now = Instant.now().toEpochMilli();
    long start = call.getLong("start", fallbackStart.toEpochMilli());
    long end = call.getLong("end", now);
    int limit = call.getInt("limit", DEFAULT_LIMIT);

    ReadRecordsRequest request = new ReadRecordsRequest.Builder<>(
        recordType,
        TimeRangeFilter.between(Instant.ofEpochMilli(start), Instant.ofEpochMilli(end)))
        .setLimit(limit)
        .build();

    healthConnectClient().readRecords(request)
        .addOnSuccessListener(records -> call.resolve(buildResult(records, type)))
        .addOnFailureListener(error -> call.reject(type + "_failure", error));
  }

  private JSObject buildResult(List<? extends Record> records, String type) {
    JSArray normalized = new JSArray();
    if (records != null) {
      for (Record record : records) {
        normalized.put(toCanonical(record, type));
      }
    }
    JSObject payload = new JSObject();
    payload.put("readings", normalized);
    return payload;
  }

  private JSObject toCanonical(Record record, String type) {
    JSObject entry = new JSObject();
    entry.put("type", type);
    Instant start = record.getStartTime();
    Instant end = record.getEndTime();
    entry.put("start", start.toString());
    entry.put("end", end.toString());

    JSObject fields = new JSObject();
    if (record instanceof StepsRecord) {
      fields.put("count", ((StepsRecord) record).getCount());
    }
    if (record instanceof HeartRateRecord) {
      fields.put("bpm", ((HeartRateRecord) record).getBeatsPerMinute());
    }
    if (record instanceof SleepSessionRecord) {
      SleepSessionRecord sleep = (SleepSessionRecord) record;
      fields.put("stage", sleep.getStage().toString());
      fields.put("confidence", sleep.getConfidence());
    }

    entry.put("fields", fields);
    entry.put("dedupe_key", createDedupeKey(type, start, end, fields));
    return entry;
  }

  private String createDedupeKey(String type, Instant start, Instant end, JSObject fields) {
    String fieldHash = fields.toString();
    return type + "::" + start.toEpochMilli() + "::" + end.toEpochMilli() + "::" + fieldHash;
  }
}

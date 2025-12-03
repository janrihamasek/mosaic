# Database ERD (current)

```mermaid
erDiagram
    USERS ||--o{ ACTIVITIES : owns
    USERS ||--o{ ENTRIES : owns
    ACTIVITIES ||--o{ ENTRIES : referenced_by_name

    USERS {
      int id PK
      string username
      string password_hash
      datetime created_at
    }

    ACTIVITIES {
      int id PK
      string name "UNIQUE (global)"
      string category
      string activity_type
      float goal
      text description
      bool active
      int frequency_per_day
      int frequency_per_week
      string deactivated_at
    }

    ENTRIES {
      int id PK
      string date
      string activity "references activities.name (app-level)"
      text description
      float value
      text note
      string activity_category
      float activity_goal
    }

    BACKUP_SETTINGS {
      int id PK
      bool enabled
      int interval_minutes
      datetime last_run
    }
```

**Known gaps:**
- `activities` and `entries` are not scoped by `user_id` (global namespace).
- No FK between `entries.activity` and `activities.id/name` (app enforces via code).

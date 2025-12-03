# Database ERD (current)

```mermaid
erDiagram
    USERS ||--o{ ACTIVITIES : owns
    USERS ||--o{ ENTRIES : owns
    USERS ||--|| BACKUP_SETTINGS : has_one
    ACTIVITIES ||--o{ ENTRIES : referenced_by_name

    USERS {
      int id PK
      string username
      string password_hash
      datetime created_at
      bool is_admin
      string display_name
    }

    ACTIVITIES {
      int id PK
      int user_id FK "ON DELETE CASCADE"
      string name "UNIQUE (user_id, name)"
      string category
      string activity_type
      float goal
      text description
      bool active
      int frequency_per_day
      int frequency_per_week
      string deactivated_at
      bool is_system
    }

    ENTRIES {
      int id PK
      int user_id FK "ON DELETE CASCADE"
      string date
      string activity "references activities.name (app-level)"
      text description
      float value
      text note
      string activity_category
      float activity_goal
      string activity_type
      string UNIQUE "user_id, date, activity"
    }

    BACKUP_SETTINGS {
      int id PK
      int user_id FK "ON DELETE CASCADE"
      bool enabled
      int interval_minutes
      datetime last_run
      string UNIQUE "user_id"
    }
```

**Notes:**
- All user-owned tables include `user_id` and cascade on user deletion.
- Activity names are unique per user; different users can share names safely.
- Entries are scoped by `(user_id, date, activity)`; no cross-user leakage.

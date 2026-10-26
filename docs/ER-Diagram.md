# Study Shuttle System ER model

The model below matches the student self-service application. Accounts authenticate individual students. Students can enroll in many subjects, and each subject can have many students through `STUDENT_SUBJECT`.

```mermaid
erDiagram
    STUDENT ||--|| ACCOUNT : authenticates_with
    STUDENT ||--o{ STUDENT_SUBJECT : enrolls
    SUBJECT ||--o{ STUDENT_SUBJECT : has_enrollments
    STUDENT ||--o{ STUDY_TASK : owns
    SUBJECT ||--o{ STUDY_TASK : categorizes
    STUDENT ||--o{ STUDY_SESSION : records
    SUBJECT ||--o{ STUDY_SESSION : covers
    STUDY_SESSION ||--o{ DIFFICULTY : encounters
    STUDENT ||--o{ STUDENT_STRESS : records
    STUDY_SESSION o|--o{ STUDENT_STRESS : may_be_related_to
    STUDENT ||--o{ PERFORMANCE : receives
    SUBJECT ||--o{ PERFORMANCE : assessed_in

    STUDENT {
        int student_id PK
        string name
        string program
        int semester
    }
    ACCOUNT {
        string email PK
        string username UK
        string password_hash
        int student_id FK_UK
    }
    SUBJECT {
        int subject_id PK
        string subject_name
        string subject_code UK
        string difficulty_level
    }
    STUDENT_SUBJECT {
        int student_id PK_FK
        int subject_id PK_FK
        date enrolled_on
    }
    STUDY_TASK {
        int task_id PK
        int student_id FK
        int subject_id FK
        string task_name
        date deadline
        string priority
        string status
    }
    STUDY_SESSION {
        int session_id PK
        int student_id FK
        int subject_id FK
        date session_date
        int duration_minutes
        int productivity
        string notes
    }
    DIFFICULTY {
        int difficulty_id PK
        int session_id FK
        string difficulty_type
        string description
        string severity
        boolean solved
        date resolved_date
    }
    STUDENT_STRESS {
        int stress_id PK
        int student_id FK
        int session_id FK_optional
        int stress_level
        string reason
        string notes
        date recorded_date
    }
    PERFORMANCE {
        int performance_id PK
        int student_id FK
        int subject_id FK
        string assessment_name
        float marks_obtained
        float max_marks
        date assessment_date
    }
```

Password values are stored as salted password hashes. `STUDENT_SUBJECT` resolves the many-to-many student/subject relationship. Task, session, and performance rows each refer directly to their student and subject so reports can be scoped to the signed-in student.

-- =============================================================
-- PMO 运维管理平台　数据库初始化 DDL
-- 版本：v1.0（对应 TSD v3.0 §3）　数据库：PostgreSQL 15
-- 说明：
--   1. 本文件由《PMO平台技术开发规格说明书_v3.0》§3 数据字典翻译而来，
--      两者冲突时以 TSD 主文档为准，并回改本文件。
--   2. 所有业务表含 created_at / updated_at / deleted_at，软删除不物理删除。
--   3. 枚举用 VARCHAR + 应用层常量，不用 PG enum 类型（改枚举免改表）。
--   4. 金额 NUMERIC(14,2)，百分比 NUMERIC(5,2)，时间 TIMESTAMPTZ(UTC)。
-- =============================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- 中文模糊检索
CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- 如需 gen_random_uuid

-- -------------------------------------------------------------
-- 3.1 组织与身份域（M10）
-- -------------------------------------------------------------
CREATE TABLE dept (
  id               BIGSERIAL PRIMARY KEY,
  name             VARCHAR(128) NOT NULL,
  parent_id        BIGINT REFERENCES dept(id),
  source_id        VARCHAR(64)  NOT NULL,
  path             VARCHAR(512) NOT NULL,
  manager_user_id  BIGINT,
  order_no         INT NOT NULL DEFAULT 0,
  status           VARCHAR(16)  NOT NULL DEFAULT 'active',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_dept_path ON dept(path);
CREATE INDEX idx_dept_parent ON dept(parent_id);

CREATE TABLE "user" (
  id               BIGSERIAL PRIMARY KEY,
  employee_no      VARCHAR(32)  NOT NULL,
  name             VARCHAR(64)  NOT NULL,
  email            VARCHAR(128) NOT NULL,
  dept_id          BIGINT REFERENCES dept(id),
  title            VARCHAR(64),
  avatar_url       VARCHAR(512),
  status           VARCHAR(16)  NOT NULL DEFAULT 'active',
  src_ldap         BOOLEAN NOT NULL DEFAULT false,
  src_wechat       BOOLEAN NOT NULL DEFAULT false,
  src_synced_at    TIMESTAMPTZ,
  password_hash    VARCHAR(255),
  is_external      BOOLEAN NOT NULL DEFAULT false,
  last_login_at    TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE UNIQUE INDEX uk_user_employee_no ON "user"(employee_no) WHERE deleted_at IS NULL;
CREATE INDEX idx_user_dept_status ON "user"(dept_id, status);
CREATE INDEX idx_user_name_trgm ON "user" USING gin (name gin_trgm_ops);

CREATE TABLE external_account (
  id               BIGSERIAL PRIMARY KEY,
  login_name       VARCHAR(64)  NOT NULL UNIQUE,
  display_name     VARCHAR(64)  NOT NULL,
  acct_type        VARCHAR(32)  NOT NULL,
  org_name         VARCHAR(128) NOT NULL,
  project_ids      JSONB NOT NULL DEFAULT '[]',
  field_whitelist  JSONB NOT NULL DEFAULT '{}',
  status           VARCHAR(16)  NOT NULL DEFAULT 'invited',
  mfa_secret       VARCHAR(128),
  expires_at       TIMESTAMPTZ NOT NULL,
  last_login_at    TIMESTAMPTZ,
  password_hash    VARCHAR(255) NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);

CREATE TABLE sync_conflict (
  id               BIGSERIAL PRIMARY KEY,
  employee_no      VARCHAR(32)  NOT NULL,
  conflict_type    VARCHAR(32)  NOT NULL,
  ldap_payload     JSONB,
  wechat_payload   JSONB,
  status           VARCHAR(16)  NOT NULL DEFAULT 'pending',
  resolved_by      BIGINT,
  resolution       VARCHAR(32),
  resolved_at      TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_sync_conflict_status ON sync_conflict(status, created_at);

CREATE TABLE role (
  id               BIGSERIAL PRIMARY KEY,
  code             VARCHAR(32) NOT NULL UNIQUE,
  name             VARCHAR(64) NOT NULL,
  scope            VARCHAR(16) NOT NULL DEFAULT 'global',
  builtin          BOOLEAN NOT NULL DEFAULT true,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE role_binding (
  id               BIGSERIAL PRIMARY KEY,
  user_id          BIGINT NOT NULL,
  role_id          BIGINT NOT NULL REFERENCES role(id),
  project_id       BIGINT,
  dept_id          BIGINT,
  granted_by       BIGINT NOT NULL,
  expires_at       TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_role_binding_user ON role_binding(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_role_binding_proj ON role_binding(project_id) WHERE deleted_at IS NULL;

CREATE TABLE data_domain (
  id               BIGSERIAL PRIMARY KEY,
  code             VARCHAR(32) NOT NULL UNIQUE,
  name             VARCHAR(64) NOT NULL,
  expr             JSONB NOT NULL,
  description      TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);

-- -------------------------------------------------------------
-- 3.2 项目与门禁域（M1 + M4）
-- -------------------------------------------------------------
CREATE TABLE program (
  id               BIGSERIAL PRIMARY KEY,
  code             VARCHAR(64) NOT NULL UNIQUE,
  name             VARCHAR(128) NOT NULL,
  owner_user_id    BIGINT NOT NULL,
  secrecy_level    VARCHAR(16) NOT NULL DEFAULT 'internal',
  target_date      DATE,
  status           VARCHAR(16) NOT NULL DEFAULT 'active',
  description      TEXT,
  created_by       BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);

CREATE TABLE project_type (
  id               BIGSERIAL PRIMARY KEY,
  code             VARCHAR(32) NOT NULL UNIQUE,
  name             VARCHAR(64) NOT NULL,
  sort_order       INT NOT NULL DEFAULT 0,
  enabled          BOOLEAN NOT NULL DEFAULT true,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE project (
  id               BIGSERIAL PRIMARY KEY,
  code             VARCHAR(64)  NOT NULL,
  name             VARCHAR(200) NOT NULL,
  program_id       BIGINT REFERENCES program(id),
  type_id          BIGINT NOT NULL REFERENCES project_type(id),
  pm_user_id       BIGINT NOT NULL,
  dept_id          BIGINT NOT NULL REFERENCES dept(id),
  status           VARCHAR(16) NOT NULL DEFAULT 'draft',
  secrecy_level    VARCHAR(16) NOT NULL,
  current_stage_id BIGINT,
  progress_pct     NUMERIC(5,2) NOT NULL DEFAULT 0,
  health           VARCHAR(8)  NOT NULL DEFAULT 'na',
  health_updated_at TIMESTAMPTZ,
  plan_start       DATE NOT NULL,
  plan_end         DATE NOT NULL,
  actual_start     DATE,
  actual_end       DATE,
  baseline_id      BIGINT,
  data_pedigree    VARCHAR(16) NOT NULL DEFAULT 'trial',
  milestone_summary JSONB,
  created_by       BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE UNIQUE INDEX uk_project_code ON project(code) WHERE deleted_at IS NULL;
CREATE INDEX idx_project_pm_status ON project(pm_user_id, status);
CREATE INDEX idx_project_program ON project(program_id);
CREATE INDEX idx_project_type_status ON project(type_id, status);
CREATE INDEX idx_project_name_trgm ON project USING gin (name gin_trgm_ops);

CREATE TABLE project_stakeholder (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  user_id          BIGINT NOT NULL,
  role_label       VARCHAR(32) NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ,
  UNIQUE (project_id, user_id, role_label)
);

CREATE TABLE stage_template (
  id               BIGSERIAL PRIMARY KEY,
  type_id          BIGINT NOT NULL REFERENCES project_type(id),
  code             VARCHAR(64) NOT NULL,
  name             VARCHAR(128) NOT NULL,
  order_no         INT NOT NULL,
  is_core          BOOLEAN NOT NULL DEFAULT false,
  typical_days     INT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ,
  UNIQUE (type_id, code)
);

CREATE TABLE checklist_template (
  id               BIGSERIAL PRIMARY KEY,
  code             VARCHAR(64) NOT NULL,
  name             VARCHAR(128) NOT NULL,
  version          INT NOT NULL DEFAULT 1,
  items            JSONB NOT NULL DEFAULT '[]',
  status           VARCHAR(16) NOT NULL DEFAULT 'draft',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);

CREATE TABLE gate_template (
  id               BIGSERIAL PRIMARY KEY,
  type_id          BIGINT NOT NULL REFERENCES project_type(id),
  stage_template_id BIGINT REFERENCES stage_template(id),
  code             VARCHAR(64) NOT NULL,
  name             VARCHAR(128) NOT NULL,
  order_no         INT NOT NULL,
  is_core          BOOLEAN NOT NULL DEFAULT false,
  is_high_risk     BOOLEAN NOT NULL DEFAULT false,
  signoff_roles    JSONB,
  checklist_template_id BIGINT REFERENCES checklist_template(id),
  enforce_mode     VARCHAR(16) NOT NULL DEFAULT 'commitment',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ,
  UNIQUE (type_id, code)
);

CREATE TABLE project_stage (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  template_id      BIGINT REFERENCES stage_template(id),
  name             VARCHAR(128) NOT NULL,
  order_no         INT NOT NULL,
  status           VARCHAR(16) NOT NULL DEFAULT 'not_started',
  plan_start       DATE,
  plan_end         DATE,
  actual_start     DATE,
  actual_end       DATE,
  is_tailored      BOOLEAN NOT NULL DEFAULT false,
  tailor_reason    TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_stage_project ON project_stage(project_id, order_no);

CREATE TABLE gate (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  stage_id         BIGINT REFERENCES project_stage(id),
  template_id      BIGINT REFERENCES gate_template(id),
  name             VARCHAR(128) NOT NULL,
  status           VARCHAR(16) NOT NULL DEFAULT 'not_started',
  decision         VARCHAR(16),
  decided_by       BIGINT,
  decided_at       TIMESTAMPTZ,
  is_high_risk     BOOLEAN NOT NULL DEFAULT false,
  enforce_mode     VARCHAR(16) NOT NULL DEFAULT 'commitment',
  gap_items        JSONB,
  waive_reason     TEXT,
  blocked_flag     BOOLEAN NOT NULL DEFAULT false,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_gate_project ON gate(project_id, order_no);
CREATE INDEX idx_gate_blocked ON gate(project_id) WHERE blocked_flag = true;

CREATE TABLE checklist_instance (
  id               BIGSERIAL PRIMARY KEY,
  gate_id          BIGINT NOT NULL,
  template_id      BIGINT REFERENCES checklist_template(id),
  template_version INT NOT NULL DEFAULT 1,
  items            JSONB NOT NULL DEFAULT '[]',
  total_count      INT NOT NULL DEFAULT 0,
  done_count       INT NOT NULL DEFAULT 0,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_checklist_gate ON checklist_instance(gate_id);

CREATE TABLE review (
  id               BIGSERIAL PRIMARY KEY,
  gate_id          BIGINT NOT NULL,
  title            VARCHAR(200) NOT NULL,
  scheduled_at     TIMESTAMPTZ,
  status           VARCHAR(16) NOT NULL DEFAULT 'draft',
  conclusion       TEXT,
  minutes_url      VARCHAR(512),
  created_by       BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_review_gate ON review(gate_id);

CREATE TABLE review_item (
  id               BIGSERIAL PRIMARY KEY,
  review_id        BIGINT NOT NULL,
  kind             VARCHAR(16) NOT NULL,
  content          TEXT NOT NULL,
  owner_user_id    BIGINT NOT NULL,
  due_date         DATE,
  status           VARCHAR(16) NOT NULL DEFAULT 'open',
  todo_id          BIGINT,
  closed_at        TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_review_item_owner ON review_item(owner_user_id, status, due_date);

CREATE TABLE review_signoff (
  id               BIGSERIAL PRIMARY KEY,
  review_id        BIGINT NOT NULL,
  role_code        VARCHAR(32) NOT NULL,
  user_id          BIGINT NOT NULL,
  status           VARCHAR(16) NOT NULL DEFAULT 'pending',
  delegated_from   BIGINT,
  signed_at        TIMESTAMPTZ,
  comment          TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_signoff_review ON review_signoff(review_id);

-- -------------------------------------------------------------
-- 3.3 任务与进度域（M1）
-- -------------------------------------------------------------
CREATE TABLE wbs (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  parent_id        BIGINT REFERENCES wbs(id),
  code             VARCHAR(64) NOT NULL,
  name             VARCHAR(200) NOT NULL,
  level            SMALLINT NOT NULL,
  order_no         INT NOT NULL DEFAULT 0,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_wbs_project ON wbs(project_id, order_no);

CREATE TABLE task (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  wbs_id           BIGINT REFERENCES wbs(id),
  parent_id        BIGINT REFERENCES task(id),
  name             VARCHAR(200) NOT NULL,
  description      TEXT,
  owner_user_id    BIGINT NOT NULL,
  assignee_ids     JSONB,
  consult_ids      JSONB,
  inform_ids       JSONB,
  plan_start       DATE NOT NULL,
  plan_end         DATE NOT NULL,
  actual_start     DATE,
  actual_end       DATE,
  est_hours        NUMERIC(8,2),
  progress_pct     NUMERIC(5,2) NOT NULL DEFAULT 0,
  status           VARCHAR(16) NOT NULL DEFAULT 'not_started',
  blocked_reason   TEXT,
  blocked_help_user_id BIGINT,
  priority         SMALLINT NOT NULL DEFAULT 3,
  is_milestone     BOOLEAN NOT NULL DEFAULT false,
  is_critical      BOOLEAN NOT NULL DEFAULT false,
  ci_status        VARCHAR(16),
  ci_ref           VARCHAR(128),
  baseline_offset_days INT,
  external_ref     VARCHAR(128),
  created_by       BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_task_project_status ON task(project_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_task_owner ON task(owner_user_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_task_plan_end ON task(plan_end) WHERE status <> 'done' AND deleted_at IS NULL;
CREATE INDEX idx_task_external_ref ON task(external_ref);

-- 一个任务有且仅有一个 accountable owner
CREATE TABLE task_raci (
  id               BIGSERIAL PRIMARY KEY,
  task_id          BIGINT NOT NULL,
  user_id          BIGINT NOT NULL,
  raci             VARCHAR(1) NOT NULL,
  is_primary_accountable BOOLEAN NOT NULL DEFAULT false,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE UNIQUE INDEX uk_task_primary_a ON task_raci(task_id) WHERE is_primary_accountable AND deleted_at IS NULL;
CREATE INDEX idx_raci_task ON task_raci(task_id);

CREATE TABLE dependency (
  id               BIGSERIAL PRIMARY KEY,
  predecessor_task_id BIGINT NOT NULL,
  successor_task_id   BIGINT NOT NULL,
  dep_type         VARCHAR(2) NOT NULL DEFAULT 'FS',
  lag_days         INT NOT NULL DEFAULT 0,
  cross_project    BOOLEAN NOT NULL DEFAULT false,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ,
  UNIQUE (predecessor_task_id, successor_task_id)
);
CREATE INDEX idx_dep_pred ON dependency(predecessor_task_id);
CREATE INDEX idx_dep_succ ON dependency(successor_task_id);

CREATE TABLE baseline (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  name             VARCHAR(100) NOT NULL,
  kind             VARCHAR(16) NOT NULL,
  snapshot_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by       BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_baseline_project ON baseline(project_id, snapshot_at DESC);

CREATE TABLE baseline_task (
  id               BIGSERIAL PRIMARY KEY,
  baseline_id      BIGINT NOT NULL,
  task_id          BIGINT NOT NULL,
  plan_start       DATE NOT NULL,
  plan_end         DATE NOT NULL,
  est_hours        NUMERIC(8,2),
  progress_pct     NUMERIC(5,2),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_baseline_task ON baseline_task(baseline_id, task_id);

CREATE TABLE milestone (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  task_id          BIGINT,
  name             VARCHAR(200) NOT NULL,
  kind             VARCHAR(32),
  plan_date        DATE NOT NULL,
  actual_date      DATE,
  status           VARCHAR(16) NOT NULL DEFAULT 'pending',
  is_critical      BOOLEAN NOT NULL DEFAULT false,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_milestone_project ON milestone(project_id, plan_date);
CREATE INDEX idx_milestone_kind ON milestone(kind, plan_date);

-- -------------------------------------------------------------
-- 3.4 协同域（M6）
-- -------------------------------------------------------------
CREATE TABLE ticket (
  id               BIGSERIAL PRIMARY KEY,
  code             VARCHAR(64) NOT NULL UNIQUE,
  title            VARCHAR(200) NOT NULL,
  ticket_type      VARCHAR(16) NOT NULL,
  project_id       BIGINT,
  requester_user_id BIGINT NOT NULL,
  target_dept_id   BIGINT NOT NULL,
  target_user_id   BIGINT,
  description      TEXT NOT NULL,
  priority         SMALLINT NOT NULL DEFAULT 3,
  status           VARCHAR(16) NOT NULL DEFAULT 'pending',
  sla_due_at       TIMESTAMPTZ NOT NULL,
  responded_at     TIMESTAMPTZ,
  resolved_at      TIMESTAMPTZ,
  escalate_level   SMALLINT NOT NULL DEFAULT 0,
  satisfaction_score SMALLINT,
  closed_by        BIGINT,
  close_comment    TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_ticket_target_dept ON ticket(target_dept_id, status);
CREATE INDEX idx_ticket_requester ON ticket(requester_user_id);
CREATE INDEX idx_ticket_sla ON ticket(sla_due_at) WHERE status NOT IN ('closed','resolved');

CREATE TABLE ticket_action (
  id               BIGSERIAL PRIMARY KEY,
  ticket_id        BIGINT NOT NULL,
  actor_user_id    BIGINT NOT NULL,
  action           VARCHAR(32) NOT NULL,
  from_status      VARCHAR(16),
  to_status        VARCHAR(16),
  comment          TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ticket_action ON ticket_action(ticket_id, created_at);

CREATE TABLE meeting (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT,
  title            VARCHAR(200) NOT NULL,
  start_at         TIMESTAMPTZ NOT NULL,
  attendees        JSONB,
  minutes_url      VARCHAR(512),
  created_by       BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);

CREATE TABLE meeting_decision (
  id               BIGSERIAL PRIMARY KEY,
  meeting_id       BIGINT NOT NULL,
  content          TEXT NOT NULL,
  owner_user_id    BIGINT NOT NULL,
  due_date         DATE NOT NULL,
  status           VARCHAR(16) NOT NULL DEFAULT 'open',
  todo_id          BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_decision_owner ON meeting_decision(owner_user_id, status);

CREATE TABLE weekly_report (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  week_start       DATE NOT NULL,
  week_end         DATE NOT NULL,
  auto_content     JSONB NOT NULL DEFAULT '{}',
  ai_summary       TEXT,
  pm_comment       TEXT,
  risk_supplement  TEXT,
  status           VARCHAR(16) NOT NULL DEFAULT 'draft',
  published_at     TIMESTAMPTZ,
  published_by     BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ,
  UNIQUE (project_id, week_start)
);

CREATE TABLE todo_item (
  id               BIGSERIAL PRIMARY KEY,
  user_id          BIGINT NOT NULL,
  kind             VARCHAR(16) NOT NULL,
  ref_type         VARCHAR(32) NOT NULL,
  ref_id           BIGINT NOT NULL,
  title            VARCHAR(200) NOT NULL,
  due_at           TIMESTAMPTZ,
  status           VARCHAR(16) NOT NULL DEFAULT 'open',
  priority_score   NUMERIC(6,2) NOT NULL DEFAULT 0,
  source_channel   VARCHAR(16) NOT NULL DEFAULT 'system',
  done_at          TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_todo_user ON todo_item(user_id, status, priority_score DESC);

CREATE TABLE notification (
  id               BIGSERIAL PRIMARY KEY,
  user_id          BIGINT NOT NULL,
  channel          VARCHAR(16) NOT NULL,
  event_type       VARCHAR(64) NOT NULL,
  payload          JSONB NOT NULL DEFAULT '{}',
  status           VARCHAR(16) NOT NULL DEFAULT 'pending',
  dedup_key        VARCHAR(128),
  sent_at          TIMESTAMPTZ,
  fail_reason      TEXT,
  retry_count      SMALLINT NOT NULL DEFAULT 0,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notification_status ON notification(status, created_at);
CREATE INDEX idx_notification_dedup ON notification(dedup_key);

CREATE TABLE notification_rule (
  id               BIGSERIAL PRIMARY KEY,
  event_type       VARCHAR(64) NOT NULL,
  channels         JSONB NOT NULL DEFAULT '["inapp"]',
  freq_limit       VARCHAR(32) NOT NULL DEFAULT 'realtime',
  user_override    JSONB,
  enabled          BOOLEAN NOT NULL DEFAULT true,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -------------------------------------------------------------
-- 3.5 资源与成本域（M3/M7，P1 建表 P2 实现）
-- -------------------------------------------------------------
CREATE TABLE skill (
  id               BIGSERIAL PRIMARY KEY,
  code             VARCHAR(64) NOT NULL UNIQUE,
  name             VARCHAR(128) NOT NULL,
  category         VARCHAR(32) NOT NULL,
  status           VARCHAR(16) NOT NULL DEFAULT 'active',
  merged_to        BIGINT REFERENCES skill(id),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);

CREATE TABLE member_skill (
  id               BIGSERIAL PRIMARY KEY,
  user_id          BIGINT NOT NULL,
  skill_id         BIGINT NOT NULL REFERENCES skill(id),
  level            SMALLINT NOT NULL DEFAULT 3,
  source           VARCHAR(16) NOT NULL DEFAULT 'self',
  verified_by      BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ,
  UNIQUE (user_id, skill_id)
);
CREATE INDEX idx_member_skill_skill ON member_skill(skill_id, level);

CREATE TABLE resource_pool (
  id               BIGSERIAL PRIMARY KEY,
  res_type         VARCHAR(16) NOT NULL,
  name             VARCHAR(128) NOT NULL,
  dept_id          BIGINT REFERENCES dept(id),
  owner_user_id    BIGINT,
  capacity_unit    VARCHAR(16),
  status           VARCHAR(16) NOT NULL DEFAULT 'active',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);

CREATE TABLE reservation (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  res_type         VARCHAR(16) NOT NULL,
  resource_id      BIGINT NOT NULL,
  percent          NUMERIC(5,2) NOT NULL,
  start_date       DATE NOT NULL,
  end_date         DATE NOT NULL,
  status           VARCHAR(16) NOT NULL DEFAULT 'requested',
  approved_by      BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_reservation_res ON reservation(resource_id, start_date, end_date);

CREATE TABLE lab_resource (
  id               BIGSERIAL PRIMARY KEY,
  name             VARCHAR(128) NOT NULL,
  location         VARCHAR(128),
  env_spec         TEXT,
  access_level     VARCHAR(16) NOT NULL DEFAULT 'normal',
  status           VARCHAR(16) NOT NULL DEFAULT 'available',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);

CREATE TABLE lab_booking (
  id               BIGSERIAL PRIMARY KEY,
  lab_resource_id  BIGINT NOT NULL REFERENCES lab_resource(id),
  project_id       BIGINT NOT NULL,
  user_id          BIGINT NOT NULL,
  start_at         TIMESTAMPTZ NOT NULL,
  end_at           TIMESTAMPTZ NOT NULL,
  status           VARCHAR(16) NOT NULL DEFAULT 'booked',
  purpose          TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE UNIQUE INDEX uk_lab_slot ON lab_booking(lab_resource_id, start_at, end_at) WHERE status <> 'cancelled' AND deleted_at IS NULL;

CREATE TABLE batch (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  batch_type       VARCHAR(16) NOT NULL,
  vendor_name      VARCHAR(128) NOT NULL,
  lot_no           VARCHAR(64),
  status           VARCHAR(16) NOT NULL DEFAULT 'planned',
  plan_release_date DATE,
  actual_release_date DATE,
  plan_out_date    DATE,
  actual_out_date  DATE,
  qty              INT,
  shared_batch_id  BIGINT REFERENCES batch(id),
  source           VARCHAR(16) NOT NULL DEFAULT 'manual',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_batch_project ON batch(project_id, batch_type);

CREATE TABLE batch_milestone (
  id               BIGSERIAL PRIMARY KEY,
  batch_id         BIGINT NOT NULL,
  name             VARCHAR(64) NOT NULL,
  plan_date        DATE,
  actual_date      DATE,
  status           VARCHAR(16) NOT NULL DEFAULT 'pending',
  source           VARCHAR(16) NOT NULL DEFAULT 'manual',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_batch_ms ON batch_milestone(batch_id);

CREATE TABLE cost_share (
  id               BIGSERIAL PRIMARY KEY,
  batch_id         BIGINT NOT NULL,
  project_id       BIGINT NOT NULL,
  amount           NUMERIC(14,2) NOT NULL,
  share_rule       VARCHAR(32) NOT NULL,
  confirmed        BOOLEAN NOT NULL DEFAULT false,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);

CREATE TABLE budget (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  category         VARCHAR(16) NOT NULL,
  year_month       CHAR(7) NOT NULL,
  planned_amount   NUMERIC(14,2) NOT NULL DEFAULT 0,
  note             TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ,
  UNIQUE (project_id, category, year_month)
);

CREATE TABLE cost_ledger (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  year_month       CHAR(7) NOT NULL,
  category         VARCHAR(16) NOT NULL,
  amount           NUMERIC(14,2) NOT NULL DEFAULT 0,
  source           VARCHAR(16) NOT NULL DEFAULT 'manual',
  import_job_id    BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_cost_ledger_proj ON cost_ledger(project_id, year_month);

CREATE TABLE timesheet (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  task_id          BIGINT,
  user_id          BIGINT NOT NULL,
  week_start       DATE NOT NULL,
  hours            NUMERIC(6,2) NOT NULL,
  note             TEXT,
  status           VARCHAR(16) NOT NULL DEFAULT 'draft',
  approver_id      BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ,
  UNIQUE (user_id, project_id, task_id, week_start)
);

-- -------------------------------------------------------------
-- 3.6 风险域（M5，P2）
-- -------------------------------------------------------------
CREATE TABLE risk (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  code             VARCHAR(64) NOT NULL UNIQUE,
  title            VARCHAR(200) NOT NULL,
  description      TEXT,
  probability      SMALLINT NOT NULL DEFAULT 3,
  impact           SMALLINT NOT NULL DEFAULT 3,
  level            VARCHAR(8) NOT NULL DEFAULT 'medium',
  owner_user_id    BIGINT NOT NULL,
  mitigation       TEXT,
  trigger_condition TEXT,
  review_cycle_days INT NOT NULL DEFAULT 14,
  next_review_at   TIMESTAMPTZ NOT NULL,
  status           VARCHAR(16) NOT NULL DEFAULT 'open',
  in_library       BOOLEAN NOT NULL DEFAULT false,
  closed_at        TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_risk_review ON risk(next_review_at) WHERE status <> 'closed';
CREATE INDEX idx_risk_project ON risk(project_id, status);

CREATE TABLE issue (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  code             VARCHAR(64) NOT NULL UNIQUE,
  title            VARCHAR(200) NOT NULL,
  severity         VARCHAR(8) NOT NULL DEFAULT 'p2',
  owner_user_id    BIGINT NOT NULL,
  status           VARCHAR(16) NOT NULL DEFAULT 'open',
  due_at           TIMESTAMPTZ,
  escalated_at     TIMESTAMPTZ,
  source           VARCHAR(32),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_issue_owner ON issue(owner_user_id, status);

CREATE TABLE change_request (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  code             VARCHAR(64) NOT NULL UNIQUE,
  title            VARCHAR(200) NOT NULL,
  change_type      VARCHAR(16) NOT NULL,
  impact           JSONB,
  status           VARCHAR(16) NOT NULL DEFAULT 'draft',
  approved_by      BIGINT,
  baseline_id      BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);

-- -------------------------------------------------------------
-- 3.7 交接物（M2）
-- -------------------------------------------------------------
CREATE TABLE deliverable (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  name             VARCHAR(200) NOT NULL,
  deliver_type     VARCHAR(32) NOT NULL,
  from_project_id  BIGINT,
  to_project_id    BIGINT,
  from_user_id     BIGINT NOT NULL,
  to_user_id       BIGINT NOT NULL,
  due_date         DATE NOT NULL,
  file_url         VARCHAR(512),
  status           VARCHAR(16) NOT NULL DEFAULT 'pending',
  delivered_at     TIMESTAMPTZ,
  accepted_at      TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_deliverable_to ON deliverable(to_user_id, status, due_date);

-- -------------------------------------------------------------
-- 3.8 平台底座（M10）
-- -------------------------------------------------------------
CREATE TABLE attachment (
  id               BIGSERIAL PRIMARY KEY,
  object_type      VARCHAR(32) NOT NULL,
  object_id        BIGINT NOT NULL,
  file_name        VARCHAR(255) NOT NULL,
  size_bytes       BIGINT NOT NULL,
  storage_key      VARCHAR(512) NOT NULL,
  uploaded_by      BIGINT NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);
CREATE INDEX idx_attachment_obj ON attachment(object_type, object_id);

CREATE TABLE audit_log (
  id               BIGSERIAL,
  actor_user_id    BIGINT,
  actor_type       VARCHAR(16) NOT NULL DEFAULT 'internal',
  action           VARCHAR(64) NOT NULL,
  object_type      VARCHAR(32) NOT NULL,
  object_id        BIGINT,
  before           JSONB,
  after            JSONB,
  ip               VARCHAR(64),
  user_agent       VARCHAR(512),
  trace_id         VARCHAR(64) NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);
-- 分区必须按月预建（不设 DEFAULT 分区，否则后续新增分区会因数据重叠失败）。
-- 运维脚本每月 25 日创建次月分区，示例：
-- CREATE TABLE audit_log_2026_11 PARTITION OF audit_log
--   FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
-- 首期请至少预建 3 个月分区，否则插入会报 "no partition of relation found"。
-- 归档：分区满 180 天后 DETACH + 导出冷存。
CREATE INDEX idx_audit_obj ON audit_log(object_type, object_id);
CREATE INDEX idx_audit_actor ON audit_log(actor_user_id, created_at DESC);

CREATE TABLE import_job (
  id               BIGSERIAL PRIMARY KEY,
  import_type      VARCHAR(32) NOT NULL,
  file_url         VARCHAR(512) NOT NULL,
  mapping          JSONB NOT NULL DEFAULT '{}',
  status           VARCHAR(16) NOT NULL DEFAULT 'uploaded',
  total_rows       INT NOT NULL DEFAULT 0,
  success_rows     INT NOT NULL DEFAULT 0,
  failed_rows      INT NOT NULL DEFAULT 0,
  error_report_url VARCHAR(512),
  operator_id      BIGINT NOT NULL,
  rollback_token   VARCHAR(64) NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE dictionary (
  id               BIGSERIAL PRIMARY KEY,
  category         VARCHAR(32) NOT NULL,
  code             VARCHAR(64) NOT NULL,
  name             VARCHAR(128) NOT NULL,
  sort_order       INT NOT NULL DEFAULT 0,
  status           VARCHAR(16) NOT NULL DEFAULT 'active',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ,
  UNIQUE (category, code)
);

CREATE TABLE template (
  id               BIGSERIAL PRIMARY KEY,
  tpl_type         VARCHAR(16) NOT NULL,
  code             VARCHAR(64) NOT NULL,
  name             VARCHAR(128) NOT NULL,
  version          INT NOT NULL DEFAULT 1,
  content          JSONB NOT NULL DEFAULT '{}',
  status           VARCHAR(16) NOT NULL DEFAULT 'draft',
  tailorable       BOOLEAN NOT NULL DEFAULT true,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at       TIMESTAMPTZ
);

CREATE TABLE secrecy_change_request (
  id               BIGSERIAL PRIMARY KEY,
  project_id       BIGINT NOT NULL,
  from_level       VARCHAR(16) NOT NULL,
  to_level         VARCHAR(16) NOT NULL,
  reason           TEXT NOT NULL,
  requested_by     BIGINT NOT NULL,
  approver1_id     BIGINT,
  approver2_id     BIGINT,
  status           VARCHAR(16) NOT NULL DEFAULT 'pending',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE integration_config (
  id               BIGSERIAL PRIMARY KEY,
  code             VARCHAR(32) NOT NULL UNIQUE,
  name             VARCHAR(64) NOT NULL,
  enabled          BOOLEAN NOT NULL DEFAULT false,
  params           BYTEA,               -- AES 加密后的 JSON，密钥取自环境变量
  last_sync_at     TIMESTAMPTZ,
  last_status      VARCHAR(16),
  fail_count       SMALLINT NOT NULL DEFAULT 0,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ai_call_log (
  id               BIGSERIAL PRIMARY KEY,
  user_id          BIGINT NOT NULL,
  scene            VARCHAR(32) NOT NULL,
  provider         VARCHAR(32) NOT NULL,
  token_in         INT NOT NULL DEFAULT 0,
  token_out        INT NOT NULL DEFAULT 0,
  cost_cent        NUMERIC(10,4) NOT NULL DEFAULT 0,
  latency_ms       INT NOT NULL DEFAULT 0,
  status           VARCHAR(16) NOT NULL,
  request_digest   VARCHAR(255) NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ai_log_created ON ai_call_log(created_at DESC);
CREATE INDEX idx_ai_log_user ON ai_call_log(user_id, created_at DESC);

-- -------------------------------------------------------------
-- 报表物化视图（驾驶舱用，每日刷新）
-- -------------------------------------------------------------
CREATE MATERIALIZED VIEW mv_project_health_daily AS
SELECT p.id AS project_id, p.code, p.name, p.type_id, p.program_id, p.dept_id,
       p.pm_user_id, p.status, p.health, p.progress_pct, p.secrecy_level,
       (SELECT count(*) FROM task t
          WHERE t.project_id = p.id AND t.deleted_at IS NULL
            AND t.status = 'blocked') AS blocked_task_cnt,
       (SELECT count(*) FROM ticket k
          WHERE k.project_id = p.id AND k.deleted_at IS NULL
            AND k.status IN ('pending','escalated')) AS open_ticket_cnt,
       (SELECT count(*) FROM gate g
          WHERE g.project_id = p.id AND g.deleted_at IS NULL
            AND g.blocked_flag = true) AS blocked_gate_cnt,
       now() AS refreshed_at
FROM project p
WHERE p.deleted_at IS NULL;
CREATE UNIQUE INDEX uk_mv_health ON mv_project_health_daily(project_id);
-- 刷新：REFRESH MATERIALIZED VIEW CONCURRENTLY mv_project_health_daily;（每日 02:30）

-- =============================================================
-- 初始数据（角色）
-- =============================================================
INSERT INTO role (code, name, scope, builtin) VALUES
  ('pmo_admin','PMO 管理员','global',true),
  ('pmo_secrecy','密级管理员','global',true),
  ('pm','项目经理','project',true),
  ('dept_head','部门主管','dept',true),
  ('member','项目成员','project',true),
  ('program_owner','专项负责人','project',true),
  ('exec','高管/经营层','global',true),
  ('finance','财务接口人','global',true),
  ('qa','质量体系','global',true);

INSERT INTO project_type (code, name, sort_order) VALUES
  ('chip_design','芯片设计',1),
  ('pkg_design','芯片封装设计',2),
  ('test_eng','芯片测试工程',3),
  ('hw_board','硬件板卡设计',4),
  ('software','软件设计',5),
  ('system','整机设计',6),
  ('cluster','集群调测',7),
  ('npi','NPI 导入',8),
  ('delivery','客户交付专项',9),
  ('solution','解决方案专项',10);

-- 阶段与门禁模板由 scripts/seed/project_types.py 按 TSD 附录 A 写入
-- =============================================================
-- 结束
-- =============================================================

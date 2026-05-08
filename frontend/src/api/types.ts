export type LifecycleState = "setup" | "active" | "completed";

export type CustomFieldSpec = {
  key: string;
  label: string;
  type: "text" | "number" | "select";
  required: boolean;
};

export type Tournament = {
  id: string;
  name: string;
  competition_date: string;
  time_zone: string;
  rounds_per_match: number;
  round_length_seconds: number;
  slideshow_slide_seconds: number;
  lifecycle_state: LifecycleState;
  is_demo: boolean;
  judge_auto_release_seconds: number;
  custom_participant_fields: CustomFieldSpec[];
};

export type Judge = {
  id: string;
  tournament_id: string;
  name: string;
  code: string;
  created_at: string;
};

export type Participant = {
  id: string;
  tournament_id: string;
  name: string;
  division_id: string | null;
  custom_fields: Record<string, string | number | null>;
  is_withdrawn: boolean;
};

export type DivisionState =
  | "setup"
  | "round_robin"
  | "play_ins"
  | "semis"
  | "finals"
  | "completed"
  | "paused";

export type Division = {
  id: string;
  tournament_id: string;
  name: string;
  state: DivisionState;
  paused_reason: string | null;
};

export type MatchPhase = "round_robin" | "play_in" | "semi" | "final" | "bronze";
export type MatchState =
  | "scheduled"
  | "in_progress"
  | "paused"
  | "pending_review"
  | "submitted";

export type MatchRound = {
  round_number: number;
  competitor_a_score: number;
  competitor_b_score: number;
};

export type Match = {
  id: string;
  division_id: string;
  phase: MatchPhase;
  state: MatchState;
  order_index: number;
  competitor_a_id: string;
  competitor_b_id: string;
  winner_id: string | null;
  assigned_judge_id: string | null;
  rounds: MatchRound[];
};

export type ActorType = "admin" | "judge" | "system";

export type ActivityEntry = {
  id: string;
  tournament_id: string;
  actor_type: ActorType;
  actor_id: string;
  actor_display_name: string;
  action: string;
  description: string;
  division_id: string | null;
  created_at: string;
};

export type BackupStatus = "pending" | "complete" | "failed";
export type BackupTrigger = "manual" | "pre_action" | "hourly";

export type Backup = {
  id: string;
  tournament_id: string;
  triggered_by: BackupTrigger;
  pre_action_description: string | null;
  s3_key: string | null;
  size_bytes: number | null;
  status: BackupStatus;
  created_at: string;
  completed_at: string | null;
};

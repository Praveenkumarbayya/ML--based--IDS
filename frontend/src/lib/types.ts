// Mirrors api/schemas.py so the frontend and backend share a contract.

export type Label = "Benign" | "Malicious";

export interface NetworkFlow {
  duration?: number;
  protocol_type?: string;
  service?: string;
  flag?: string;
  src_bytes?: number;
  dst_bytes?: number;
  land?: number;
  wrong_fragment?: number;
  urgent?: number;
  hot?: number;
  num_failed_logins?: number;
  logged_in?: number;
  num_compromised?: number;
  root_shell?: number;
  su_attempted?: number;
  num_root?: number;
  num_file_creations?: number;
  num_shells?: number;
  num_access_files?: number;
  num_outbound_cmds?: number;
  is_host_login?: number;
  is_guest_login?: number;
  count?: number;
  srv_count?: number;
  serror_rate?: number;
  srv_serror_rate?: number;
  rerror_rate?: number;
  srv_rerror_rate?: number;
  same_srv_rate?: number;
  diff_srv_rate?: number;
  srv_diff_host_rate?: number;
  dst_host_count?: number;
  dst_host_srv_count?: number;
  dst_host_same_srv_rate?: number;
  dst_host_diff_srv_rate?: number;
  dst_host_same_src_port_rate?: number;
  dst_host_srv_diff_host_rate?: number;
  dst_host_serror_rate?: number;
  dst_host_srv_serror_rate?: number;
  dst_host_rerror_rate?: number;
  dst_host_srv_rerror_rate?: number;
}

export interface FeatureContribution {
  feature: string;
  value: number;
}

export interface PredictionResponse {
  request_id: string;
  model_used: string;
  prediction: Label;
  confidence: number;
  class_probabilities: Record<string, number>;
  latency_ms: number;
  top_features: FeatureContribution[];
}

export interface HealthResponse {
  status: "ok" | "degraded";
  models_loaded: string[];
  preprocessor_loaded: boolean;
}

export interface MetadataResponse {
  available_models: string[];
  default_model: string | null;
  class_labels: string[];
  feature_names: string[];
}

export interface AuditPrediction {
  id: number;
  request_id: string;
  created_at: string;
  endpoint: string;
  model_used: string;
  prediction: Label;
  confidence: number;
  latency_ms: number;
  client_ip: string | null;
  raw_features: Record<string, unknown>;
  class_probabilities: Record<string, number>;
}

export interface Alert {
  id: number;
  prediction_id: number;
  created_at: string;
  severity: "low" | "medium" | "high";
  acknowledged: boolean;
  ack_by: string | null;
  ack_at: string | null;
}

export interface WSAlertMessage {
  type: "alert";
  alert_id: number;
  request_id: string;
  prediction_id: number;
  model_used: string;
  prediction: Label;
  confidence: number;
  severity: "low" | "medium" | "high";
  latency_ms: number;
  top_features: FeatureContribution[];
  timestamp: string;
}

export interface ModelEvalMetrics {
  accuracy: number;
  precision_macro: number;
  recall_macro: number;
  f1_macro: number;
  roc_auc: number | null;
  confusion_matrix: number[][];
  classification_report: Record<string, unknown>;
  precision_per_class: Record<string, number>;
  recall_per_class: Record<string, number>;
  f1_per_class: Record<string, number>;
  name: string;
}

export type EvaluationReport = Record<string, Record<string, ModelEvalMetrics>>;

export interface TrainingSummary {
  [modelName: string]: {
    best_params: Record<string, unknown>;
    cv_score: number | null;
    train_time_seconds: number | null;
  };
}
